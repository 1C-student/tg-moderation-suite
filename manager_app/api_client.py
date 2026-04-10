from __future__ import annotations

import requests


class ApiClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"x-api-key": api_key}

    def mute(self, chat_id: int, user_id: int, minutes: int) -> requests.Response:
        return requests.post(
            f"{self.base_url}/admin/mute",
            json={"chat_id": chat_id, "user_id": user_id, "minutes": minutes},
            headers=self.headers,
            timeout=15,
        )

    def unmute(self, chat_id: int, user_id: int) -> requests.Response:
        return requests.post(
            f"{self.base_url}/admin/unmute",
            json={"chat_id": chat_id, "user_id": user_id},
            headers=self.headers,
            timeout=15,
        )

    def set_limit(self, chat_id: int, messages_per_minute: int) -> requests.Response:
        return requests.post(
            f"{self.base_url}/admin/limit",
            json={"chat_id": chat_id, "messages_per_minute": messages_per_minute},
            headers=self.headers,
            timeout=15,
        )

    def resolve_chat(self, group_link: str) -> requests.Response:
        return requests.post(
            f"{self.base_url}/admin/resolve_chat",
            json={"group_link": group_link},
            headers=self.headers,
            timeout=20,
        )

    def list_messages(self, chat_id: int) -> requests.Response:
        return requests.get(
            f"{self.base_url}/admin/chats/{chat_id}/messages",
            headers=self.headers,
            timeout=20,
        )

    def list_users(self, chat_id: int) -> requests.Response:
        return requests.get(
            f"{self.base_url}/admin/chats/{chat_id}/users",
            headers=self.headers,
            timeout=20,
        )

    def delete_message(self, chat_id: int, message_id: int) -> requests.Response:
        return requests.post(
            f"{self.base_url}/admin/delete_message",
            json={"chat_id": chat_id, "message_id": message_id},
            headers=self.headers,
            timeout=15,
        )
