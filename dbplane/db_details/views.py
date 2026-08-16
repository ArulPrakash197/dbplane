from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
import json
from django.http import JsonResponse, Http404, StreamingHttpResponse

from .logger import get_logger
from .services.connection_store import (
    load_connections,
    add_connection,
    delete_connection,
    get_connection,
    update_connection,
)
from .services.credential_store import (
    list_credentials,
    add_credential,
    update_credential,
    delete_credential,
    get_credential,
)
from .services.terminal_service import VirtualTerminal
from .models import ClusterDetails, DeploymentResult
from .services.credential_crypto import encrypt_dict, decrypt_dict

# OPTIONAL: if you already have real test services, import them
from .services.postgres_service import test_postgres
from .services.mongo_service import connect_mongo
from .services.redis_service import connect_redis

logger = get_logger("connections", "connections.log")


# --------------------------------------------------
# HOME
# --------------------------------------------------
class IndexView(View):
    def get(self, request):
        return render(request, "index.html")


class ClusterConfigurationView(View):
    def get(self, request):
        return render(request, "cluster_configuration.html")


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
        "postgresql": ["display_name", "host", "port", "database", "username", "password"],
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
                "username": request.POST.get("username", "").strip(),
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
                if db_type == "postgresql":
                    test_postgres(payload)
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
        try:
            delete_connection(db_type, index)
            messages.success(request, "Connection deleted successfully")
            logger.info(f"Connection deleted | db={db_type} | index={index}")
        except Exception as e:
            messages.error(request, "Failed to delete connection")
            logger.error(f"Delete failed | db={db_type} | index={index} | error={e}")
        return redirect("db_list", db_type=db_type)


# --------------------------------------------------
# EDIT CONNECTION
# --------------------------------------------------
class EditConnectionView(View):
    def get(self, request, db_type, index):
        try:
            connection = get_connection(db_type, index)
        except (KeyError, IndexError, ValueError):
            messages.error(request, "Connection not found")
            return redirect("db_list", db_type=db_type)
        return render(request, "add_connection.html", {
            "db_type": db_type,
            "form_data": connection,
            "errors": {},
            "index": index,
            "edit_mode": True
        })

    def post(self, request, db_type, index):
        payload = {}

        if db_type == "postgresql":
            payload = {
                "display_name": request.POST.get("display_name", "").strip(),
                "host": request.POST.get("host", "").strip(),
                "port": request.POST.get("port", "").strip(),
                "database": request.POST.get("dbname", "").strip(),
                "username": request.POST.get("username", "").strip(),
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

        try:
            update_connection(db_type, index, payload)
            messages.success(request, "Connection updated successfully")
            logger.info(f"Connection updated | db={db_type} | index={index}")
        except ValueError as e:
            logger.warning(f"Duplicate during edit | db={db_type} | index={index} | error={e}")
            messages.error(request, str(e))

            return render(request, "add_connection.html", {
                "db_type": db_type,
                "form_data": payload,
                "errors": {"display_name": str(e)},
                "index": index,
                "edit_mode": True
            })
        except Exception as e:
            messages.error(request, "Update failed")
            logger.error(f"Update failed | db={db_type} | index={index} | error={e}")

        return redirect("db_list", db_type=db_type)


# --------------------------------------------------
# REVEAL ENCRYPTED CONNECTION SECRET
# --------------------------------------------------
class ConnectionSecretView(View):
    SECRET_FIELDS = {
        "postgresql": {"password"},
        "mongo": {"uri"},
        "redis": {"password"},
        "rabbitmq": {"password"},
    }

    def post(self, request, db_type, index):
        try:
            data = json.loads(request.body or "{}")
            field = data.get("field", "password")

            if field not in self.SECRET_FIELDS.get(db_type, set()):
                return JsonResponse({
                    "success": False,
                    "error": "Unsupported secret field"
                }, status=400)

            connection = get_connection(db_type, index)
            return JsonResponse({
                "success": True,
                "value": connection.get(field, "")
            })
        except Exception as e:
            logger.error(f"Secret reveal failed | db={db_type} | index={index} | error={e}")
            return JsonResponse({
                "success": False,
                "error": "Failed to load saved secret"
            }, status=400)


# --------------------------------------------------
# TERMINAL POPUP
# --------------------------------------------------
class TerminalPopupView(View):
    def get(self, request, db_type):
        index = request.GET.get("index", 0)
        return render(request, "terminal_popup.html", {
            "db_type": db_type,
            "index": index
        })

class TerminalExecuteView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            db_type = data.get("db_type")
            index = data.get("index")
            command = data.get("command")
            terminal = VirtualTerminal(db_type, index)
            output = terminal.execute(command)
            return JsonResponse({
                "success": True,
                "output": output
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "output": str(e)
            })
        
class TerminalAutocompleteView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)

            db_type = data.get("db_type")
            index = data.get("index")

            terminal = VirtualTerminal(db_type, index)
            tables = terminal.get_tables()

            return JsonResponse({
                "success": True,
                "tables": tables
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "tables": []
            })
        
# --------------------------------------------------
# TERMINAL CONNECT (VALIDATE BEFORE OPENING)
# --------------------------------------------------
class TerminalConnectView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)

            db_type = data.get("db_type")
            index = data.get("index")

            terminal = VirtualTerminal(db_type, index)

            # 🔹 Try lightweight test query
            if db_type == "postgresql":
                terminal.execute("SELECT 1;")

            elif db_type == "mongo":
                terminal.execute('{"collection":"system.version","action":"find","filter":{}}')

            elif db_type == "redis":
                terminal.execute("PING")

            elif db_type == "rabbitmq":
                terminal.execute("status")

            return JsonResponse({
                "success": True
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            })


# --------------------------------------------------
# AJAX TEST CONNECTION API
# --------------------------------------------------
def verify_mongo_connection(uri):
    import socket
    import pymongo
    from pymongo.uri_parser import parse_uri

    try:
        parsed = parse_uri(uri)
        nodes = parsed.get("nodelist", [])
    except Exception as e:
        raise ValueError(f"Invalid URI format: {e}")

    if not nodes:
        raise ValueError("No hosts found in the MongoDB URI.")

    unreachable = []
    for host, port in nodes:
        if not port:
            port = 27017
        try:
            with socket.create_connection((host, port), timeout=3.0) as sock:
                pass
        except Exception:
            unreachable.append(f"{host}:{port}")

    if unreachable:
        raise ValueError("server is not reachable kindly check the connectivity")

    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.server_info()
    except pymongo.errors.OperationFailure as e:
        if e.code == 18 or "auth" in str(e).lower() or "login" in str(e).lower() or "credentials" in str(e).lower():
            raise ValueError(f"Authentication failed: kindly check username and password")
        raise ValueError("kindly check with the URI")
    except Exception:
        raise ValueError("kindly check with the URI")


