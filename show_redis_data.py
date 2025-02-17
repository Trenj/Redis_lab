import redis
from tabulate import tabulate

# Подключение к Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Получение всех пользователей
user_keys = r.keys("user:*")
users = []

for key in user_keys:
    if key.count(":") == 1:  # Оставляем только основные ключи пользователей
        user_id = key.split(":")[1]
        user_data = r.hgetall(key)
        
        # Получаем друзей пользователя
        friends_key = f"user:{user_id}:friends"
        friends = r.smembers(friends_key)
        friends_list = ", ".join(friends) if friends else "No friends"
        
        # Получаем сообщения пользователя
        messages = []
        message_keys = r.keys("message:*")
        for msg_key in message_keys:
            msg_data = r.hgetall(msg_key)
            if msg_data.get("user_id") == user_id:
                messages.append(msg_data.get("text", ""))
        messages_text = "\n".join(messages) if messages else "No messages"

        # Добавляем в список пользователей
        users.append([user_id, user_data.get("name", "N/A"), user_data.get("login", "N/A"), friends_list, messages_text])

# Вывод данных в виде таблицы
headers = ["ID", "Name", "Login", "Friends", "Messages"]
print(tabulate(users, headers=headers, tablefmt="grid"))
