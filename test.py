"""

import redis

def redis_string():
    try:
        r = redis.StrictRedis(
            host=redis_host, port=redis_port, decode_responses=True)
        r.set("message", "Hello, world!")
        msg = r.get("message")
        print(msg)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    redis_host = 'localhost'  # Укажите ваш хост Redis
    redis_port = 6379         # Укажите ваш порт Redis
    redis_string()

"""