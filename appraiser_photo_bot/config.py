import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class BotConfig:
    """Конфигурация бота."""

    token: str
    log_level: str = "INFO"
    cleanup_interval: int = 600
    session_timeout: int = 1800
    max_photos: int = 100
    max_rows: int = 10
    max_cols: int = 10
    image_quality: int = 85
    image_max_size: int = 2000
    debug: bool = False
    admin_id: Optional[int] = None
    enable_buttons: bool = True
    button_timeout: int = 3600

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Создает конфигурацию из переменных окружения."""
        return cls(
            token=os.getenv("BOT_TOKEN", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            cleanup_interval=int(os.getenv("CLEANUP_INTERVAL", "600")),
            session_timeout=int(os.getenv("SESSION_TIMEOUT", "1800")),
            max_photos=int(os.getenv("MAX_PHOTOS", "100")),
            max_rows=int(os.getenv("MAX_ROWS", "10")),
            max_cols=int(os.getenv("MAX_COLS", "10")),
            image_quality=int(os.getenv("IMAGE_QUALITY", "85")),
            image_max_size=int(os.getenv("IMAGE_MAX_SIZE", "2000")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            admin_id=int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None,
            enable_buttons=os.getenv("ENABLE_BUTTONS", "true").lower() == "true",
            button_timeout=int(os.getenv("BUTTON_TIMEOUT", "3600")),
        )
