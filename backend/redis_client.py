import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def get_cache(key: str):
    return redis_client.get(key)

def set_cache(key: str, value: str, expire: int = 3600):
    redis_client.set(key, value, ex=expire)
