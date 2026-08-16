import json
import psycopg2
from pymongo import MongoClient
import redis
import requests
from .connection_store import *
from db_details.logger import get_logger

logger = get_logger("terminal_service", "terminal.log")

class VirtualTerminal:

    def __init__(self, db_type, index):
        self.db_type = db_type
        self.conn_data = get_connection(db_type, index)

    def execute(self, command):
        command = command.strip()

        if not command:
            return ""

        if self.db_type == "postgresql":
            return self._postgres(command)

        elif self.db_type == "mongo":
            return self._mongo(command)

        elif self.db_type == "redis":
            return self._redis(command)

        elif self.db_type == "rabbitmq":
            return self._rabbitmq(command)

        else:
            return "Unsupported database type"

    def _postgres(self, command):
        try:
        # -----------------------------------
        # 1. Handle meta commands (minimal)
        # -----------------------------------
            if command == "\\conninfo":
                return {
                    "message": f"""
    You are connected to database "{self.conn_data['database']}"
    as user "{self.conn_data['username']}"
    on host "{self.conn_data['host']}"
    port "{self.conn_data['port']}".
                    """.strip()
                }

            elif command.startswith("\\c "):
                new_db = command.split(" ")[1]
                self.conn_data["database"] = new_db
                return {"message": f"Switched to database '{new_db}'"}

            elif command == "\\l":
                command = "SELECT datname FROM pg_database WHERE datistemplate = false;"

            elif command == "\\dt":
                command = """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema='public';
                """

            elif command.startswith("\\d "):
                table = command.split(" ")[1]
                command = f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{table}';
                """

            # -----------------------------------
            # 2. Smart command parser 🚀
            # -----------------------------------
            command = self._parse_smart_command(command)

            # -----------------------------------
            # 3. Execute SQL
            # -----------------------------------
            conn = psycopg2.connect(
                host=self.conn_data["host"],
                port=self.conn_data["port"],
                database=self.conn_data["database"],
                user=self.conn_data["username"],
                password=self.conn_data["password"]
            )

            cursor = conn.cursor()
            cursor.execute(command)

            # -----------------------------------
            # 4. Format result
            # -----------------------------------
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

                result = {
                    "columns": columns,
                    "rows": rows
                }
            else:
                conn.commit()
                result = {
                    "columns": [],
                    "rows": [],
                    "message": "Query executed successfully."
                }

            cursor.close()
            conn.close()

            return result

        except Exception as e:
            logger.error(f"Postgres execution failed: {str(e)}", exc_info=True)
            return {"error": str(e)}
        
    
    def get_tables(self):
        if self.db_type == "postgresql":
            return self._postgres_tables()
        return []
    
    def _parse_smart_command(self, command):
        cmd = command.lower().strip()

        # -----------------------------------
        # Tables
        # -----------------------------------
        if cmd == "tables":
            return """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema='public';
            """

        # -----------------------------------
        # Describe table
        # -----------------------------------
        elif cmd.startswith("describe "):
            table = cmd.split(" ")[1]
            return f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table}';
            """

        # -----------------------------------
        # Count rows
        # -----------------------------------
        elif cmd.startswith("count "):
            table = cmd.split(" ")[1]
            return f"SELECT COUNT(*) FROM {table};"

        # -----------------------------------
        # Top rows
        # -----------------------------------
        elif cmd.startswith("top "):
            parts = cmd.split(" ")
            if len(parts) >= 3:
                limit = parts[1]
                table = parts[2]
                return f"SELECT * FROM {table} LIMIT {limit};"

        # -----------------------------------
        # Default → return as SQL
        # -----------------------------------
        return command
        
    def _mongo(self, command):
        try:
            payload = json.loads(command)
            uri = f"mongodb://{self.conn_data['user']}:{self.conn_data['password']}@{self.conn_data['host']}:{self.conn_data['port']}"
            client = MongoClient(uri)
            db = client[self.conn_data["database"]]
            collection = db[payload["collection"]]
            if payload["action"] == "find":
                result = list(collection.find(payload.get("filter", {})))
            elif payload["action"] == "insert":
                result = collection.insert_one(payload["document"]).inserted_id
            else:
                result = "Unsupported action"
            client.close()
            return str(result)
        except Exception as e:
            return f"ERROR: {str(e)}"
        
    def _redis(self, command):
        try:
            r = redis.Redis(
                host=self.conn_data["host"],
                port=self.conn_data["port"],
                password=self.conn_data["password"],
                decode_responses=True
            )
            parts = command.split()
            result = r.execute_command(parts[0], *parts[1:])
            return str(result)
        except Exception as e:
            return f"ERROR: {str(e)}"
        
    def _rabbitmq(self, command):
        try:
            if command == "status":
                url = f"http://{self.conn_data['host']}:15672/api/overview"
                response = requests.get(
                    url,
                    auth=(self.conn_data["user"], self.conn_data["password"])
                )
                return json.dumps(response.json(), indent=2)
            return "Unsupported RabbitMQ command"
        except Exception as e:
            return f"ERROR: {str(e)}"
        
    # def get_connection(db_type, index):
    #     data = load_connections()
    #     if db_type not in data:
    #         raise ValueError("Invalid database type")
    #     index = int(index)
    #     if index < 0 or index >= len(data[db_type]):
    #         raise ValueError("Invalid index")
    #     return data[db_type][index]
    
    def _postgres_tables(self):
        try:
            conn = psycopg2.connect(
                host=self.conn_data["host"],
                port=self.conn_data["port"],
                database=self.conn_data["database"],
                user=self.conn_data["username"],
                password=self.conn_data["password"]
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)

            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return tables

        except Exception as e:
            logger.error(f"Failed to fetch tables: {str(e)}", exc_info=True)
            return []
    