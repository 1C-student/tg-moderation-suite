from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from contextlib import suppress
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message, Update
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
import uvicorn

from .config import settings
from .moderation import RateLimiter, mute_user, unmute_user
from .storage import delete_mute, get_limit, init_db, set_limit, set_mute
from .vk_bridge import send_to_vk_group

bot = Bot(token=settings.telegram_token)
dp = Dispatcher()
rate_limiter = RateLimiter()
chat_messages: dict[int, deque[dict]] = defaultdict(lambda: deque(maxlen=300))
chat_users: dict[int, dict[int, dict]] = defaultdict(dict)


class MuteRequest(BaseModel):
    chat_id: int
    user_id: int
    minutes: int = Field(default=10, ge=1, le=1440)


class UnmuteRequest(BaseModel):
    chat_id: int
    user_id: int


class LimitRequest(BaseModel):
    chat_id: int
    messages_per_minute: int = Field(ge=1, le=120)


class ResolveChatRequest(BaseModel):
    group_link: str


class DeleteMessageRequest(BaseModel):
    chat_id: int
    message_id: int


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != settings.manager_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _extract_chat_ref(group_link: str) -> str:
    value = group_link.strip()
    if value.startswith("@"):
        return value
    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        path = parsed.path.strip("/")
        if not path:
            raise HTTPException(status_code=400, detail="Invalid group link")
        if path.startswith("+"):
            raise HTTPException(
                status_code=400,
                detail="Invite links cannot be resolved directly. Add bot to group first and use @username or chat_id.",
            )
        return f"@{path.split('/')[0]}"
    return value


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Бот модерации активен.\n"
        "Команды администратора: /mute user_id minutes, /unmute user_id, /limit count"
    )


@dp.message(Command("limit"))
async def cmd_limit(message: Message) -> None:
    if not message.text:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Формат: /limit <сообщений_в_минуту>")
        return
    try:
        value = int(parts[1])
    except ValueError:
        await message.answer("Лимит должен быть числом.")
        return
    set_limit(message.chat.id, value)
    await message.answer(f"Лимит сообщений установлен: {value}/мин")


@dp.message(Command("mute"))
async def cmd_mute(message: Message) -> None:
    if not message.text:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Формат: /mute <user_id> <минут>")
        return
    try:
        user_id = int(parts[1])
        minutes = int(parts[2])
    except ValueError:
        await message.answer("user_id и минут должно быть числом.")
        return

    until_ts = await mute_user(bot, message.chat.id, user_id, minutes)
    set_mute(message.chat.id, user_id, until_ts)
    await message.answer(f"Пользователь {user_id} замьючен на {minutes} минут.")


@dp.message(Command("unmute"))
async def cmd_unmute(message: Message) -> None:
    if not message.text:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Формат: /unmute <user_id>")
        return
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return

    await unmute_user(bot, message.chat.id, user_id)
    delete_mute(message.chat.id, user_id)
    await message.answer(f"Пользователь {user_id} размьючен.")


@dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def anti_spam_handler(message: Message) -> None:
    if message.from_user is None:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id
    chat_users[chat_id][user_id] = {
        "user_id": user_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name or "",
    }
    chat_messages[chat_id].append(
        {
            "message_id": message.message_id,
            "user_id": user_id,
            "username": message.from_user.username or "",
            "full_name": message.from_user.full_name or "",
            "text": message.text or message.caption or "",
        }
    )
    limit = get_limit(chat_id) or settings.default_message_limit_per_minute
    if rate_limiter.is_spam(chat_id, user_id, limit):
        await mute_user(bot, chat_id, user_id, 5)
        await message.answer(f"@{message.from_user.username or user_id} временно замьючен за флуд.")
        await send_to_vk_group(
            f"[TG] Пользователь {user_id} замьючен в чате {chat_id} за превышение лимита сообщений."
        )


