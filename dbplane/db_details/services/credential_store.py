from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError, ProgrammingError
from django.utils import timezone

from db_details.models import CredentialRecord

from .credential_crypto import decrypt_dict, encrypt_dict


DEFAULT_SECRET_FIELDS = {
    "password",
    "uri",
    "token",
    "secret",
    "api_key",
    "private_key",
    "client_secret",
}


def normalize_key(value):
    return str(value or "").strip().lower().replace(" ", "_")


def _clean_payload(payload):
    return {
        key: value
        for key, value in payload.items()
        if value is not None and key not in {"id", "component", "credential_type"}
    }


def _split_payload(payload, secret_fields=None):
    secret_field_names = set(secret_fields or DEFAULT_SECRET_FIELDS)
    cleaned_payload = _clean_payload(payload)
    display_name = str(cleaned_payload.pop("display_name", "")).strip()

    public_data = {}
    secret_data = {}

    for key, value in cleaned_payload.items():
        if key in secret_field_names:
            if value not in ("", None):
                secret_data[key] = value
        else:
            public_data[key] = value

    return display_name, public_data, secret_data


def _serialize_record(record, include_secrets=False):
    payload = {
        "id": record.id,
        "component": record.component,
        "credential_type": record.credential_type,
        "display_name": record.display_name,
        **(record.public_data or {}),
    }

    if include_secrets:
        payload.update(decrypt_dict(record.encrypted_secret_data))

    return payload


def _query(component, credential_type=None, include_deleted=False):
    filters = {"component": normalize_key(component)}
    if credential_type:
        filters["credential_type"] = normalize_key(credential_type)
    if not include_deleted:
        filters["is_deleted"] = False
    return CredentialRecord.objects.filter(**filters).order_by("id")


def _get_record_by_index(component, credential_type, index):
    try:
        index = int(index)
        return _query(component, credential_type)[index]
    except (IndexError, ValueError):
        raise ValueError("Invalid index")
    except (OperationalError, ProgrammingError) as exc:
        raise ImproperlyConfigured("Credential table is missing. Run: python manage.py migrate") from exc


def list_credentials(component, credential_type=None, include_secrets=False, include_deleted=False):
    try:
        return [
            _serialize_record(record, include_secrets=include_secrets)
            for record in _query(component, credential_type, include_deleted=include_deleted)
        ]
    except (OperationalError, ProgrammingError) as exc:
        raise ImproperlyConfigured("Credential table is missing. Run: python manage.py migrate") from exc


def add_credential(component, credential_type, payload, secret_fields=None):
    component = normalize_key(component)
    credential_type = normalize_key(credential_type)
    display_name, public_data, secret_data = _split_payload(payload, secret_fields)

    if not display_name:
        raise ValueError("Display name is required")

    if CredentialRecord.objects.filter(
        component=component,
        credential_type=credential_type,
        display_name__iexact=display_name,
        is_deleted=False,
    ).exists():
        raise ValueError("Display name already exists")

    return CredentialRecord.objects.create(
        component=component,
        credential_type=credential_type,
        display_name=display_name,
        public_data=public_data,
        encrypted_secret_data=encrypt_dict(secret_data),
    )


def update_credential(
    component,
    credential_type,
    index,
    payload,
    secret_fields=None,
    preserve_blank_secrets=True,
):
    record = _get_record_by_index(component, credential_type, index)
    display_name, public_data, secret_data = _split_payload(payload, secret_fields)

    if not display_name:
        raise ValueError("Display name is required")

    duplicate_exists = CredentialRecord.objects.filter(
        component=record.component,
        credential_type=record.credential_type,
        display_name__iexact=display_name,
        is_deleted=False,
    ).exclude(pk=record.pk).exists()
    if duplicate_exists:
        raise ValueError("Display name already exists")

    if preserve_blank_secrets:
        merged_secret_data = decrypt_dict(record.encrypted_secret_data)
        merged_secret_data.update(secret_data)
    else:
        merged_secret_data = secret_data

    record.display_name = display_name
    record.public_data = public_data
    record.encrypted_secret_data = encrypt_dict(merged_secret_data)
    record.save(update_fields=["display_name", "public_data", "encrypted_secret_data", "updated_at"])
    return record


def delete_credential(component, credential_type, index):
    record = _get_record_by_index(component, credential_type, index)
    record.is_deleted = True
    record.deleted_at = timezone.now()
    record.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    return record


def get_credential(component, credential_type, index, include_secrets=True):
    record = _get_record_by_index(component, credential_type, index)
    return _serialize_record(record, include_secrets=include_secrets)