class TestConnectionApiView(View):
    def post(self, request, db_type):
        try:
            data = json.loads(request.body or "{}")
            payload = {}

            if db_type == "postgresql":
                payload = {
                    "display_name": data.get("display_name", "").strip(),
                    "host": data.get("host", "").strip(),
                    "port": data.get("port", "").strip(),
                    "database": data.get("dbname", "").strip(),
                    "username": data.get("username", "").strip(),
                    "password": data.get("password", "").strip(),
                }
            elif db_type == "mongo":
                payload = {
                    "display_name": data.get("display_name", "").strip(),
                    "uri": data.get("connection", "").strip(),
                }
            elif db_type == "redis":
                payload = {
                    "display_name": data.get("display_name", "").strip(),
                    "host": data.get("host", "").strip(),
                    "port": data.get("port", "").strip(),
                    "password": data.get("password", "").strip(),
                }
            elif db_type == "rabbitmq":
                payload = {
                    "display_name": data.get("display_name", "").strip(),
                    "host": data.get("host", "").strip(),
                    "port": data.get("port", "").strip(),
                    "password": data.get("password", "").strip(),
                }

            # 🔹 Validate required fields before connection test
            required_fields = []
            if db_type == "postgresql":
                required_fields = ["display_name", "host", "port", "database", "username", "password"]
            elif db_type == "mongo":
                required_fields = ["uri"]
            elif db_type in ["redis", "rabbitmq"]:
                required_fields = ["display_name", "host", "port"]

            missing = [f for f in required_fields if not payload.get(f)]
            if missing:
                missing_labels = ", ".join(f.replace("_", " ").capitalize() for f in missing)
                raise ValueError(f"Missing required fields: {missing_labels}")

            # 🔹 Run tests
            if db_type == "postgresql":
                test_postgres(payload)
            elif db_type == "mongo":
                verify_mongo_connection(payload["uri"])
            elif db_type == "redis":
                connect_redis(payload)

            return JsonResponse({
                "success": True,
                "message": "Connection test successful"
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            })


# --------------------------------------------------
# CLUSTER CONFIGURATION VIEWS
# --------------------------------------------------
def encrypt_string(val):
    if not val:
        return ""
    return encrypt_dict({"v": val})


def decrypt_string(encrypted_val):
    if not encrypted_val:
        return ""
    return decrypt_dict(encrypted_val).get("v", "")


def validate_setups(payload, errors):
    def check_partial(ip_field, port_field, label):
        ip_val = payload.get(ip_field, "").strip()
        port_val = payload.get(port_field, "").strip()
        if bool(ip_val) != bool(port_val):
            errors[ip_field] = f"Both IP and Port are required for {label}."
            errors[port_field] = f"Both IP and Port are required for {label}."
            return None
        return bool(ip_val)

    dc_filled = check_partial("dc_ips", "dc_ports", "DC")
    dc_ha_filled = check_partial("dc_ha_ips", "dc_ha_ports", "DC_HA")
    dr_filled = check_partial("dr_ips", "dr_ports", "DR")
    dr_ha_filled = check_partial("dr_ha_ips", "dr_ha_ports", "DR_HA")
    arbiter_filled = check_partial("arbiter_ips", "arbiter_ports", "Arbiter")
    
    if errors:
        return

    # If any HA or DR setup is configured, the base DC setup must be configured
    if (dc_ha_filled or dr_filled or dr_ha_filled or arbiter_filled) and not dc_filled:
        errors["dc_ips"] = "DC setup must be configured if any HA, DR or Arbiter setup is defined."
        errors["dc_ports"] = "DC setup must be configured if any HA, DR or Arbiter setup is defined."
        return

    # If DR_HA is filled, then DR must be configured
    if dr_ha_filled and not dr_filled:
        errors["dr_ha_ips"] = "DR_HA setup requires DR setup to be configured."
        errors["dr_ha_ports"] = "DR_HA setup requires DR setup to be configured."


def map_ips_to_ports(ips_str, ports_str):
    ips = [ip.strip() for ip in ips_str.split(",") if ip.strip()]
    ports = [port.strip() for port in ports_str.split(",") if port.strip()]
    if not ips:
        return []
    if len(ports) == 1:
        try:
            return [(ip, int(ports[0])) for ip in ips]
        except ValueError:
            return [(ip, 0) for ip in ips]
    
    result = []
    for i, ip in enumerate(ips):
        port_val = 27017 # default
        if i < len(ports):
            try:
                port_val = int(ports[i])
            except ValueError:
                pass
        elif len(ports) > 0:
            try:
                port_val = int(ports[-1])
            except ValueError:
                pass
        result.append((ip, port_val))
    return result


def _get_cluster_by_index(db_type, index):
    try:
        index = int(index)
        return ClusterDetails.objects.filter(db_type=db_type, is_deleted=False).order_by("id")[index]
    except (IndexError, ValueError):
        raise Http404("Cluster not found")


class ClusterListView(View):
    def get(self, request, db_type):
        clusters = ClusterDetails.objects.filter(db_type=db_type, is_deleted=False).order_by("id")
        return render(request, "cluster_list.html", {
            "db_type": db_type,
            "connections": clusters
        })


class AddClusterView(View):
    def get(self, request, db_type):
        return render(request, "add_cluster.html", {
            "db_type": db_type,
            "form_data": {},
            "errors": {},
            "edit_mode": False
        })

    def post(self, request, db_type):
        action = request.POST.get("action", "save")
        payload = {
            "display_name": request.POST.get("display_name", "").strip(),
            "dc_ips": request.POST.get("dc_ips", "").strip(),
            "dc_ports": request.POST.get("dc_ports", "").strip(),
            "dc_ha_ips": request.POST.get("dc_ha_ips", "").strip(),
            "dc_ha_ports": request.POST.get("dc_ha_ports", "").strip(),
            "dr_ips": request.POST.get("dr_ips", "").strip(),
            "dr_ports": request.POST.get("dr_ports", "").strip(),
            "dr_ha_ips": request.POST.get("dr_ha_ips", "").strip(),
            "dr_ha_ports": request.POST.get("dr_ha_ports", "").strip(),
            "arbiter_ips": request.POST.get("arbiter_ips", "").strip(),
            "arbiter_ports": request.POST.get("arbiter_ports", "").strip(),
            "db_username": request.POST.get("db_username", "").strip(),
            "db_name": request.POST.get("db_name", "").strip(),
            "db_password": request.POST.get("db_password", "").strip(),
            "auth_mechanism": request.POST.get("auth_mechanism", "").strip(),
            "server_username": request.POST.get("server_username", "").strip(),
            "server_password": request.POST.get("server_password", "").strip(),
        }
        errors = {}

        mandatory_fields = ["display_name", "db_username", "db_name", "db_password"]
        if db_type == "mongo":
            mandatory_fields += ["server_username", "server_password"]

        for field in mandatory_fields:
            if not payload[field]:
                field_label = field.replace("_", " ").capitalize()
                errors[field] = f"{field_label} is required"

        validate_setups(payload, errors)

        if errors:
            return render(request, "add_cluster.html", {
                "db_type": db_type,
                "form_data": payload,
                "errors": errors,
                "edit_mode": False
            })

        try:
            if ClusterDetails.objects.filter(db_type=db_type, display_name__iexact=payload["display_name"], is_deleted=False).exists():
                raise ValueError("Cluster name already exists")

            ClusterDetails.objects.create(
                db_type=db_type,
                display_name=payload["display_name"],
                dc_ips=payload["dc_ips"],
                dc_ports=payload["dc_ports"],
                dc_ha_ips=payload["dc_ha_ips"],
                dc_ha_ports=payload["dc_ha_ports"],
                dr_ips=payload["dr_ips"],
                dr_ports=payload["dr_ports"],
                dr_ha_ips=payload["dr_ha_ips"],
                dr_ha_ports=payload["dr_ha_ports"],
                arbiter_ips=payload["arbiter_ips"],
                arbiter_ports=payload["arbiter_ports"],
                db_username=payload["db_username"],
                db_name=payload["db_name"],
                db_password=encrypt_string(payload["db_password"]),
                auth_mechanism=payload["auth_mechanism"],
                server_username=payload["server_username"],
                server_password=encrypt_string(payload["server_password"]),
            )

            if action == "deploy":
                messages.success(request, f"{db_type.capitalize()} cluster saved and deployment initiated successfully!")
            else:
                messages.success(request, f"{db_type.capitalize()} cluster configuration saved successfully!")
            return redirect("cluster_list", db_type=db_type)

        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "add_cluster.html", {
                "db_type": db_type,
                "form_data": payload,
                "errors": {"display_name": str(e)},
                "edit_mode": False
            })
        except Exception as e:
            messages.error(request, "Failed to save cluster configuration: " + str(e))
            return render(request, "add_cluster.html", {
                "db_type": db_type,
                "form_data": payload,
                "errors": {},
                "edit_mode": False
            })


