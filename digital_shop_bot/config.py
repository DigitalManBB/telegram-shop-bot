import json
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Загружаем переменные окружения из файла .env
load_dotenv(dotenv_path=ENV_PATH)

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")


def parse_admin_ids(raw: str) -> list[int]:
    """Преобразует ADMIN_IDS в список int."""
    value = raw.strip()
    if not value:
        return []

    
    if value.startswith("[") and value.endswith("]"):
        parsed = json.loads(value)
        return [int(x) for x in parsed]

    
    parts = [p.strip() for p in value.replace(",", " ").split() if p.strip()]
    return [int(p) for p in parts]


ADMIN_IDS = parse_admin_ids(ADMIN_IDS_RAW)


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором."""
    return user_id in ADMIN_IDS

