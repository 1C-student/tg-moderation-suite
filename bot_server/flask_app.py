from __future__ import annotations

import asyncio

from aiogram.types import Update
from flask import Flask, jsonify, request

from app.main import (
    _extract_chat_ref,
    admin_delete_message,
    admin_limit,
    admin_messages,
    admin_mute,
    admin_resolve_chat,
    admin_setup_webhook,
    admin_unmute,
    admin_users,
    vk_callback,
)
from app.main import DeleteMessageRequest, LimitRequest, MuteRequest, ResolveChatRequest, UnmuteRequest
from app.main import settings

flask_app = Flask(__name__)


def run(coro):
    return asyncio.run(coro)


def check_api_key() -> tuple[bool, tuple]:
    if request.headers.get("x-api-key", "") != settings.manager_api_key:
        return False, (jsonify({"detail": "Invalid API key"}), 401)
    return True, ()


@flask_app.get("/health")
def health():
    return jsonify({"status": "ok"})


@flask_app.post("/telegram/webhook")
def telegram_webhook():
    expected = settings.telegram_webhook_secret
    if expected:
        actual = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if actual != expected:
            return jsonify({"detail": "Invalid Telegram webhook secret"}), 403
    payload = request.get_json(silent=True) or {}
    update = Update.model_validate(payload)
    from app.main import bot, dp

    run(dp.feed_update(bot, update))
    return jsonify({"ok": True})


@flask_app.post("/admin/setup_webhook")
def setup_webhook():
    ok, err = check_api_key()
    if not ok:
        return err
    return jsonify(run(admin_setup_webhook()))


@flask_app.post("/admin/mute")
def mute():
    ok, err = check_api_key()
    if not ok:
        return err
    payload = MuteRequest.model_validate(request.get_json(silent=True) or {})
    return jsonify(run(admin_mute(payload)))


@flask_app.post("/admin/unmute")
def unmute():
    ok, err = check_api_key()
    if not ok:
        return err
    payload = UnmuteRequest.model_validate(request.get_json(silent=True) or {})
    return jsonify(run(admin_unmute(payload)))


@flask_app.post("/admin/limit")
def limit():
    ok, err = check_api_key()
    if not ok:
        return err
    payload = LimitRequest.model_validate(request.get_json(silent=True) or {})
    return jsonify(run(admin_limit(payload)))


@flask_app.post("/admin/resolve_chat")
def resolve_chat():
    ok, err = check_api_key()
    if not ok:
        return err
    payload = ResolveChatRequest.model_validate(request.get_json(silent=True) or {})
    return jsonify(run(admin_resolve_chat(payload)))


@flask_app.get("/admin/chats/<int:chat_id>/messages")
def messages(chat_id: int):
    ok, err = check_api_key()
    if not ok:
        return err
    return jsonify(run(admin_messages(chat_id)))


@flask_app.get("/admin/chats/<int:chat_id>/users")
def users(chat_id: int):
    ok, err = check_api_key()
    if not ok:
        return err
    return jsonify(run(admin_users(chat_id)))


@flask_app.post("/admin/delete_message")
def delete_message():
    ok, err = check_api_key()
    if not ok:
        return err
    payload = DeleteMessageRequest.model_validate(request.get_json(silent=True) or {})
    return jsonify(run(admin_delete_message(payload)))


@flask_app.post("/vk/callback")
def vk_cb():
    payload = request.get_json(silent=True) or {}
    result = run(vk_callback(payload))
    return result, 200, {"Content-Type": "text/plain; charset=utf-8"}


application = flask_app
