from __future__ import annotations

import time
from collections import defaultdict, deque

from aiogram import Bot
from aiogram.types import ChatPermissions


class RateLimiter:
    def __init__(self) -> None:
        self._bucket: dict[tuple[int, int], deque[float]] = defaultdict(deque)

    def is_spam(self, chat_id: int, user_id: int, max_per_minute: int) -> bool:
        now = time.time()
        key = (chat_id, user_id)
        q = self._bucket[key]
        while q and now - q[0] > 60:
            q.popleft()
        q.append(now)
        return len(q) > max_per_minute


async def mute_user(bot: Bot, chat_id: int, user_id: int, minutes: int) -> int:
    until_ts = int(time.time()) + minutes * 60
    permissions = ChatPermissions(can_send_messages=False)
    await bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user_id,
        permissions=permissions,
        until_date=until_ts,
    )
    return until_ts


async def unmute_user(bot: Bot, chat_id: int, user_id: int) -> None:
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False,
    )
    await bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=permissions)
