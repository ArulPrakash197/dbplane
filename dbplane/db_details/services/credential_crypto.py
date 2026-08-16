import json
import os
import stat
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


KEY_ENV_NAME = "DBPLANE_CREDENTIAL_KEY"
KEY_FILE_ENV_NAME = "DBPLANE_CREDENTIAL_KEY_FILE"
DEFAULT_KEY_FILE_NAME = ".dbplane_credential.key"


def _load_fernet_classes():
    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ImportError as exc:
        raise ImproperlyConfigured(
            "The 'cryptography' package is required for encrypted credential storage. "
            "Install it with: pip install cryptography"
        ) from exc
    return Fernet, InvalidToken


def _get_key_file_path():
    configured_path = os.environ.get(KEY_FILE_ENV_NAME)
    if configured_path:
        return Path(configured_path)
    return Path(settings.BASE_DIR) / DEFAULT_KEY_FILE_NAME


def _read_or_create_key():
    env_key = os.environ.get(KEY_ENV_NAME)
    if env_key:
        return env_key.encode("utf-8")

    Fernet, _ = _load_fernet_classes()
    key_file = _get_key_file_path()

    if key_file.exists():
        return key_file.read_bytes().strip()

    key = Fernet.generate_key()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(key)

    try:
        os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    return key


def _get_fernet():
    Fernet, _ = _load_fernet_classes()
    try:
        return Fernet(_read_or_create_key())
    except Exception as exc:
        raise ImproperlyConfigured(
            "Invalid DB Plane credential key. Use a Fernet key in "
            f"{KEY_ENV_NAME} or {KEY_FILE_ENV_NAME}."
        ) from exc


def encrypt_dict(data):
    if not data:
        return ""

    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _get_fernet().encrypt(payload).decode("utf-8")


def decrypt_dict(token):
    if not token:
        return {}

    _, InvalidToken = _load_fernet_classes()
    try:
        payload = _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
        return json.loads(payload)
    except InvalidToken as exc:
        raise ImproperlyConfigured(
            "Saved credentials could not be decrypted. The configured DB Plane "
            "credential key may be missing or different from the original key."
        ) from exc