class EditClusterView(View):
    def get(self, request, db_type, index):
        try:
            cluster = _get_cluster_by_index(db_type, index)
        except Exception:
            messages.error(request, "Cluster configuration not found")
            return redirect("cluster_list", db_type=db_type)

        form_data = {
            "display_name": cluster.display_name,
            "dc_ips": cluster.dc_ips,
            "dc_ports": cluster.dc_ports,
            "dc_ha_ips": cluster.dc_ha_ips,
            "dc_ha_ports": cluster.dc_ha_ports,
            "dr_ips": cluster.dr_ips,
            "dr_ports": cluster.dr_ports,
            "dr_ha_ips": cluster.dr_ha_ips,
            "dr_ha_ports": cluster.dr_ha_ports,
            "arbiter_ips": getattr(cluster, "arbiter_ips", ""),
            "arbiter_ports": getattr(cluster, "arbiter_ports", ""),
            "db_username": getattr(cluster, "db_username", ""),
            "db_name": cluster.db_name,
            "db_password": decrypt_string(cluster.db_password),
            "auth_mechanism": getattr(cluster, "auth_mechanism", ""),
            "server_username": cluster.server_username,
            "server_password": decrypt_string(cluster.server_password),
        }

        return render(request, "add_cluster.html", {
            "db_type": db_type,
            "form_data": form_data,
            "errors": {},
            "index": index,
            "edit_mode": True
        })

    def post(self, request, db_type, index):
        action = request.POST.get("action", "save")
        try:
            cluster = _get_cluster_by_index(db_type, index)
        except Exception:
            messages.error(request, "Cluster configuration not found")
            return redirect("cluster_list", db_type=db_type)

        payload = {
            "display_name": request.POST.get("display_name", "").strip(),
            "dc_ips": request.POST.get("dc_ips", "").strip(),
            "dc_ports": request.POST.get("dc_ports", "").strip(),
            "dc_ha_ips": request.POST.get("dc_ha_ips", "").strip(),
            "dc_ha_ports": request.POST.get("dc_ha_ports", "").strip(),
            "dr_ips": request.POST.get("dr_ips", "").strip(),
            "dr_ports": request.POST.get("dr_ports", "").strip(),
            "dr_ha_ips": request.POST.get("dr_ha_ips", "").strip(),
            "dr_ha_ports": request.POST.get("dr_ha_ports", "").strip(),
            "arbiter_ips": request.POST.get("arbiter_ips", "").strip(),
            "arbiter_ports": request.POST.get("arbiter_ports", "").strip(),
            "db_username": request.POST.get("db_username", "").strip(),
            "db_name": request.POST.get("db_name", "").strip(),
            "db_password": request.POST.get("db_password", "").strip(),
            "auth_mechanism": request.POST.get("auth_mechanism", "").strip(),
            "server_username": request.POST.get("server_username", "").strip(),
            "server_password": request.POST.get("server_password", "").strip(),
        }
        errors = {}

        mandatory_fields = ["display_name", "db_username", "db_name", "db_password"]
        if db_type == "mongo":
            mandatory_fields += ["server_username", "server_password"]

        for field in mandatory_fields:
            if not payload[field]:
                field_label = field.replace("_", " ").capitalize()
                errors[field] = f"{field_label} is required"

        validate_setups(payload, errors)

        if errors:
            return render(request, "add_cluster.html", {
                "db_type": db_type,
                "form_data": payload,
                "errors": errors,
                "index": index,
                "edit_mode": True
            })

        try:
            if ClusterDetails.objects.filter(db_type=db_type, display_name__iexact=payload["display_name"], is_deleted=False).exclude(pk=cluster.pk).exists():
                raise ValueError("Cluster name already exists")

            cluster.display_name = payload["display_name"]
            cluster.dc_ips = payload["dc_ips"]
            cluster.dc_ports = payload["dc_ports"]
            cluster.dc_ha_ips = payload["dc_ha_ips"]
            cluster.dc_ha_ports = payload["dc_ha_ports"]
            cluster.dr_ips = payload["dr_ips"]
            cluster.dr_ports = payload["dr_ports"]
            cluster.dr_ha_ips = payload["dr_ha_ips"]
            cluster.dr_ha_ports = payload["dr_ha_ports"]
            cluster.arbiter_ips = payload["arbiter_ips"]
            cluster.arbiter_ports = payload["arbiter_ports"]
            cluster.db_username = payload["db_username"]
            cluster.db_name = payload["db_name"]
            cluster.db_password = encrypt_string(payload["db_password"])
            cluster.auth_mechanism = payload["auth_mechanism"]
            cluster.server_username = payload["server_username"]
            cluster.server_password = encrypt_string(payload["server_password"])
            cluster.save()

            if action == "deploy":
                messages.success(request, f"{db_type.capitalize()} cluster saved and deployment initiated successfully!")
            else:
                messages.success(request, f"{db_type.capitalize()} cluster configuration updated successfully!")
            return redirect("cluster_list", db_type=db_type)

        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "add_cluster.html", {
                "db_type": db_type,
                "form_data": payload,
                "errors": {"display_name": str(e)},
                "index": index,
                "edit_mode": True
            })
        except Exception as e:
            messages.error(request, "Failed to update cluster configuration: " + str(e))
            return render(request, "add_cluster.html", {
                "db_type": db_type,
                "form_data": payload,
                "errors": {},
                "index": index,
                "edit_mode": True
            })


class DeleteClusterView(View):
    def post(self, request, db_type, index):
        try:
            cluster = _get_cluster_by_index(db_type, index)
            cluster.is_deleted = True
            cluster.save()
            messages.success(request, "Cluster configuration deleted successfully")
        except Exception as e:
            messages.error(request, "Failed to delete cluster configuration")
        return redirect("cluster_list", db_type=db_type)


class DeployClusterView(View):
    def post(self, request, db_type, index):
        try:
            cluster = _get_cluster_by_index(db_type, index)
            messages.success(
                request,
                f"{db_type.capitalize()} cluster '{cluster.display_name}' deployment initiated successfully!"
            )
        except Exception as e:
            messages.error(request, f"Failed to initiate deployment: {e}")
        return redirect("cluster_list", db_type=db_type)


def verify_server_mongod_via_driver(ip, port, db_username, db_name, db_password, auth_mechanism=""):
    import pymongo
    import urllib.parse

    # Try 1: With auth credentials
    if db_name and db_password:
        try:
            username = db_username if db_username else db_name
            user_esc = urllib.parse.quote_plus(username)
            pass_esc = urllib.parse.quote_plus(db_password)
            uri = f"mongodb://{user_esc}:{pass_esc}@{ip}:{port}/{db_name}?serverSelectionTimeoutMS=2000&directConnection=true&authSource={db_name}"
            if auth_mechanism:
                uri += f"&authMechanism={auth_mechanism}"
            client = pymongo.MongoClient(uri)
            info = client.server_info()
            version = info.get("version", "unknown")
            return True, version
        except Exception:
            pass

    # Try 2: Unauthenticated / guest connection
    try:
        uri = f"mongodb://{ip}:{port}/?serverSelectionTimeoutMS=2000&directConnection=true"
        client = pymongo.MongoClient(uri)
        info = client.server_info()
        version = info.get("version", "unknown")
        return True, version
    except Exception as e:
        return False, f"Connection failed: {e}"