async def _apply_webhook() -> None:
    if not settings.public_base_url:
        return
    webhook_url = f"{settings.public_base_url.rstrip('/')}{settings.telegram_webhook_path}"
    await bot.set_webhook(url=webhook_url, secret_token=settings.telegram_webhook_secret or None)


init_db()
app = FastAPI(title="Telegram Moderation Bot API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(settings.telegram_webhook_path)
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(default="")) -> dict[str, str]:
    expected = settings.telegram_webhook_secret
    if expected and x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")
    payload = await request.json()
    update = Update.model_validate(payload)
    await dp.feed_update(bot, update)
    return {"ok": "true"}


@app.post("/admin/setup_webhook", dependencies=[Depends(verify_api_key)])
async def admin_setup_webhook() -> dict[str, str]:
    await _apply_webhook()
    return {"status": "webhook_set"}


@app.post("/admin/mute", dependencies=[Depends(verify_api_key)])
async def admin_mute(payload: MuteRequest) -> dict[str, str]:
    until_ts = await mute_user(bot, payload.chat_id, payload.user_id, payload.minutes)
    set_mute(payload.chat_id, payload.user_id, until_ts)
    return {"status": "muted"}


@app.post("/admin/unmute", dependencies=[Depends(verify_api_key)])
async def admin_unmute(payload: UnmuteRequest) -> dict[str, str]:
    await unmute_user(bot, payload.chat_id, payload.user_id)
    delete_mute(payload.chat_id, payload.user_id)
    return {"status": "unmuted"}


@app.post("/admin/limit", dependencies=[Depends(verify_api_key)])
async def admin_limit(payload: LimitRequest) -> dict[str, str]:
    set_limit(payload.chat_id, payload.messages_per_minute)
    return {"status": "limit_updated"}


@app.post("/admin/resolve_chat", dependencies=[Depends(verify_api_key)])
async def admin_resolve_chat(payload: ResolveChatRequest) -> dict:
    chat_ref = _extract_chat_ref(payload.group_link)
    try:
        chat = await bot.get_chat(chat_ref)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Cannot resolve chat: {exc}") from exc
    return {"chat_id": chat.id, "title": chat.title or chat.username or str(chat.id)}


@app.get("/admin/chats/{chat_id}/messages", dependencies=[Depends(verify_api_key)])
async def admin_messages(chat_id: int) -> dict:
    return {"items": list(chat_messages.get(chat_id, []))}


@app.get("/admin/chats/{chat_id}/users", dependencies=[Depends(verify_api_key)])
async def admin_users(chat_id: int) -> dict:
    users = list(chat_users.get(chat_id, {}).values())
    users.sort(key=lambda item: item.get("full_name", ""))
    return {"items": users}


@app.post("/admin/delete_message", dependencies=[Depends(verify_api_key)])
async def admin_delete_message(payload: DeleteMessageRequest) -> dict[str, str]:
    await bot.delete_message(chat_id=payload.chat_id, message_id=payload.message_id)
    return {"status": "deleted"}


@app.post("/vk/callback")
async def vk_callback(payload: dict) -> str:
    if payload.get("type") == "confirmation":
        return settings.vk_confirmation_code
    if settings.vk_secret and payload.get("secret") != settings.vk_secret:
        raise HTTPException(status_code=403, detail="Invalid VK secret")
    if payload.get("type") == "message_new":
        obj = payload.get("object", {})
        message = obj.get("message", {})
        text = message.get("text", "").strip()
        if text and settings.vk_target_tg_chat_id:
            await bot.send_message(chat_id=settings.vk_target_tg_chat_id, text=f"[VK] {text}")
    return "ok"


if __name__ == "__main__":
    if settings.bot_mode.lower() == "polling":
        async def _run_polling() -> None:
            try:
                await dp.start_polling(bot)
            finally:
                await bot.session.close()

        asyncio.run(_run_polling())
        raise SystemExit(0)

    uvicorn.run("app.main:app", host=settings.server_host, port=settings.server_port, reload=False)
