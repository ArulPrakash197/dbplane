import psycopg2
from .connection_store import add_connection
from ..logger import get_logger


def connect_postgres(payload):
    conn = psycopg2.connect(
        host=payload["host"],
        port=payload["port"],
        database=payload["database"],
        user=payload["user"],
        password=payload["password"],
        connect_timeout=10
    )
    conn.close()

    add_connection("postgres", payload)

def test_postgres(payload):
    psycopg2.connect(
        host=payload["host"],
        port=payload["port"],
        database=payload["database"],
        password=payload["password"],
        connect_timeout=10
    )