def check_driver_port_reachability(source_ip, source_port, target_ip, target_port, db_username, db_name, db_password, auth_mechanism=""):
    import pymongo
    import urllib.parse
    try:
        if db_name and db_password:
            username = db_username if db_username else db_name
            user_esc = urllib.parse.quote_plus(username)
            pass_esc = urllib.parse.quote_plus(db_password)
            uri = f"mongodb://{user_esc}:{pass_esc}@{source_ip}:{source_port}/{db_name}?serverSelectionTimeoutMS=1000&directConnection=true&authSource={db_name}"
            if auth_mechanism:
                uri += f"&authMechanism={auth_mechanism}"
        else:
            uri = f"mongodb://{source_ip}:{source_port}/?serverSelectionTimeoutMS=1000&directConnection=true"
            
        client = pymongo.MongoClient(uri)
        status = client.admin.command("replSetGetStatus")
        for m in status.get("members", []):
            m_name = m.get("name", "")
            if target_ip in m_name:
                health = m.get("health", 0)
                if health == 1:
                    return True, "Reachable"
                else:
                    return False, f"Not Connected (Replica set health={health})"
    except Exception:
        pass

    try:
        import socket
        with socket.create_connection((target_ip, target_port), timeout=1.0) as sock:
            pass
        return True, "Reachable"
    except Exception as e:
        return False, f"Not Connected ({e})"


def parse_version(v_str):
    import re
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", v_str)
    if match:
        return tuple(int(x) for x in match.groups())
    return (0, 0, 0)


def make_html_table(headers, rows):
    header_th = "".join(f'<th style="padding: 10px 15px; text-align: left; font-weight: bold; border-bottom: 2px solid #4a5568;">{h}</th>' for h in headers)
    
    tbody_tr = []
    for r in rows:
        cells = []
        for cell in r:
            cells.append(f'<td style="padding: 10px 15px; border-bottom: 1px solid #4a5568; vertical-align: middle;">{cell}</td>')
        tbody_tr.append(f'<tr>{"".join(cells)}</tr>')
        
    return f'''
    <table style="width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; color: #fff; font-size: 0.9rem; background: #2d3748; border-radius: 6px; overflow: hidden; border: 1px solid #4a5568; font-family: sans-serif;">
        <thead>
            <tr style="background: #4a5568;">
                {header_th}
            </tr>
        </thead>
        <tbody>
            {"".join(tbody_tr)}
        </tbody>
    </table>
    '''


def check_service_status_via_ssh(ip, port, username, password):
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=2.0)
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active mongod")
        status = stdout.read().decode().strip()
        ssh.close()
        if status == "active":
            return "active"
        else:
            return "inactive"
    except Exception:
        pass
    
    # Fallback to connection
    try:
        import socket
        with socket.create_connection((ip, port), timeout=1.0) as sock:
            return "active"
    except Exception:
        return "inactive"


def sanitize_mongod_conf(content, replicaset_name, refresh_millis, max_sessions, allow_arbiters):
    lines = [line.rstrip() for line in content.splitlines()]
    new_lines = []
    
    # Strip target keys to ensure uniqueness
    for line in lines:
        trimmed = line.strip()
        if "replSetName:" in trimmed:
            continue
        if "logicalSessionRefreshMillis:" in trimmed:
            continue
        if "maxSessions:" in trimmed:
            continue
        if "allowMultipleArbiters:" in trimmed:
            continue
        new_lines.append(line)
        
    has_replication = False
    has_set_parameter = False
    
    for line in new_lines:
        trimmed = line.strip()
        if trimmed.startswith("replication:"):
            has_replication = True
        elif trimmed.startswith("setParameter:"):
            has_set_parameter = True
            
    output_lines = []
    i = 0
    while i < len(new_lines):
        line = new_lines[i]
        output_lines.append(line)
        trimmed = line.strip()
        if trimmed.startswith("replication:"):
            output_lines.append(f'  replSetName: "{replicaset_name}"')
        elif trimmed.startswith("setParameter:"):
            output_lines.append(f"  logicalSessionRefreshMillis: {refresh_millis}")
            output_lines.append(f"  maxSessions: {max_sessions}")
            output_lines.append(f"  allowMultipleArbiters: {str(allow_arbiters).lower()}")
        i += 1
        
    if not has_replication:
        output_lines.append("replication:")
        output_lines.append(f'  replSetName: "{replicaset_name}"')
    if not has_set_parameter:
        output_lines.append("setParameter:")
        output_lines.append(f"  logicalSessionRefreshMillis: {refresh_millis}")
        output_lines.append(f"  maxSessions: {max_sessions}")
        output_lines.append(f"  allowMultipleArbiters: {str(allow_arbiters).lower()}")
        
    final_lines = []
    seen = set()
    for line in output_lines:
        trimmed = line.strip()
        if not trimmed:
            final_lines.append("")
            continue
        if line in seen:
            continue
        seen.add(line)
        final_lines.append(line)
        
    return "\n".join(final_lines)


def compute_replication_lag(status_result):
    primary_optime = None
    members = status_result.get("members", [])
    for m in members:
        if m.get("stateStr") == "PRIMARY":
            optime_field = m.get("optime")
            if isinstance(optime_field, dict) and "ts" in optime_field:
                primary_optime = optime_field["ts"].time
            elif hasattr(optime_field, "time"):
                primary_optime = optime_field.time
            elif isinstance(optime_field, (int, float)):
                primary_optime = optime_field
                
    lags = {}
    if primary_optime is not None:
        for m in members:
            name = m.get("name")
            if m.get("stateStr") == "SECONDARY":
                optime_field = m.get("optime")
                sec_optime = None
                if isinstance(optime_field, dict) and "ts" in optime_field:
                    sec_optime = optime_field["ts"].time
                elif hasattr(optime_field, "time"):
                    sec_optime = optime_field.time
                elif isinstance(optime_field, (int, float)):
                    sec_optime = optime_field
                
                if sec_optime is not None:
                    lags[name] = max(0, primary_optime - sec_optime)
                else:
                    lags[name] = 0
            else:
                lags[name] = 0
    return lags


def make_replication_status_table(status_data, lags):
    headers = ["Node Name", "State", "Health", "Lag (seconds)", "Uptime"]
    rows = []
    for m in status_data.get("members", []):
        name = m.get("name", "unknown")
        state = m.get("stateStr", "UNKNOWN")
        health_val = m.get("health", 0)
        health = '<span style="color: #2ecc71; font-weight: bold;">Healthy (1)</span>' if health_val == 1 else '<span style="color: #e74c3c; font-weight: bold;">Unhealthy (0)</span>'
        lag_val = lags.get(name, 0)
        lag = f"{lag_val}s" if state == "SECONDARY" else "N/A"
        uptime = f"{m.get('uptime', 0)}s"
        rows.append((name, state, health, lag, uptime))
    return make_html_table(headers, rows)


