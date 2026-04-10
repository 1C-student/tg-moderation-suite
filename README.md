# Telegram Moderation Suite

Состав:
- `bot_server` - сервер Telegram-бота (mute/unmute, антифлуд, API для управления, VK Callback endpoint).
- `manager_app` - отдельная программа управления (GUI), собирается в `.exe`.

## 1) Важно про токен

Ты отправил токен бота в открытом сообщении. Его нужно **срочно перевыпустить** через BotFather (`/revoke` и новый `/token`) и использовать уже новый токен.

## 2) Запуск бота на отдельном сервере

На VPS/сервере (Ubuntu/Windows Server):

1. Скопируй папку `bot_server`.
2. Установи Python 3.11+.
3. Команды:

```bash
cd bot_server
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

4. В `.env` заполни:
- `TELEGRAM_TOKEN`
- `MANAGER_API_KEY`
- `VK_CONFIRMATION_CODE`, `VK_SECRET`, `VK_GROUP_TOKEN` (если нужен мост с VK)
- `VK_TARGET_TG_CHAT_ID` (ID чата Telegram, куда пересылать сообщения из VK)

5. Запуск:

```bash
.venv/bin/python -m app.main
```

Сервер поднимет:
- Telegram polling для модерации
- HTTP API на `SERVER_HOST:SERVER_PORT`
- VK callback endpoint: `POST /vk/callback`

## 2.1) Полный автозапуск 24/7 на VPS (рекомендуется)

Я добавил деплой через Docker (`restart: unless-stopped`), чтобы бот работал постоянно и автоматически поднимался после перезагрузки сервера.

### Что нужно от тебя (один раз):
1. Купить/иметь VPS (Ubuntu 22.04+).
2. Привязать домен к IP сервера (A-запись), например `bot.yourdomain.com`.
3. Загрузить проект на сервер.

### Команды на сервере:
```bash
cd tg-moderation-suite
cp bot_server/.env.example bot_server/.env
nano bot_server/.env
```

Заполни минимум:
- `TELEGRAM_TOKEN`
- `MANAGER_API_KEY`

Далее:
```bash
chmod +x scripts/deploy_vps.sh scripts/renew_ssl.sh
./scripts/deploy_vps.sh bot.yourdomain.com your@email.com
```

После деплоя:
- `API URL` для программы: `https://bot.yourdomain.com`
- `API KEY` для программы: значение `MANAGER_API_KEY` из `bot_server/.env`

### Автопродление SSL
Добавь в cron на VPS:
```bash
crontab -e
```
Строка:
```cron
0 4 * * * cd /root/tg-moderation-suite && ./scripts/renew_ssl.sh >> /var/log/tg_bot_renew.log 2>&1
```

## 2.2) Бесплатный деплой на PythonAnywhere (webhook-режим)

Если нет VPS, можно развернуть в PythonAnywhere. Для бесплатного тарифа нужен webhook-режим (без polling).

1. Создай аккаунт: [PythonAnywhere](https://www.pythonanywhere.com/)
2. Залей папку `bot_server` в домашнюю директорию (через Files или git).
3. Открой Bash console и выполни:
```bash
cd ~/bot_server
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
4. В `.env` укажи:
- `BOT_MODE=webhook`
- `PUBLIC_BASE_URL=https://<username>.pythonanywhere.com`
- `TELEGRAM_WEBHOOK_SECRET=<случайный_секрет>`
- `TELEGRAM_TOKEN`, `MANAGER_API_KEY`
5. Вкладка **Web** в PythonAnywhere:
- Add a new web app (manual config, Python 3.10)
- Путь WSGI-файла замени содержимым из `bot_server/pythonanywhere_wsgi.py`
- Нажми Reload
6. Поставь webhook (один раз):
```bash
curl -X POST "https://<username>.pythonanywhere.com/admin/setup_webhook" \
  -H "x-api-key: <MANAGER_API_KEY>"
```
7. Проверка:
```bash
curl "https://<username>.pythonanywhere.com/health"
```

## 3) Интеграция в Telegram группу

1. Добавь бота в группу.
2. Выдай права администратора:
- ограничение участников
- удаление/модерация сообщений (по необходимости)
3. Команды в чате:
- `/mute <user_id> <minutes>`
- `/unmute <user_id>`
- `/limit <messages_per_minute>`

## 4) Интеграция с группой ВКонтакте

В настройках сообщества VK:
1. Включи Callback API.
2. Укажи URL: `https://YOUR_DOMAIN/vk/callback`
3. Подставь `VK_CONFIRMATION_CODE` и `VK_SECRET` в `.env`.
4. Дай права токену сообщества на сообщения.

## 5) Отдельная программа для управления

Папка: `manager_app`.

Локальный запуск:
```bash
cd manager_app
python -m pip install -r requirements.txt
python manager_gui.py
```

Сборка `.exe`:
```bat
cd manager_app
build_exe.bat
```

Готовый файл будет:
- `manager_app\\dist\\TGModerationManager.exe`

## API для программы управления

Авторизация через заголовок `x-api-key`.

Endpoints:
- `POST /admin/mute` `{ chat_id, user_id, minutes }`
- `POST /admin/unmute` `{ chat_id, user_id }`
- `POST /admin/limit` `{ chat_id, messages_per_minute }`
- `POST /admin/resolve_chat` `{ group_link }`
- `GET /admin/chats/{chat_id}/messages`
- `GET /admin/chats/{chat_id}/users`
- `POST /admin/delete_message` `{ chat_id, message_id }`
- `POST /admin/setup_webhook`

## Ограничения Telegram API

- Бот не может получить полный список всех участников группы напрямую.
- В приложении показывается список активных пользователей (тех, чьи сообщения уже видел бот).
- Лента сообщений также формируется из входящих сообщений после добавления бота в группу.

