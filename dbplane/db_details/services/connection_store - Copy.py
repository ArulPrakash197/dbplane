import json
import os
# from ..logger import get_logger
from db_details.logger import get_logger

logger = get_logger("connection_store", "connections.log")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONN_FILE = os.path.join(BASE_DIR, "connections.json")


def load_connections():
    logger.info("Loading connections")
    if not os.path.exists(CONN_FILE):
        logger.warning("connections.json not found. Creating new file.")
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
    try:
        with open(CONN_FILE, "r") as f:
            data = json.load(f)
            logger.info("Connections loaded successfully")
            return data
    except Exception as e:
        logger.error(f"Failed to load connections: {e}", exc_info=True)
        raise


def save_connections(data):
    with open(CONN_FILE, "w") as f:
        json.dump(data, f, indent=4)
        logger.info("Saved Connections successfully")


def add_connection(db_type, conn):
    logger.info(f"Adding connection | db={db_type}")
    data = load_connections()
    new_name = conn.get("display_name")
    for existing in data.get(db_type, []):
        if existing.get("display_name") == new_name:
            logger.warning(f"Duplicate connection name: {new_name}")
            raise ValueError("Display name already exists")
    data[db_type].append(conn)
    save_connections(data)
    logger.info(f"Connection added successfully | db={db_type} | name={new_name}")

def delete_connection(db_type, index):
    logger.info(f"Deleting connection | db={db_type} | index={index}")
    data = load_connections()
    if db_type not in data:
        logger.error(f"Invalid db_type: {db_type}")
        raise ValueError("Invalid database type")
    index = int(index)
    if index < 0 or index >= len(data[db_type]):
        logger.error(f"Invalid index: {index} for db={db_type}")
        raise ValueError("Invalid index")
    deleted = data[db_type].pop(index)
    save_connections(data)
    logger.info(f"Connection deleted | db={db_type} | name={deleted.get('display_name')}")


def update_connection(db_type, index, new_conn):
    logger.info(f"Updating connection | db={db_type} | index={index}")
    data = load_connections()
    if db_type not in data:
        raise ValueError("Invalid database type")
    index = int(index)
    if index < 0 or index >= len(data[db_type]):
        raise ValueError("Invalid index")
    new_name = new_conn.get("display_name")
    for i, existing in enumerate(data[db_type]):
        if i != index and existing.get("display_name", "").lower() == new_name.lower():
            raise ValueError("Database name already exists")
    data[db_type][index] = new_conn
    save_connections(data)
    logger.info(f"Connection updated successfully | db={db_type}")

def get_connection(db_type, index):
    logger.info(f"Fetching connection | db={db_type} | index={index}")
    data = load_connections()
    if db_type not in data:
        logger.error(f"Invalid db_type: {db_type}")
        raise ValueError("Invalid database type")
    index = int(index)
    if index < 0 or index >= len(data[db_type]):
        logger.error(f"Invalid index: {index} for db={db_type}")
        raise ValueError("Invalid index")
    conn = data[db_type][index]
    logger.info(f"Connection fetched | db={db_type} | name={conn.get('display_name')}")
    return conn
