import redis
from .connection_store import add_connection


def connect_redis(payload):
    r = redis.Redis(
        host=payload["host"],
        port=payload["port"],
        password=payload["password"],
        socket_connect_timeout=5
    )
    r.ping()

    add_connection("redis", payload)
