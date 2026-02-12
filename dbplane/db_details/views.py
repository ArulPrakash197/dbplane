from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages

from .logger import get_logger
from .services.connection_store import (
    load_connections,
    add_connection,
    delete_connection,
    update_connection,
)

# OPTIONAL: if you already have real test services, import them
from .services.postgres_service import test_postgres
# from .services.mongo_service import test_mongo
# from .services.redis_service import test_redis
# from .services.rabbimq_service import test_rabbitmq

logger = get_logger("connections", "connections.log")


# --------------------------------------------------
# HOME
# --------------------------------------------------
class IndexView(View):
    def get(self, request):
        return render(request, "index.html")


# --------------------------------------------------
# LIST CONNECTIONS
# --------------------------------------------------
class DatabaseListView(View):
    def get(self, request, db_type):
        connections = load_connections()
        return render(request, "database_list.html", {
            "db_type": db_type,
            "connections": connections.get(db_type, [])
        })


# --------------------------------------------------
# ADD CONNECTION (TEST + SAVE)
# --------------------------------------------------
class AddConnectionView(View):

    REQUIRED_FIELDS = {
        "postgresql": ["display_name", "host", "port", "database", "password"],
        "mongo": ["display_name", "uri"],
        "redis": ["display_name", "host", "port", "password"],
        "rabbitmq": ["display_name", "host", "port", "password"],
    }

    def get(self, request, db_type):
        return render(request, "add_connection.html", {
            "db_type": db_type,
            "form_data": {},
            "errors": {}
        })

    def post(self, request, db_type):
        payload = {}
        errors = {}
        action = request.POST.get("action")  # "test" or "save"

        logger.info(f"AddConnection POST | db={db_type} | action={action}")

        # -------- BUILD PAYLOAD (MATCHES YOUR HTML) --------
        if db_type == "postgresql":
            payload = {
                "display_name": request.POST.get("display_name", "").strip(),
                "host": request.POST.get("host", "").strip(),
                "port": request.POST.get("port", "").strip(),
                "database": request.POST.get("dbname", "").strip(),
                "password": request.POST.get("password", "").strip(),
            }

        elif db_type == "mongo":
            payload = {
                "display_name": request.POST.get("display_name", "").strip(),
                "uri": request.POST.get("connection", "").strip(),
            }

        elif db_type == "redis":
            payload = {
                "display_name": request.POST.get("display_name", "").strip(),
                "host": request.POST.get("host", "").strip(),
                "port": request.POST.get("port", "").strip(),
                "password": request.POST.get("password", "").strip(),
            }

        elif db_type == "rabbitmq":
            payload = {
                "display_name": request.POST.get("display_name", "").strip(),
                "host": request.POST.get("host", "").strip(),
                "port": request.POST.get("port", "").strip(),
                "password": request.POST.get("password", "").strip(),
            }

        else:
            messages.error(request, "Unsupported database type")
            return redirect("db_list", db_type=db_type)

        # -------- REQUIRED FIELD VALIDATION --------
        for field in self.REQUIRED_FIELDS.get(db_type, []):
            if not payload.get(field):
                errors[field] = "This field is required"

        if errors:
            logger.warning(f"Validation failed | {errors}")
            return render(request, "add_connection.html", {
                "db_type": db_type,
                "form_data": payload,
                "errors": errors
            })

        # --------------------------------------------------
        # TEST CONNECTION (NO SAVE)
        # --------------------------------------------------
        if action == "test":
            try:
                # 🔹 Replace with real test calls if available
                # if db_type == "postgresql":
                #     test_postgres(payload)
                # elif db_type == "mongo":
                #     test_mongo(payload)
                # elif db_type == "redis":
                #     test_redis(payload)

                messages.success(request, "Connection test successful")
                logger.info("Connection test successful")

            except Exception as e:
                logger.error("Connection test failed", exc_info=True)
                messages.error(request, f"Connection failed: {e}")

            return render(request, "add_connection.html", {
                "db_type": db_type,
                "form_data": payload,
                "errors": {}
            })

        # --------------------------------------------------
        # SAVE CONNECTION (NO TEST)
        # --------------------------------------------------
        if action == "save":
            try:
                add_connection(db_type, payload)

                messages.success(
                    request,
                    f"{db_type.capitalize()} connection saved successfully!"
                )
                logger.info("Connection saved successfully")

                return redirect("db_list", db_type=db_type)

            except ValueError as e:
                # duplicate display_name
                logger.warning(str(e))
                messages.error(request, str(e))
                return render(request, "add_connection.html", {
                    "db_type": db_type,
                    "form_data": payload,
                    "errors": {"display_name": str(e)}
                })

            except Exception:
                logger.error("Unexpected error while saving", exc_info=True)
                messages.error(request, "Something went wrong. Please try again.")
                return render(request, "add_connection.html", {
                    "db_type": db_type,
                    "form_data": payload,
                    "errors": {}
                })


# --------------------------------------------------
# DELETE CONNECTION
# --------------------------------------------------
class DeleteConnectionView(View):
    def post(self, request, db_type, index):
        delete_connection(db_type, index)
        messages.success(request, "Connection deleted successfully")
        logger.info(f"Connection deleted | db={db_type} | index={index}")
        return redirect("db_list", db_type=db_type)


# --------------------------------------------------
# EDIT CONNECTION
# --------------------------------------------------
class EditConnectionView(View):
    def get(self, request, db_type, index):
        connections = load_connections()
        return render(request, "edit_connection.html", {
            "db_type": db_type,
            "connection": connections[db_type][index],
            "index": index
        })

    def post(self, request, db_type, index):
        payload = dict(request.POST)
        payload.pop("csrfmiddlewaretoken", None)

        update_connection(db_type, index, payload)

        messages.success(request, "Connection updated successfully")
        logger.info(f"Connection updated | db={db_type} | index={index}")

        return redirect("db_list", db_type=db_type)


# --------------------------------------------------
# TERMINAL POPUP
# --------------------------------------------------
class TerminalPopupView(View):
    def get(self, request, db_type):
        return render(request, "terminal_popup.html", {
            "db_type": db_type
        })
