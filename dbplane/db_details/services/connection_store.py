import json
import os
# from ./logger import get_logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONN_FILE = os.path.join(BASE_DIR, "connections.json")


def load_connections():
    print("📁 USING JSON FILE:", CONN_FILE)
    if not os.path.exists(CONN_FILE):
        with open(CONN_FILE, "w") as f:
            json.dump(
                {
                    "postgresql": [],
                    "mongo": [],
                    "redis": [],
                    "rabbitmq": []
                },
                f,
                indent=4
            )

    with open(CONN_FILE, "r") as f:
        return json.load(f)


def save_connections(data):
    with open(CONN_FILE, "w") as f:
        json.dump(data, f, indent=4)


def add_connection(db_type, conn):
    print("👉 add_connection called")
    print("👉 db_type:", db_type)
    print("👉 conn:", conn)
    data = load_connections()
    print("👉 before save:", data)
    new_name = conn.get("display_name")
    for existing in data.get(db_type, []):
        if existing.get("display_name") == new_name:
            raise ValueError("Database name already exists")
    data[db_type].append(conn)
    save_connections(data)
    print("✅ after save:", data)

def delete_connection(db_type, index):
    data = load_connections()
    data[db_type].pop(index)
    save_connections(data)


def update_connection(db_type, index, new_conn):
    data = load_connections()
    data[db_type][index] = new_conn
    save_connections(data)
