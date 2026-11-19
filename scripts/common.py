"""Shared helpers for the reddit-aws-bot scripts."""
import json
import os
import pathlib

import requests
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
CONFIG_PATH = ROOT / "config.yaml"

PENDING_DRAFT_PATH = STATE_DIR / "pending_draft.json"
TELEGRAM_OFFSET_PATH = STATE_DIR / "telegram_offset.json"
HISTORY_PATH = STATE_DIR / "history.json"

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_json(path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_pending_draft():
    return _load_json(PENDING_DRAFT_PATH, None)


def save_pending_draft(draft):
    _save_json(PENDING_DRAFT_PATH, draft)


def clear_pending_draft():
    if PENDING_DRAFT_PATH.exists():
        PENDING_DRAFT_PATH.unlink()


def load_history():
    return _load_json(HISTORY_PATH, {"posted": [], "rejected": []})


def save_history(history):
    _save_json(HISTORY_PATH, history)


def load_telegram_offset():
    data = _load_json(TELEGRAM_OFFSET_PATH, {"offset": 0})
    return data.get("offset", 0)


def save_telegram_offset(offset):
    _save_json(TELEGRAM_OFFSET_PATH, {"offset": offset})


class TelegramError(RuntimeError):
    pass


def _telegram_call(method, payload=None, params=None):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = TELEGRAM_API.format(token=token, method=method)
    resp = requests.post(url, json=payload, params=params, timeout=30)
    data = resp.json()
    if not data.get("ok"):
        raise TelegramError(f"Telegram API error on {method}: {data}")
    return data["result"]


def telegram_send_draft(draft):
    """Send a draft for approval with Approve/Reject inline buttons."""
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    text = (
        f"*New Reddit draft for r/{draft['subreddit']}*\n\n"
        f"*Title:* {draft['title']}\n\n"
        f"{draft['body']}"
    )
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve:{draft['draft_id']}"},
            {"text": "❌ Reject", "callback_data": f"reject:{draft['draft_id']}"},
        ]]
    }
    return _telegram_call(
        "sendMessage",
        payload={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
        },
    )


def telegram_send_text(text):
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    return _telegram_call("sendMessage", payload={"chat_id": chat_id, "text": text})


def telegram_get_updates(offset):
    return _telegram_call(
        "getUpdates",
        params={"offset": offset, "timeout": 0},
    )


def telegram_answer_callback(callback_query_id, text):
    return _telegram_call(
        "answerCallbackQuery",
        payload={"callback_query_id": callback_query_id, "text": text},
    )
