from __future__ import annotations
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"

SECRET_KEY = os.environ.get("SOFTHUB_SECRET_KEY", "soft-hub-local-admin")
ADMIN_USERNAME = os.environ.get("SOFTHUB_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("SOFTHUB_ADMIN_PASSWORD", "123456")

ENABLE_DATA_BACKUPS = os.environ.get("SOFTHUB_ENABLE_DATA_BACKUPS", "1") != "0"
BACKUP_KEEP_PER_FILE = int(os.environ.get("SOFTHUB_BACKUP_KEEP_PER_FILE", "20"))


def check_security() -> list[str]:
    warnings: list[str] = []
    if SECRET_KEY == "soft-hub-local-admin":
        warnings.append("SOFTHUB_SECRET_KEY 使用了默认值，请在生产环境中设置随机密钥。")
    if "SOFTHUB_ADMIN_USERNAME" not in os.environ:
        warnings.append("SOFTHUB_ADMIN_USERNAME 使用了默认值 (admin)。")
    if "SOFTHUB_ADMIN_PASSWORD" not in os.environ:
        warnings.append("SOFTHUB_ADMIN_PASSWORD 使用了默认值 (123456)，请立即修改。")
    return warnings
