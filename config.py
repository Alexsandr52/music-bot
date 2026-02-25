"""Конфигурация бота."""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()


# Telegram Bot API Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Прокси для yt_dlp (если нужен)
# Форматы:
# - HTTP: "http://user:password@host:port"
# - SOCKS5: "socks5://user:password@host:port"
# Примеры:
PROXY = os.getenv("PROXY", "")

# Или используйте встроенный прокси Telegram (для HTTP запросов бота)
# Требует библиотеку: pip install httpx[socks]
# TELEGRAM_PROXY = "socks5://127.0.0.1:1080"
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY", None)

# Количество результатов поиска
SEARCH_LIMIT = 5

# Максимальное количество хранимых треков
MAX_TRACKS = 50

# Папка для сохранения треков
TRACKS_DIR = "tracks"


def validate_config():
    """Проверяет конфигурацию."""
    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден! Создайте файл .env с строкой:\n"
            "BOT_TOKEN=your_token_here"
        )
    return True