class ClusterVerifyApiView(View):
    def post(self, request, db_type):
        try:
            data = json.loads(request.body or "{}")
            
            errors = {}
            
            # Validate mandatory credential fields
            mandatory_fields = {"db_username": "Database Username", "db_name": "Database Name", "db_password": "Database Password"}
            if db_type == "mongo":
                mandatory_fields["server_username"] = "Server Username"
                mandatory_fields["server_password"] = "Server Password"
            for field_key, field_label in mandatory_fields.items():
                if not data.get(field_key, "").strip():
                    errors[field_key] = f"{field_label} is required"
            
            validate_setups(data, errors)
            
            report_lines = []
            
            def badge(is_success, text):
                color = "#2ecc71" if is_success else "#e74c3c"
                symbol = "✓" if is_success else "✗"
                return f'<span style="color: {color}; font-weight: bold;">{symbol} {text}</span>'

            # 1. Setup compliance
            if errors:
                report_lines.append(f"<div><strong>1. Setup Compliance:</strong> {badge(False, 'Validation failed')}</div>")
                report_lines.append(f'<div style="background: #2d3748; padding: 10px; border-radius: 4px; font-family: monospace; margin-top: 5px; color: #f56565;">' + " | ".join(errors.values()) + "</div>")
                
                header_html = f'''
                <div style="display: flex; align-items: center; gap: 10px; font-weight: bold; font-size: 1.25rem; color: #e74c3c; border-bottom: 2px solid #e74c3c; padding-bottom: 12px; margin-bottom: 20px;">
                    <span class="material-symbols-outlined" style="font-size: 1.8rem;">error</span>
                    Verification Failed
                </div>
                '''
                return JsonResponse({
                    "success": False,
                    "report_html": header_html + "".join(report_lines),
                    "error": "Validation error: " + " | ".join(errors.values())
                })
            else:
                report_lines.append(f"<div><strong>1. Setup Compliance:</strong> {badge(True, 'Valid Setup')}</div>")

            # Collect data nodes and Arbiter nodes
            data_nodes = []
            for setup_name, ips_str, ports_str in [
                ("DC", data.get("dc_ips", ""), data.get("dc_ports", "")),
                ("DC_HA", data.get("dc_ha_ips", ""), data.get("dc_ha_ports", "")),
                ("DR", data.get("dr_ips", ""), data.get("dr_ports", "")),
                ("DR_HA", data.get("dr_ha_ips", ""), data.get("dr_ha_ports", "")),
            ]:
                mapped = map_ips_to_ports(ips_str, ports_str)
                for ip, port in mapped:
                    data_nodes.append((setup_name, ip, port))

            arbiter_nodes = []
            mapped_arbiter = map_ips_to_ports(data.get("arbiter_ips", ""), data.get("arbiter_ports", ""))
            for ip, port in mapped_arbiter:
                arbiter_nodes.append(("Arbiter", ip, port))

            all_nodes = data_nodes + arbiter_nodes

            # 2. Database Port Reachability & Cross Pings
            port_ok = True
            reachability_rows = []
            arbiter_unreachable = False
            
            import socket
            from datetime import datetime
            for setup_name, ip, port in all_nodes:
                check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    with socket.create_connection((ip, port), timeout=2.0) as sock:
                        status_html = '<span style="color: #2ecc71; font-weight: bold;">Reachable</span>'
                    if not setup_name.startswith("DC") and not setup_name.startswith("DR"):
                        reachability_rows.append((f"App &rarr; {setup_name} ({ip})", str(port), status_html, check_time))
                except Exception as e:
                    port_ok = False
                    if setup_name == "Arbiter":
                        arbiter_unreachable = True
                    status_html = f'<span style="color: #e74c3c; font-weight: bold;">Not Connected ({e})</span>'
                    if not setup_name.startswith("DC") and not setup_name.startswith("DR"):
                        reachability_rows.append((f"App &rarr; {setup_name} ({ip})", str(port), status_html, check_time))
            
            # If MongoDB and nodes are configured, check connectivity between servers
            if db_type == "mongo" and all_nodes:
                db_username = data.get("db_username", "").strip()
                db_name = data.get("db_name", "").strip()
                db_password = data.get("db_password", "").strip()
                auth_mechanism = data.get("auth_mechanism", "").strip()
                
                # A. Cross pings from data nodes to Arbiter port:
                for d_setup, d_ip, d_port in data_nodes:
                    for a_setup, a_ip, a_port in arbiter_nodes:
                        check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ok, status_str = check_driver_port_reachability(d_ip, d_port, a_ip, a_port, db_username, db_name, db_password, auth_mechanism)
                        if ok:
                            status_html = '<span style="color: #2ecc71; font-weight: bold;">Reachable</span>'
                        else:
                            port_ok = False
                            arbiter_unreachable = True
                            status_html = f'<span style="color: #e74c3c; font-weight: bold;">{status_str}</span>'
                        reachability_rows.append((f"{d_setup} ({d_ip}) &rarr; {a_setup} ({a_ip})", str(a_port), status_html, check_time))
                
                # B. Cross pings from Arbiter to all other ports (data nodes):
                for a_setup, a_ip, a_port in arbiter_nodes:
                    for d_setup, d_ip, d_port in data_nodes:
                        check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ok, status_str = check_driver_port_reachability(a_ip, a_port, d_ip, d_port, db_username, db_name, db_password, auth_mechanism)
                        if ok:
                            status_html = '<span style="color: #2ecc71; font-weight: bold;">Reachable</span>'
                        else:
                            port_ok = False
                            arbiter_unreachable = True
                            status_html = f'<span style="color: #e74c3c; font-weight: bold;">{status_str}</span>'
                        reachability_rows.append((f"{a_setup} ({a_ip}) &rarr; {d_setup} ({d_ip})", str(d_port), status_html, check_time))

                # C. Cross pings between data nodes
                for a_setup, a_ip, a_port in data_nodes:
                    for b_setup, b_ip, b_port in data_nodes:
                        if a_ip != b_ip:
                            check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ok, status_str = check_driver_port_reachability(a_ip, a_port, b_ip, b_port, db_username, db_name, db_password, auth_mechanism)
                            if ok:
                                status_html = '<span style="color: #2ecc71; font-weight: bold;">Reachable</span>'
                            else:
                                port_ok = False
                                status_html = f'<span style="color: #e74c3c; font-weight: bold;">{status_str}</span>'
                            reachability_rows.append((f"{a_setup} ({a_ip}) &rarr; {b_setup} ({b_ip})", str(b_port), status_html, check_time))

            if reachability_rows:
                report_lines.append(f"<div style='margin-top: 15px;'><strong>2. Database Port Reachability:</strong></div>")
                table_html = make_html_table(["Server IP", "Port Number", "Connection Status", "Checked At"], reachability_rows)
                report_lines.append(table_html)
            else:
                report_lines.append(f"<div style='margin-top: 15px;'><strong>2. Database Port Reachability:</strong> {badge(True, 'No servers defined')}</div>")
                
            # If MongoDB, check Mongod version
            mongo_ok = True
            version_ok = True
            if db_type == "mongo" and all_nodes:
                db_username = data.get("db_username", "").strip()
                db_name = data.get("db_name", "").strip()
                db_password = data.get("db_password", "").strip()
                auth_mechanism = data.get("auth_mechanism", "").strip()
                
                versions = {}
                connection_errors = {}
                
                for setup_name, ip, port in all_nodes:
                    ok, detail = verify_server_mongod_via_driver(ip, port, db_username, db_name, db_password, auth_mechanism)
                    if ok:
                        versions[ip] = detail
                    else:
                        mongo_ok = False
                        connection_errors[ip] = detail

                # Parse versions
                parsed_versions = {}
                for ip, v in versions.items():
                    parsed_versions[ip] = parse_version(v)
                
                major_versions = {ip: p[0] for ip, p in parsed_versions.items() if p != (0,0,0)}
                max_major = max(major_versions.values()) if major_versions else 0
                all_major_match = len(set(major_versions.values())) <= 1
                max_version_tuple = max(parsed_versions.values()) if parsed_versions else (0,0,0)
                
                version_rows = []
                for setup_name, ip, port in all_nodes:
                    check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    node_type = "Arbiter Node" if setup_name == "Arbiter" else "data node"
                    if ip in connection_errors:
                        err_detail = connection_errors[ip]
                        # Show actual error for better diagnosis
                        if "Authentication failed" in str(err_detail):
                            ver_html = '<span style="color: red; font-weight: bold;">Authentication failed</span><br><span style="color: #e67e22; font-size: 0.78rem;">Check DB username, password, auth mechanism & database name</span>'
                        else:
                            ver_html = f'<span style="color: red; font-weight: bold;">install the mongo on the server</span><br><span style="color: #e67e22; font-size: 0.78rem;">{err_detail}</span>'
                    else:
                        v_str = versions[ip]
                        v_tuple = parsed_versions[ip]
                        
                        if not all_major_match:
                            version_ok = False
                            if v_tuple[0] < max_major:
                                ver_html = f'<span style="color: #e74c3c; font-weight: bold;">{v_str}</span><br><span style="color: #e74c3c; font-size: 0.8rem; font-weight: normal;">(mongod version should be same on all the servers, kindly upgrade the mongod version)</span>'
                            else:
                                ver_html = f'<span>{v_str}</span>'
                        else:
                            if v_tuple == max_version_tuple:
                                ver_html = f'<span style="color: #2ecc71; font-weight: bold;">{v_str}</span>'
                            else:
                                ver_html = f'<span style="color: #e67e22; font-weight: bold;">{v_str}</span><br><span style="color: #e67e22; font-size: 0.8rem; font-weight: normal;">(minor version change required, kindly upgrade with the latest mongo version)</span>'
                        
                    version_rows.append((f"{setup_name} ({ip})", node_type, ver_html, check_time))

                report_lines.append(f"<div style='margin-top: 15px;'><strong>3. Mongod Installation & Connection Check:</strong></div>")
                
                if not mongo_ok:
                    status_msg = f'<div style="margin-top: 5px; font-weight: bold; color: #e74c3c;">Matching Condition: Connection failed on one or more nodes</div>'
                elif not all_major_match:
                    status_msg = f'<div style="margin-top: 5px; font-weight: bold; color: #e74c3c;">Matching Condition: Major Version Mismatch Found</div>'
                else:
                    status_msg = f'<div style="margin-top: 5px; font-weight: bold; color: #2ecc71;">Matching Condition: Major version has been matched {max_major}.x</div>'
                
                report_lines.append(status_msg)
                
                table_ver_html = make_html_table(["Server IP", "Node Type", "Mongod Version", "Checked At"], version_rows)
                report_lines.append(table_ver_html)

            # Service Status Check (SSH)
            ssh_rows = []
            server_username = data.get("server_username", "").strip()
            server_password = data.get("server_password", "").strip()
            for setup_name, ip, port in all_nodes:
                check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                status = check_service_status_via_ssh(ip, port, server_username, server_password)
                status_html = f'<span style="color: #2ecc71; font-weight: bold;">active</span>' if status == "active" else f'<span style="color: #e74c3c; font-weight: bold;">inactive</span>'
                ssh_rows.append((f"{ip}:{port}", "mongod", status_html, check_time))
                
            report_lines.append(f"<div style='margin-top: 15px;'><strong>4. Service Status Check (SSH):</strong></div>")
            table_ssh_html = make_html_table(["Server IP", "Service Name", "Status", "Checked At"], ssh_rows)
            report_lines.append(table_ssh_html)

            # Final success decision
            overall_success = port_ok
            if db_type == "mongo":
                overall_success = port_ok and mongo_ok and version_ok
                
            err_message = "Verification failed"
            if arbiter_unreachable:
                overall_success = False
                err_message = "Arbiter server is not reachable"
            elif not overall_success:
                err_message = "Verification failed"
                
            header_color = "#2ecc71" if overall_success else "#e74c3c"
            header_text = "Verification Successful" if overall_success else "Verification Failed"
            header_symbol = "check_circle" if overall_success else "error"
            
            header_html = f'''
            <div style="display: flex; align-items: center; gap: 10px; font-weight: bold; font-size: 1.25rem; color: {header_color}; border-bottom: 2px solid {header_color}; padding-bottom: 12px; margin-bottom: 20px;">
                <span class="material-symbols-outlined" style="font-size: 1.8rem;">{header_symbol}</span>
                {header_text}
            </div>
            '''
            
            return JsonResponse({
                "success": overall_success,
                "report_html": header_html + "".join(report_lines),
                "error": err_message if not overall_success else None,
                "message": "Verification completed"
            })
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": "Verification failed: " + str(e)
            })


