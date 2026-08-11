import json
import os

from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError, ProgrammingError

from db_details.logger import get_logger
from db_details.models import CredentialRecord

from .credential_store import (
    add_credential,
    delete_credential,
    get_credential,
    list_credentials,
    update_credential,
)


logger = get_logger("connection_store", "connections.log")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONN_FILE = os.path.join(BASE_DIR, "connections.json")
DATABASES_COMPONENT = "databases"
DEFAULT_CONNECTIONS = {
    "postgresql": [],
    "mongo": [],
    "redis": [],
    "rabbitmq": [],
}
SECRET_FIELDS_BY_DB_TYPE = {
    "postgresql": {"password"},
    "mongo": {"uri"},
    "redis": {"password"},
    "rabbitmq": {"password"},
}

_json_migration_checked = False


def _secret_fields_for(db_type):
    return SECRET_FIELDS_BY_DB_TYPE.get(db_type, {"password", "uri"})


def _migrate_json_connections_if_needed():
    global _json_migration_checked

    if _json_migration_checked:
        return

    _json_migration_checked = True

    if not os.path.exists(CONN_FILE):
        return

    try:
        has_database_credentials = CredentialRecord.objects.filter(
            component=DATABASES_COMPONENT
        ).exists()
    except (OperationalError, ProgrammingError) as exc:
        raise ImproperlyConfigured("Credential table is missing. Run: python manage.py migrate") from exc

    if has_database_credentials:
        return

    try:
        with open(CONN_FILE, "r") as file_obj:
            legacy_data = json.load(file_obj)
    except Exception as exc:
        logger.error("Failed to read legacy connections.json", exc_info=True)
        raise ImproperlyConfigured("Could not import existing connections.json") from exc

    migrated_count = 0
    for db_type, connections in legacy_data.items():
        if db_type not in DEFAULT_CONNECTIONS:
            continue

        for connection in connections:
            try:
                add_credential(
                    DATABASES_COMPONENT,
                    db_type,
                    connection,
                    secret_fields=_secret_fields_for(db_type),
                )
                migrated_count += 1
            except ValueError:
                logger.warning(
                    "Skipped duplicate legacy connection | db=%s | name=%s",
                    db_type,
                    connection.get("display_name"),
                )

    if migrated_count:
        logger.info("Migrated %s connections from connections.json", migrated_count)


def load_connections(include_secrets=False):
    logger.info("Loading connections")
    _migrate_json_connections_if_needed()

    data = {key: [] for key in DEFAULT_CONNECTIONS}
    for db_type in data:
        data[db_type] = list_credentials(
            DATABASES_COMPONENT,
            db_type,
            include_secrets=include_secrets,
        )

    logger.info("Connections loaded successfully")
    return data


def save_connections(data):
    raise NotImplementedError("Connections are now saved with add_connection/update_connection")


def add_connection(db_type, conn):
    logger.info("Adding connection | db=%s", db_type)
    _migrate_json_connections_if_needed()
    record = add_credential(
        DATABASES_COMPONENT,
        db_type,
        conn,
        secret_fields=_secret_fields_for(db_type),
    )
    logger.info("Connection added successfully | db=%s | name=%s", db_type, record.display_name)
    return record


def delete_connection(db_type, index):
    logger.info("Deleting connection | db=%s | index=%s", db_type, index)
    _migrate_json_connections_if_needed()
    deleted = delete_credential(DATABASES_COMPONENT, db_type, index)
    logger.info("Connection deleted | db=%s | name=%s", db_type, deleted.display_name)


def update_connection(db_type, index, new_conn):
    logger.info("Updating connection | db=%s | index=%s", db_type, index)
    _migrate_json_connections_if_needed()
    record = update_credential(
        DATABASES_COMPONENT,
        db_type,
        index,
        new_conn,
        secret_fields=_secret_fields_for(db_type),
        preserve_blank_secrets=True,
    )
    logger.info("Connection updated successfully | db=%s | name=%s", db_type, record.display_name)
    return record


def get_connection(db_type, index):
    logger.info("Fetching connection | db=%s | index=%s", db_type, index)
    _migrate_json_connections_if_needed()
    connection = get_credential(
        DATABASES_COMPONENT,
        db_type,
        index,
        include_secrets=True,
    )
    logger.info("Connection fetched | db=%s | name=%s", db_type, connection.get("display_name"))
    return connection
