import redis
from tabulate import tabulate

# Подключение к Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Получение всех пользователей (фильтруем только основные ключи, исключая user:*:friends)
user_keys = [key for key in r.keys("user:*") if ":" not in key[5:]]

users = []

for key in user_keys:
    user_id = key.split(":")[1]  # ID пользователя
    user_data = r.hgetall(key)

    # Получаем список друзей пользователя
    friends_key = f"user:{user_id}:friends"
    friends = sorted(r.smembers(friends_key), key=int)  # Преобразуем к числу для сортировки
    friends_list = ", ".join(friends) if friends else "No friends"

    # Получаем сообщения пользователя
    messages = []
    message_keys = r.keys("message:*")
    for msg_key in message_keys:
        msg_data = r.hgetall(msg_key)
        if msg_data.get("user_id") == str(user_id):  # Сравниваем ID в строковом формате
            messages.append(msg_data.get("text", ""))
    
    messages_text = "\n".join(messages) if messages else "No messages"

    # Добавляем пользователя в список
    users.append([user_id, user_data.get("name", "N/A"), user_data.get("login", "N/A"), friends_list, messages_text])

# Вывод данных в виде таблицы
headers = ["ID", "Name", "Login", "Friends", "Messages"]
if users:
    print(tabulate(users, headers=headers, tablefmt="grid"))
else:
    print("Нет пользователей в системе.")
