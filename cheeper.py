import redis
from tabulate import tabulate
from datetime import datetime

# Подключение к Redis с обработкой ошибок
def connect_to_redis():
    try:
        # Попытка подключения к Redis
        r = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5
        )
        # Проверка подключения
        r.ping()
        print("Успешное подключение к Redis!")
        return r
    except redis.ConnectionError as e:
        print(f"Ошибка подключения к Redis: {e}")
        print("Пожалуйста, убедитесь, что Redis сервер запущен")
        return None
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        return None

def add_user(r, user_id, name, login):
    key = f"user:{user_id}"
    if r.exists(key):
        print(f"Пользователь с ID {user_id} уже существует!")
        return
    
    # Создаем хеш пользователя
    r.hset(key, mapping={"name": name, "login": login})
    
    # Создаем пустое множество для друзей
    r.sadd(f"user:{user_id}:friends", "")
    r.srem(f"user:{user_id}:friends", "")  # Удаляем пустую строку, чтобы получить действительно пустое множество
    
    print(f"Пользователь {name} добавлен.")

def add_message(r, user_id, message):
    # Проверяем существование пользователя
    if not r.exists(f"user:{user_id}"):
        print(f"Ошибка: Пользователь с ID {user_id} не существует.")
        return
    
    # Генерируем ID сообщения
    message_id = r.incr("message:next_id")
    
    # Сохраняем сообщение
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    r.hset(f"message:{message_id}", mapping={
        "user_id": user_id,
        "text": message,
        "timestamp": timestamp
    })
    
    print(f"Сообщение добавлено пользователю {user_id}.")

def add_friend(r, user_id, friend_id):
    # Проверяем существование пользователей
    user_key, friend_key = f"user:{user_id}", f"user:{friend_id}"
    if not r.exists(user_key) or not r.exists(friend_key):
        print("Один из пользователей не найден!")
        return
    
    # Добавляем каждого пользователя в список друзей другого
    user_friends_key = f"user:{user_id}:friends"
    friend_friends_key = f"user:{friend_id}:friends"
    
    # Проверяем, являются ли уже друзьями
    if r.sismember(user_friends_key, friend_id):
        print("Они уже друзья.")
        return
    
    # Добавляем в множества друзей
    r.sadd(user_friends_key, friend_id)
    r.sadd(friend_friends_key, user_id)
    
    print(f"Пользователи {user_id} и {friend_id} теперь друзья.")

def get_messages_by_period(r, user_id, start_date=None, end_date=None):
    # Проверяем существование пользователя
    if not r.exists(f"user:{user_id}"):
        print(f"Пользователь с ID {user_id} не существует.")
        return []
    
    # Получаем все ключи сообщений
    message_keys = r.keys("message:*")
    messages = []
    
    for msg_key in message_keys:
        if msg_key == "message:next_id":  # Пропускаем счетчик ID
            continue
            
        msg_data = r.hgetall(msg_key)
        
        # Проверяем, принадлежит ли сообщение пользователю
        if msg_data.get("user_id") == str(user_id):
            timestamp_str = msg_data.get("timestamp")
            message_text = msg_data.get("text", "")
            
            # Если у сообщения есть временная метка, фильтруем по дате
            if timestamp_str and (start_date or end_date):
                try:
                    msg_date = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    
                    # Пропускаем сообщения вне указанного периода
                    if start_date and msg_date < start_date:
                        continue
                    if end_date and msg_date > end_date:
                        continue
                        
                    messages.append(f"{timestamp_str}: {message_text}")
                except ValueError:
                    # Если формат даты некорректный, добавляем сообщение без фильтрации
                    messages.append(message_text)
            else:
                # Если нет фильтрации по дате или нет временной метки, добавляем сообщение
                if timestamp_str:
                    messages.append(f"{timestamp_str}: {message_text}")
                else:
                    messages.append(message_text)
    
    return messages

def get_sorted_friend_names(r, user_id):
    # Проверяем существование пользователя
    if not r.exists(f"user:{user_id}"):
        print(f"Пользователь с ID {user_id} не существует.")
        return []
    
    # Получаем список ID друзей
    friends_key = f"user:{user_id}:friends"
    friend_ids = list(r.smembers(friends_key))
    
    # Получаем имена друзей
    friend_names = []
    for friend_id in friend_ids:
        friend_key = f"user:{friend_id}"
        if r.exists(friend_key):
            name = r.hget(friend_key, "name")
            if name:
                friend_names.append(name)
    
    # Возвращаем отсортированный список имен
    return sorted(friend_names)

