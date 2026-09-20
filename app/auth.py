import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MAX_AGE_SEC = 24 * 3600


def validate_init_data(init_data: str, bot_token: str) -> dict:
    """Проверяет подпись initData от Telegram и возвращает dict пользователя."""
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("no hash")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received_hash):
        raise ValueError("bad signature")

    if time.time() - int(parsed.get("auth_date", 0)) > MAX_AGE_SEC:
        raise ValueError("initData expired")

    return json.loads(parsed["user"])


def get_tg_user(authorization: str = Header(default="")) -> dict:
    """Зависимость FastAPI. Заголовок: Authorization: tma <initData>"""
    scheme, _, init_data = authorization.partition(" ")
    if scheme != "tma" or not init_data:
        raise HTTPException(401, "Missing initData")
    try:
        return validate_init_data(init_data, BOT_TOKEN)
    except (ValueError, KeyError):
        raise HTTPException(401, "Invalid initData")