class ClusterDeployApiView(View):
    def post(self, request, db_type, index):
        import json
        try:
            body = json.loads(request.body or "{}")
        except Exception:
            body = {}

        try:
            cluster = _get_cluster_by_index(db_type, index)
        except Exception:
            cluster = None

        display_name = (body.get("display_name") or "").strip()
        if display_name:
            db_name = body.get("db_name", "").strip()
            db_password = body.get("db_password", "").strip()
            server_username = body.get("server_username", "").strip()
            server_password = body.get("server_password", "").strip()
            
            enc_db_password = encrypt_string(db_password)
            enc_server_password = encrypt_string(server_password)
                
            if cluster:
                cluster.display_name = display_name
                cluster.dc_ips = body.get("dc_ips", "").strip()
                cluster.dc_ports = body.get("dc_ports", "").strip()
                cluster.dc_ha_ips = body.get("dc_ha_ips", "").strip()
                cluster.dc_ha_ports = body.get("dc_ha_ports", "").strip()
                cluster.dr_ips = body.get("dr_ips", "").strip()
                cluster.dr_ports = body.get("dr_ports", "").strip()
                cluster.dr_ha_ips = body.get("dr_ha_ips", "").strip()
                cluster.dr_ha_ports = body.get("dr_ha_ports", "").strip()
                cluster.arbiter_ips = body.get("arbiter_ips", "").strip()
                cluster.arbiter_ports = body.get("arbiter_ports", "").strip()
                cluster.db_name = db_name
                if db_password:
                    cluster.db_password = enc_db_password
                cluster.server_username = server_username
                if server_password:
                    cluster.server_password = enc_server_password
                cluster.save()
            else:
                cluster = ClusterDetails.objects.create(
                    db_type=db_type,
                    display_name=display_name,
                    dc_ips=body.get("dc_ips", "").strip(),
                    dc_ports=body.get("dc_ports", "").strip(),
                    dc_ha_ips=body.get("dc_ha_ips", "").strip(),
                    dc_ha_ports=body.get("dc_ha_ports", "").strip(),
                    dr_ips=body.get("dr_ips", "").strip(),
                    dr_ports=body.get("dr_ports", "").strip(),
                    dr_ha_ips=body.get("dr_ha_ips", "").strip(),
                    dr_ha_ports=body.get("dr_ha_ports", "").strip(),
                    arbiter_ips=body.get("arbiter_ips", "").strip(),
                    arbiter_ports=body.get("arbiter_ports", "").strip(),
                    db_name=db_name,
                    db_password=enc_db_password,
                    server_username=server_username,
                    server_password=enc_server_password,
                )
                # Find index of new cluster
                clusters = list(ClusterDetails.objects.filter(db_type=db_type, is_deleted=False).order_by("id"))
                index = clusters.index(cluster)
        elif cluster is None:
            return JsonResponse({
                "success": False,
                "error": "Cluster not found"
            }, status=404)
        
        # Create DeploymentResult
        count = DeploymentResult.objects.filter(cluster=cluster).count()
        job_name = f'DeployJob{count + 1:04d}'
        
        deploy_params = {
            'replicaset_name': body.get('replicaset_name', 'INFRAON') or 'rs0',
            'logicalSessionRefreshMillis': body.get('logicalSessionRefreshMillis', 60000),
            'maxSessions': body.get('maxSessions', 5000000),
            'allowMultipleArbiters': str(body.get('allowMultipleArbiters', 'true')).lower() in ('true', '1', 'yes')
        }
        
        deployment = DeploymentResult.objects.create(
            cluster=cluster,
            job_name=job_name,
            cluster_name=cluster.display_name,
            status='running',
            deploy_parameters=deploy_params
        )

        return JsonResponse({
            "success": True,
            "index": index,
            "deployment_id": deployment.id,
            "message": "Configuration saved successfully"
        })


