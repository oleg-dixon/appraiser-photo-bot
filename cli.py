#!/usr/bin/env python3
import os
import sys
import logging
from dotenv import load_dotenv
from .bot import PhotoTableBot
from .config import BotConfig

def setup_logging():
    """Настраивает логирование"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log')
        ]
    )

def main():
    """Основная функция запуска бота"""
    # Загружаем переменные окружения
    load_dotenv()
    
    # Настраиваем логирование
    setup_logging()
    
    # Проверяем наличие токена
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("Ошибка: BOT_TOKEN не найден в переменных окружения.")
        print("Создайте файл .env с содержимым:")
        print("BOT_TOKEN=your_bot_token_here")
        sys.exit(1)
    
    try:
        # Создаем конфигурацию
        config = BotConfig.from_env()
        
        # Создаем и запускаем бота
        bot = PhotoTableBot(config)
        bot.run()
        
    except KeyboardInterrupt:
        print("\nБот остановлен.")
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()