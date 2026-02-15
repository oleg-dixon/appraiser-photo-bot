FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями
COPY pyproject.toml README.md ./
COPY appraiser_photo_bot/ appraiser_photo_bot/
COPY cli.py .

# Устанавливаем пакет в режиме разработки
RUN pip install --no-cache-dir -e .

# Создаем пользователя
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Запускаем бота через cli.py
ENTRYPOINT ["python", "cli.py"]