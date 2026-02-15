#!/usr/bin/env python3
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from appraiser_photo_bot.bot import PhotoTableBot
from appraiser_photo_bot.config import BotConfig


def setup_logging() -> None:
    """Настраивает логирование."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("bot.log"),
        ],
    )


def main() -> None:
    """Основная функция запуска бота."""
    load_dotenv()

    setup_logging()

    token: Optional[str] = os.getenv("BOT_TOKEN")
    if not token:
        print("Ошибка: BOT_TOKEN не найден в переменных окружения.")
        print("Создайте файл .env с содержимым:")
        print("BOT_TOKEN=your_bot_token_here")
        sys.exit(1)

    try:
        config: BotConfig = BotConfig.from_env()
        bot: PhotoTableBot = PhotoTableBot(config)
        bot.run()

    except KeyboardInterrupt:
        print("\nБот остановлен.")
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
