import os
import logging
import yt_dlp

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Папка для сохранения треков
TRACKS_DIR = "tracks"


def ensure_tracks_dir():
    """Создает папку для треков, если она не существует."""
    if not os.path.exists(TRACKS_DIR):
        os.makedirs(TRACKS_DIR)
        logger.info(f"Создана папка для треков: {TRACKS_DIR}")


def download_audio_yt(search_query, proxy=None):
    """Скачивает аудио с YouTube по поисковому запросу.

    Args:
        search_query: Поисковый запрос (например "Artist - Song")
        proxy: Прокси в формате "http://user:pass@host:port" или "socks5://host:port"

    Returns:
        Путь к скачанному файлу или None при ошибке
    """
    ensure_tracks_dir()

    ydl_opts = {
        'format': 'bestaudio/best',
        'writethumbnail': False,
        'extractaudio': True,
        'audioformat': 'mp3',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': os.path.join(TRACKS_DIR, '%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',  # 128kbps - баланс качества и размера
        }],
    }

    # Добавляем прокси если указан
    if proxy:
        ydl_opts['proxy'] = proxy
        logger.info(f"Используется прокси: {proxy}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Поиск и скачивание: {search_query}")
            info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)

            if not info or 'entries' not in info:
                logger.error(f"Не найдено результатов для: {search_query}")
                return None

            # Берем первый результат
            video = info['entries'][0]
            if not video:
                return None

            filename = os.path.join(TRACKS_DIR, f"{video['id']}.mp3")

            if os.path.exists(filename):
                logger.info(f"Успешно скачано: {filename}")
                return filename
            else:
                logger.error(f"Файл не найден после скачивания: {filename}")
                return None

    except Exception as e:
        logger.error(f"Ошибка при скачивании: {type(e).__name__} - {e}")
        return None


def cleanup_old_files(max_files=50):
    """Удаляет старые файлы, если их количество превышает лимит.

    Args:
        max_files: Максимальное количество файлов для хранения
    """
    if not os.path.exists(TRACKS_DIR):
        return

    files = [
        os.path.join(TRACKS_DIR, f)
        for f in os.listdir(TRACKS_DIR)
        if f.endswith('.mp3')
    ]

    if len(files) > max_files:
        # Сортируем по времени изменения
        files.sort(key=os.path.getmtime)

        # Удаляем самые старые
        for file in files[:len(files) - max_files]:
            try:
                os.remove(file)
                logger.info(f"Удален старый файл: {file}")
            except Exception as e:
                logger.error(f"Ошибка при удалении {file}: {e}")