def count_friends(r, user_id):
    # Проверяем существование пользователя
    if not r.exists(f"user:{user_id}"):
        print(f"Пользователь с ID {user_id} не существует.")
        return 0
    
    # Возвращаем количество друзей
    return r.scard(f"user:{user_id}:friends")

def show_users(r):
    # Получаем все ключи пользователей (фильтруем, чтобы исключить вспомогательные ключи)
    user_keys = [key for key in r.keys("user:*") if ":" not in key[5:]]
    
    users = []
    
    for key in user_keys:
        user_id = key.split(":")[1]  # ID пользователя
        user_data = r.hgetall(key)
        
        # Получаем список друзей
        friends_key = f"user:{user_id}:friends"
        friends = sorted(r.smembers(friends_key), key=lambda x: int(x) if x.isdigit() else 0)
        friends_list = ", ".join(friends) if friends else "Нет друзей"
        
        # Получаем сообщения
        messages = []
        message_keys = r.keys("message:*")
        for msg_key in message_keys:
            if msg_key == "message:next_id":  # Пропускаем счетчик ID
                continue
                
            msg_data = r.hgetall(msg_key)
            if msg_data.get("user_id") == str(user_id):
                if "timestamp" in msg_data:
                    messages.append(f"{msg_data.get('timestamp')}: {msg_data.get('text', '')}")
                else:
                    messages.append(msg_data.get("text", ""))
        
        messages_text = "\n".join(messages) if messages else "Нет сообщений"
        
        # Добавляем пользователя в список
        users.append([user_id, user_data.get("name", "N/A"), user_data.get("login", "N/A"), friends_list, messages_text])
    
    # Вывод данных в виде таблицы
    if users:
        print(tabulate(users, headers=["ID", "Имя", "Логин", "Друзья", "Сообщения"], tablefmt="grid"))
    else:
        print("Нет пользователей в системе.")

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Неверный формат даты: {date_str}. Используйте формат ГГГГ-ММ-ДД.")
        return None

def main():
    # Подключаемся к Redis
    r = connect_to_redis()
    if not r:
        print("Невозможно продолжить без подключения к Redis.")
        return
    
    actions = {
        "1": ("Добавить пользователя", lambda: add_user(r, input("ID: "), input("Имя: "), input("Логин: "))),
        "2": ("Добавить сообщение", lambda: add_message(r, input("ID пользователя: "), input("Сообщение: "))),
        "3": ("Добавить друга", lambda: add_friend(r, input("ID пользователя: "), input("ID друга: "))),
        "4": ("Показать сообщения за период", lambda: show_messages_by_period(r)),
        "5": ("Показать упорядоченный список имен друзей", lambda: print("\n".join(get_sorted_friend_names(r, input("ID пользователя: "))) or "Нет друзей.")),
        "6": ("Показать количество друзей", lambda: print(f"Количество друзей: {count_friends(r, input('ID пользователя: '))}")),
        "7": ("Показать всех пользователей", lambda: show_users(r)),
        "8": ("Выход", exit)
    }
    
    def show_messages_by_period(r):
        user_id = input("ID пользователя: ")
        use_period = input("Фильтровать по дате? (y/n): ").lower() == 'y'
        
        if use_period:
            start_date_str = input("Начальная дата (ГГГГ-ММ-ДД): ")
            end_date_str = input("Конечная дата (ГГГГ-ММ-ДД): ")
            
            start_date = parse_date(start_date_str) if start_date_str else None
            end_date = parse_date(end_date_str) if end_date_str else None
            
            messages = get_messages_by_period(r, user_id, start_date, end_date)
        else:
            messages = get_messages_by_period(r, user_id)
        
        if messages:
            print("\nСообщения:")
            for msg in messages:
                print(f"- {msg}")
        else:
            print("Нет сообщений за указанный период.")
    
    while True:
        print("\nМеню:")
        for k, v in actions.items():
            print(f"{k}. {v[0]}")
        choice = input("Выберите действие: ")
        actions.get(choice, (None, lambda: print("Неверный выбор. Попробуйте снова.")))[1]()

if __name__ == "__main__":
    main()