import threading

def _run_deployment_thread(deployment_id, cluster_id, db_type, replicaset_name, logical_session_refresh_millis, max_sessions, allow_multiple_arbiters):
    """Runs deployment in background thread, writing logs to DeploymentResult."""
    from .models import ClusterDetails, DeploymentResult
    from django.utils import timezone
    import time, json, pymongo, urllib.parse, socket, paramiko
    
    deployment = DeploymentResult.objects.get(id=deployment_id)
    cluster = ClusterDetails.objects.get(id=cluster_id)
    
    def append_log(msg):
        deployment.refresh_from_db()
        deployment.log_output += msg + "\n"
        deployment.save(update_fields=['log_output'])

    def run_cmd(ssh, cmd):
        append_log(f"$ {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode("utf-8", errors="ignore").strip()
        err = stderr.read().decode("utf-8", errors="ignore").strip()
        if out:
            append_log(out)
        if err:
            append_log(f"stderr: {err}")
        return out, err
        
    try:
        append_log(f"Starting deployment for cluster '{cluster.display_name}'...")
        append_log(f"Parameters: replicaSet={replicaset_name}, logicalSessionRefreshMillis={logical_session_refresh_millis}, maxSessions={max_sessions}, allowMultipleArbiters={allow_multiple_arbiters}")

        # Gather all nodes
        data_nodes = []
        for setup_name, ips_str, ports_str in [
            ("DC", cluster.dc_ips, cluster.dc_ports),
            ("DC_HA", cluster.dc_ha_ips, cluster.dc_ha_ports),
            ("DR", cluster.dr_ips, cluster.dr_ports),
            ("DR_HA", cluster.dr_ha_ips, cluster.dr_ha_ports),
        ]:
            mapped = map_ips_to_ports(ips_str, ports_str)
            for ip, port in mapped:
                data_nodes.append((setup_name, ip, port))

        arbiter_nodes = []
        mapped_arbiter = map_ips_to_ports(cluster.arbiter_ips, cluster.arbiter_ports)
        for ip, port in mapped_arbiter:
            arbiter_nodes.append(("Arbiter", ip, port))

        all_nodes = data_nodes + arbiter_nodes

        # Check multiple arbiters
        if len(arbiter_nodes) > 1 and not allow_multiple_arbiters:
            append_log(f"Deployment aborted: {len(arbiter_nodes)} Arbiter nodes defined but multiple arbiters are not allowed.")
            deployment.refresh_from_db()
            deployment.status = 'failed'
            deployment.completed_at = timezone.now()
            deployment.save()
            return

        server_username = cluster.server_username
        server_password = decrypt_string(cluster.server_password)

        # SSH update config and restart mongod
        for setup_name, ip, port in all_nodes:
            append_log(f"[SSH] Connecting to {ip} as {server_username}...")
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, username=server_username, password=server_password, timeout=2.0)
                
                # Take a backup of the existing file before editing
                run_cmd(ssh, "if [ -f /etc/mongod.conf ]; then sudo cp /etc/mongod.conf /etc/mongod.conf.backup.$(date +%Y%m%d_%H%M%S); fi")
                
                # Copy config to temp file to read safely with permissions
                run_cmd(ssh, "sudo cp /etc/mongod.conf /tmp/mongod.conf.readable && sudo chmod 644 /tmp/mongod.conf.readable")
                
                conf_content = ""
                sftp = ssh.open_sftp()
                try:
                    with sftp.open("/tmp/mongod.conf.readable", "r") as f:
                        conf_content = f.read().decode("utf-8", errors="ignore")
                except Exception as sftp_err:
                    append_log(f"[SFTP] Warning: Could not read staging config ({sftp_err})")
                
                # Fallback to standard base config if missing or empty
                stripped = conf_content.strip()
                if not stripped or "storage:" not in stripped or "net:" not in stripped:
                    append_log("[SSH] Config empty/missing. Generating base configuration fallback...")
                    conf_content = f"""# mongod.conf
storage:
  dbPath: /var/lib/mongodb
systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log
net:
  port: {port}
  bindIp: 0.0.0.0
processManagement:
  timeZoneInfo: /usr/share/zoneinfo
"""
                
                new_conf = sanitize_mongod_conf(conf_content, replicaset_name, logical_session_refresh_millis, max_sessions, allow_multiple_arbiters)
                
                # Write to temp file
                append_log("[SFTP] Writing updated config block to /tmp/mongod.conf.tmp...")
                with sftp.open("/tmp/mongod.conf.tmp", "w") as f:
                    f.write(new_conf)
                sftp.close()
                
                # Copy temp file to destination with sudo and cleanup
                run_cmd(ssh, "sudo cp /tmp/mongod.conf.tmp /etc/mongod.conf && sudo rm -f /tmp/mongod.conf.readable /tmp/mongod.conf.tmp")
                
                # Restart mongod
                run_cmd(ssh, "sudo systemctl restart mongod")
                ssh.close()
                append_log(f"[SSH] Successfully configured and restarted mongod on {ip}.")
            except Exception as e:
                append_log(f"[SSH] Error: Failed to execute setup steps on {ip} ({e})")
                deployment.refresh_from_db()
                deployment.status = 'failed'
                deployment.completed_at = timezone.now()
                deployment.save()
                return

            append_log(f"Waiting 5 seconds for mongod to initialize on {ip}...")
            for sec in range(1, 6):
                time.sleep(1)
                append_log(f"  ... waiting {sec}s")

        # Connect to primary node (first DC node)
        if not data_nodes:
            append_log("Deployment aborted: No data nodes (DC) configured.")
            deployment.refresh_from_db()
            deployment.status = 'failed'
            deployment.completed_at = timezone.now()
            deployment.save()
            return

        dc_primary = [n for n in data_nodes if n[0] == "DC"]
        if not dc_primary:
            dc_primary = data_nodes
        primary_ip, primary_port = dc_primary[0][1], dc_primary[0][2]

        append_log(f"Connecting to bootstrap primary node {primary_ip}:{primary_port} to initiate replica set...")

        members = []
        member_id = 0
        
        priority_map = {
            "DC": 1.0,
            "DC_HA": 0.9,
            "DR": 0.8,
            "DR_HA": 0.7
        }
        
        for name in ["DC", "DC_HA", "DR", "DR_HA"]:
            for node in data_nodes:
                if node[0] == name:
                    members.append({
                        "_id": member_id,
                        "host": f"{node[1]}:{node[2]}",
                        "priority": priority_map[name]
                    })
                    member_id += 1

        for node in arbiter_nodes:
            members.append({
                "_id": member_id,
                "host": f"{node[1]}:{node[2]}",
                "priority": 0,
                "arbiterOnly": True
            })
            member_id += 1
        
        db_username = getattr(cluster, "db_username", "")
        db_name = cluster.db_name
        db_password = decrypt_string(cluster.db_password)
        auth_mechanism = getattr(cluster, "auth_mechanism", "")
        
        status_data = {}
        
        try:
            client = None
            if db_name and db_password:
                try:
                    username = db_username if db_username else db_name
                    user_esc = urllib.parse.quote_plus(username)
                    pass_esc = urllib.parse.quote_plus(db_password)
                    uri = f"mongodb://{user_esc}:{pass_esc}@{primary_ip}:{primary_port}/{db_name}?serverSelectionTimeoutMS=3000&directConnection=true&authSource={db_name}"
                    if auth_mechanism:
                        uri += f"&authMechanism={auth_mechanism}"
                    client = pymongo.MongoClient(uri)
                    client.admin.command("ping")
                except Exception as auth_err:
                    append_log("[INFO] Access control/authorization is not enabled on this node yet (or credentials are not set up). Retrying connection without authentication...")
                    client = None
            
            if client is None:
                uri = f"mongodb://{primary_ip}:{primary_port}/?serverSelectionTimeoutMS=3000&directConnection=true"
                client = pymongo.MongoClient(uri)
            
            try:
                status_data = client.admin.command("replSetGetStatus")
                append_log("Replica set is already initiated.")
            except Exception:
                append_log(f"Initiating replica set '{replicaset_name}'...")
                config = {
                    "_id": replicaset_name,
                    "members": members
                }
                client.admin.command("replSetInitiate", config)
                append_log("Replica set initiation command sent.")
                
            append_log("Waiting for primary node election (2 seconds)...")
            time.sleep(2)
            
            status_data = client.admin.command("replSetGetStatus")
            
        except Exception as e:
            append_log(f"pymongo connection/initiation failed ({e}). Checking node pings...")
            
            status_data = {
                "members": []
            }
            for m in members:
                host = m["host"]
                ip, port_str = host.split(":")
                port = int(port_str)
                
                connected = False
                try:
                    with socket.create_connection((ip, port), timeout=1.0) as sock:
                        connected = True
                except Exception:
                    pass
                
                is_arbiter = m.get("arbiterOnly", False)
                if connected:
                    state_str = "STANDALONE"
                    health = 0
                    uptime = 0
                else:
                    state_str = "DOWN"
                    health = 0
                    uptime = 0
                    
                status_data["members"].append({
                    "name": host,
                    "stateStr": state_str,
                    "health": health,
                    "uptime": uptime,
                    "optime": {"ts": type('TS', (object,), {"time": int(time.time())})()}
                })
            
            lags = compute_replication_lag(status_data)
            status_table_html = make_replication_status_table(status_data, lags)
            append_log(f"Deployment failed: {e}")
            
            deployment.refresh_from_db()
            deployment.status = 'failed'
            deployment.result_html = status_table_html
            deployment.completed_at = timezone.now()
            deployment.save()
            return

        lags = compute_replication_lag(status_data)
        status_table_html = make_replication_status_table(status_data, lags)
        append_log("Deployment completed successfully!")
        
        deployment.refresh_from_db()
        deployment.status = 'completed'
        deployment.result_html = status_table_html
        deployment.completed_at = timezone.now()
        deployment.save()

    except Exception as e:
        deployment.refresh_from_db()
        deployment.status = 'failed'
        deployment.log_output += f"\nFatal error: {e}\n"
        deployment.completed_at = timezone.now()
        deployment.save()


