import pymongo
from .connection_store import add_connection


def connect_mongo(uri):
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.server_info()

    add_connection("mongodb", {"uri": uri})
