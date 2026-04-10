from __future__ import annotations

import httpx

from .config import settings


async def send_to_vk_group(message_text: str) -> None:
    if not settings.vk_group_token:
        return

    payload = {
        "group_id": "",  # optional: can be omitted when token is bound to group
        "message": message_text[:4000],
        "access_token": settings.vk_group_token,
        "v": "5.199",
        "random_id": 0,
        "peer_id": 2000000001,  # replace with real conversation id if needed
    }
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post("https://api.vk.com/method/messages.send", data=payload)