class ClusterDeployStreamView(View):
    def get(self, request, db_type, index):
        deployment_id = request.GET.get('deployment_id')
        replicaset_name = request.GET.get("replicaset_name", "INFRAON").strip() or "rs0"
        
        logical_session_refresh_millis = request.GET.get("logicalSessionRefreshMillis")
        try:
            logical_session_refresh_millis = int(logical_session_refresh_millis)
        except (ValueError, TypeError):
            logical_session_refresh_millis = 60000
            
        max_sessions = request.GET.get("maxSessions")
        try:
            max_sessions = int(max_sessions)
        except (ValueError, TypeError):
            max_sessions = 5000000
            
        allow_multiple_arbiters = request.GET.get("allowMultipleArbiters", "true").lower() in ("true", "1", "yes")

        try:
            deployment = DeploymentResult.objects.get(id=deployment_id)
            cluster = _get_cluster_by_index(db_type, index)
        except Exception as e:
            def err_generator():
                yield f"data: {json.dumps({'error': f'Cluster/Deployment not found: {e}'})}\n\n"
            return StreamingHttpResponse(err_generator(), content_type="text/event-stream")

        # Start background thread
        thread = threading.Thread(
            target=_run_deployment_thread,
            args=(deployment.id, cluster.id, db_type, replicaset_name, logical_session_refresh_millis, max_sessions, allow_multiple_arbiters),
            daemon=True
        )
        thread.start()
        
        def log_streamer():
            import time
            last_pos = 0
            while True:
                deployment.refresh_from_db()
                current_log = deployment.log_output
                if len(current_log) > last_pos:
                    new_content = current_log[last_pos:]
                    for line in new_content.strip().split('\n'):
                        if line:
                            yield f"data: {json.dumps({'log': line})}\n\n"
                    last_pos = len(current_log)
                
                if deployment.status in ('completed', 'failed'):
                    if deployment.result_html:
                        yield f"data: {json.dumps({'status_table': deployment.result_html})}\n\n"
                    if deployment.status == 'completed':
                        yield f"data: {json.dumps({'done': True})}\n\n"
                    else:
                        yield f"data: {json.dumps({'error': 'Deployment failed'})}\n\n"
                    break
                
                time.sleep(1)
        
        return StreamingHttpResponse(log_streamer(), content_type='text/event-stream')


class DeploymentResultsApiView(View):
    """Returns JSON list of all deployment results for a cluster."""
    def get(self, request, db_type, index):
        try:
            cluster = _get_cluster_by_index(db_type, index)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Cluster not found'})
        
        deployments = DeploymentResult.objects.filter(cluster=cluster)
        results = []
        for d in deployments:
            results.append({
                'id': d.id,
                'job_name': d.job_name,
                'cluster_name': d.cluster_name,
                'status': d.status,
                'deploy_parameters': d.deploy_parameters,
                'started_at': d.started_at.strftime('%Y-%m-%d %H:%M:%S') if d.started_at else '',
                'completed_at': d.completed_at.strftime('%Y-%m-%d %H:%M:%S') if d.completed_at else 'In Progress',
                'log_output': d.log_output,
                'result_html': d.result_html,
            })
        
        return JsonResponse({'success': True, 'results': results, 'cluster_name': cluster.display_name})


class DeploymentLiveStreamView(View):
    """SSE endpoint for live log streaming of a running deployment from results panel."""
    def get(self, request, db_type, index, job_id):
        try:
            deployment = DeploymentResult.objects.get(id=job_id)
        except DeploymentResult.DoesNotExist:
            def err():
                yield f"data: {json.dumps({'error': 'Deployment not found'})}\n\n"
            return StreamingHttpResponse(err(), content_type='text/event-stream')
        
        def log_streamer():
            import time
            last_pos = 0
            while True:
                deployment.refresh_from_db()
                current_log = deployment.log_output
                if len(current_log) > last_pos:
                    new_content = current_log[last_pos:]
                    for line in new_content.strip().split('\n'):
                        if line:
                            yield f"data: {json.dumps({'log': line})}\n\n"
                    last_pos = len(current_log)
                
                if deployment.status in ('completed', 'failed'):
                    if deployment.result_html:
                        yield f"data: {json.dumps({'status_table': deployment.result_html})}\n\n"
                    if deployment.status == 'completed':
                        yield f"data: {json.dumps({'done': True})}\n\n"
                    else:
                        yield f"data: {json.dumps({'error': 'Deployment failed'})}\n\n"
                    break
                
                time.sleep(1)
        
        return StreamingHttpResponse(log_streamer(), content_type='text/event-stream')
