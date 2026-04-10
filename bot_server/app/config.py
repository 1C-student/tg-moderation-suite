from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_token: str
    manager_api_key: str = "change_me"
    server_host: str = "0.0.0.0"
    server_port: int = 8080
    bot_mode: str = "webhook"  # webhook | polling
    default_message_limit_per_minute: int = 8
    telegram_webhook_path: str = "/telegram/webhook"
    telegram_webhook_secret: str = ""
    public_base_url: str = ""
    vk_group_token: str = ""
    vk_confirmation_code: str = ""
    vk_secret: str = ""
    vk_target_tg_chat_id: int = 0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
