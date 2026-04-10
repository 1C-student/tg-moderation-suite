from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

import requests

from api_client import ApiClient


class ManagerApp(tk.Tk):
    SETTINGS_PATH = Path(__file__).resolve().parent / "manager_settings.json"

    def __init__(self) -> None:
        super().__init__()
        self.title("Панель модерации")
        self.geometry("980x680")
        self.minsize(920, 620)
        self.client: ApiClient | None = None
        self.current_chat_id: int | None = None
        self.current_chat_title: str = ""
        self.message_rows: dict[str, dict[str, Any]] = {}
        self.user_rows: dict[str, dict[str, Any]] = {}
        self.selected_message_user_id: int | None = None
        self._build_ui()
        self._load_settings()
        self.after(200, self._auto_connect_if_enabled)

    def _build_ui(self) -> None:
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("Card.TFrame", background="#1f2430")
        self.style.configure("CardTitle.TLabel", background="#1f2430", foreground="#f2f2f2", font=("Segoe UI", 10, "bold"))
        self.style.configure("Info.TLabel", background="#1f2430", foreground="#d8d8d8")

        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        top = ttk.Frame(root, style="Card.TFrame", padding=12)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=1)

        ttk.Label(top, text="Подключение к серверу", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", padx=6, pady=(0, 8))
        ttk.Label(top, text="API URL", style="Info.TLabel").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.api_url = ttk.Entry(top)
        self.api_url.insert(0, "http://127.0.0.1:8080")
        self.api_url.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(top, text="API-ключ", style="Info.TLabel").grid(row=1, column=2, sticky="w", padx=6, pady=4)
        self.api_key = ttk.Entry(top, show="*")
        self.api_key.grid(row=1, column=3, sticky="ew", padx=6, pady=4)
        ttk.Button(top, text="Подключиться", command=self.connect).grid(row=1, column=4, sticky="e", padx=6, pady=4)

        group = ttk.Frame(root, style="Card.TFrame", padding=12)
        group.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        group.columnconfigure(1, weight=1)
        ttk.Label(group, text="Подключение к группе", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", padx=6, pady=(0, 8))
        ttk.Label(group, text="Ссылка на группу / @username / chat_id", style="Info.TLabel").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.group_link = ttk.Entry(group)
        self.group_link.insert(0, "https://t.me/your_group")
        self.group_link.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ttk.Button(group, text="Найти и подключить", command=self.resolve_group).grid(row=1, column=2, padx=6, pady=4)

        self.chat_info = tk.StringVar(value="Группа не подключена")
        ttk.Label(group, textvariable=self.chat_info, style="Info.TLabel").grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=(8, 2))
        self.auto_connect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            group,
            text="Автоподключение при запуске",
            variable=self.auto_connect_var,
            command=self._save_settings,
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=6, pady=(4, 0))

        body = ttk.Notebook(root)
        body.grid(row=2, column=0, sticky="nsew")

        messages_tab = ttk.Frame(body, padding=8)
        users_tab = ttk.Frame(body, padding=8)
        settings_tab = ttk.Frame(body, padding=8)
        body.add(messages_tab, text="Сообщения")
        body.add(users_tab, text="Активные пользователи")
        body.add(settings_tab, text="Модерация")

        messages_tab.columnconfigure(0, weight=1)
        messages_tab.rowconfigure(0, weight=1)
        self.messages_table = ttk.Treeview(
            messages_tab,
            columns=("message_id", "user_id", "username", "full_name", "text"),
            show="headings",
        )
        for col, title, width in (
            ("message_id", "ID", 70),
            ("user_id", "ID пользователя", 130),
            ("username", "Юзернейм", 150),
            ("full_name", "Имя", 180),
            ("text", "Сообщение", 420),
        ):
            self.messages_table.heading(col, text=title)
            self.messages_table.column(col, width=width, anchor="w")
        self.messages_table.grid(row=0, column=0, sticky="nsew")
        self.messages_table.bind("<<TreeviewSelect>>", self._on_message_select)
        msg_btns = ttk.Frame(messages_tab)
        msg_btns.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(msg_btns, text="Обновить ленту", command=self.refresh_messages).pack(side="left", padx=4)
        ttk.Button(msg_btns, text="Удалить выбранное", command=self.delete_selected_message).pack(side="left", padx=4)
        ttk.Button(msg_btns, text="Замутить автора", command=self.mute_selected_message_author).pack(side="left", padx=4)

        users_tab.columnconfigure(0, weight=1)
        users_tab.rowconfigure(0, weight=1)
        self.users_table = ttk.Treeview(
            users_tab,
            columns=("user_id", "username", "full_name"),
            show="headings",
        )
        for col, title, width in (
            ("user_id", "ID пользователя", 150),
            ("username", "Юзернейм", 200),
            ("full_name", "Имя", 360),
        ):
            self.users_table.heading(col, text=title)
            self.users_table.column(col, width=width, anchor="w")
        self.users_table.grid(row=0, column=0, sticky="nsew")
        user_btns = ttk.Frame(users_tab)
        user_btns.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(user_btns, text="Обновить список", command=self.refresh_users).pack(side="left", padx=4)
        ttk.Button(user_btns, text="Замутить выбранного", command=self.mute_selected_user).pack(side="left", padx=4)
        ttk.Button(user_btns, text="Размутить выбранного", command=self.unmute_selected_user).pack(side="left", padx=4)

        settings_tab.columnconfigure(1, weight=1)
        ttk.Label(settings_tab, text="Мут (минут)").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.minutes = ttk.Entry(settings_tab, width=16)
        self.minutes.insert(0, "10")
        self.minutes.grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(settings_tab, text="Лимит (сообщ./мин)").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.limit = ttk.Entry(settings_tab, width=16)
        self.limit.insert(0, "8")
        self.limit.grid(row=1, column=1, sticky="w", padx=6, pady=6)
        ttk.Button(settings_tab, text="Применить лимит", command=self.do_limit).grid(row=2, column=1, sticky="w", padx=6, pady=6)

    def connect(self) -> None:
        self.client = ApiClient(self.api_url.get().strip(), self.api_key.get().strip())
        self._save_settings()
        messagebox.showinfo("Подключено", "Подключение к API настроено.")

    def _require_client(self) -> ApiClient:
        if not self.client:
            raise RuntimeError("Сначала нажмите 'Подключиться'.")
        return self.client

    def _require_chat(self) -> int:
        if self.current_chat_id is None:
            raise RuntimeError("Сначала подключите группу.")
        return self.current_chat_id

    def resolve_group(self) -> None:
        try:
            client = self._require_client()
            response = client.resolve_chat(self.group_link.get().strip())
            payload = self._payload(response)
            if not response.ok:
                raise RuntimeError(str(payload))
            self.current_chat_id = int(payload["chat_id"])
            self.current_chat_title = str(payload.get("title", self.current_chat_id))
            self.chat_info.set(f"Подключено: {self.current_chat_title} (chat_id={self.current_chat_id})")
            self._save_settings()
            self.refresh_messages()
            self.refresh_users()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка подключения", str(exc))

    def refresh_messages(self) -> None:
        try:
            client = self._require_client()
            chat_id = self._require_chat()
            response = client.list_messages(chat_id)
            payload = self._payload(response)
            if not response.ok:
                raise RuntimeError(str(payload))
            self.messages_table.delete(*self.messages_table.get_children())
            self.message_rows.clear()
            for row in payload.get("items", []):
                item_id = f"msg-{row.get('message_id')}"
                self.message_rows[item_id] = row
                self.messages_table.insert(
                    "",
                    "end",
                    iid=item_id,
                    values=(
                        row.get("message_id", ""),
                        row.get("user_id", ""),
                        row.get("username", ""),
                        row.get("full_name", ""),
                        row.get("text", "")[:120].replace("\n", " "),
                    ),
                )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))

    def refresh_users(self) -> None:
        try:
            client = self._require_client()
            chat_id = self._require_chat()
            response = client.list_users(chat_id)
            payload = self._payload(response)
            if not response.ok:
                raise RuntimeError(str(payload))
            self.users_table.delete(*self.users_table.get_children())
            self.user_rows.clear()
            for row in payload.get("items", []):
                item_id = f"user-{row.get('user_id')}"
                self.user_rows[item_id] = row
                self.users_table.insert(
                    "",
                    "end",
                    iid=item_id,
                    values=(row.get("user_id", ""), row.get("username", ""), row.get("full_name", "")),
                )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))

    def _on_message_select(self, _: object) -> None:
        selected = self.messages_table.selection()
        if not selected:
            self.selected_message_user_id = None
            return
        row = self.message_rows.get(selected[0], {})
        try:
            self.selected_message_user_id = int(row.get("user_id"))
        except Exception:
            self.selected_message_user_id = None

    def do_mute(self) -> None:
        try:
            client = self._require_client()
            chat_id = self._require_chat()
            user_id = self._selected_user_id()
            minutes = int(self.minutes.get())
            response = client.mute(chat_id, user_id, minutes)
            self._show_response(response)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))

    def do_unmute(self) -> None:
        try:
            client = self._require_client()
            chat_id = self._require_chat()
            user_id = self._selected_user_id()
            response = client.unmute(chat_id, user_id)
            self._show_response(response)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))

    def do_limit(self) -> None:
        try:
            client = self._require_client()
            chat_id = self._require_chat()
            limit = int(self.limit.get())
            response = client.set_limit(chat_id, limit)
            self._show_response(response)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))

    def delete_selected_message(self) -> None:
        try:
            client = self._require_client()
            chat_id = self._require_chat()
            selected = self.messages_table.selection()
            if not selected:
                raise RuntimeError("Сначала выберите сообщение.")
            row = self.message_rows[selected[0]]
            response = client.delete_message(chat_id, int(row["message_id"]))
            self._show_response(response)
            self.refresh_messages()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))

    def mute_selected_message_author(self) -> None:
        self.selected_message_user_id = self._selected_message_author_id()
        self.do_mute()
        self.refresh_users()

    def mute_selected_user(self) -> None:
        self.do_mute()
        self.refresh_users()

    def unmute_selected_user(self) -> None:
        self.do_unmute()

    @staticmethod
    def _payload(response: requests.Response) -> dict:
        try:
            return response.json()
        except Exception:
            return {"raw": response.text}

    def _selected_message_author_id(self) -> int:
        selected = self.messages_table.selection()
        if not selected:
            raise RuntimeError("Сначала выберите сообщение.")
        row = self.message_rows[selected[0]]
        return int(row["user_id"])

    def _selected_user_id(self) -> int:
        if self.selected_message_user_id:
            return int(self.selected_message_user_id)
        selected_user = self.users_table.selection()
        if selected_user:
            row = self.user_rows[selected_user[0]]
            return int(row["user_id"])
        raise RuntimeError("Выберите пользователя во вкладке 'Активные пользователи' или сообщение во вкладке 'Сообщения'.")

    @staticmethod
    def _show_response(response: requests.Response) -> None:
        payload = ManagerApp._payload(response)
        if response.ok:
            messagebox.showinfo("Готово", str(payload))
        else:
            messagebox.showerror("Ошибка API", f"{response.status_code}: {payload}")

    def _load_settings(self) -> None:
        if not self.SETTINGS_PATH.exists():
            return
        try:
            data = json.loads(self.SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        self.api_url.delete(0, tk.END)
        self.api_url.insert(0, data.get("api_url", "http://127.0.0.1:8080"))
        self.api_key.delete(0, tk.END)
        self.api_key.insert(0, data.get("api_key", ""))
        self.group_link.delete(0, tk.END)
        self.group_link.insert(0, data.get("group_link", ""))
        self.auto_connect_var.set(bool(data.get("auto_connect", True)))

    def _save_settings(self) -> None:
        payload = {
            "api_url": self.api_url.get().strip(),
            "api_key": self.api_key.get().strip(),
            "group_link": self.group_link.get().strip(),
            "auto_connect": bool(self.auto_connect_var.get()),
        }
        self.SETTINGS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _auto_connect_if_enabled(self) -> None:
        if not self.auto_connect_var.get():
            return
        if not self.api_url.get().strip() or not self.api_key.get().strip():
            return
        try:
            self.client = ApiClient(self.api_url.get().strip(), self.api_key.get().strip())
        except Exception:
            return
        group = self.group_link.get().strip()
        if group:
            try:
                self.resolve_group()
            except Exception:
                pass


if __name__ == "__main__":
    app = ManagerApp()
    app.mainloop()
