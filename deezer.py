import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')


def search_deezer(query, limit=5):
    """Поиск треков в Deezer API.

    Args:
        query: Строка поиска (исполнитель - название)
        limit: Количество результатов (по умолчанию 5)

    Returns:
        Список словарей с информацией о треках или None при ошибке
    """
    url = "https://api.deezer.com/search"

    query = query.strip()
    if not query:
        return []

    try:
        resp = requests.get(url, params={'q': query, 'limit': limit}, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get('data'):
            top = []
            for track in data['data']:
                artist = track.get('artist', {}) or {}
                album = track.get('album', {}) or {}

                top.append({
                    'title': str(track.get('title', '')).strip(),
                    'artist': str(artist.get('name', 'Unknown')).strip(),
                    'cover': str(album.get('cover_big', '')).strip(),
                    'duration': track.get('duration', 0),
                    'query': f"{artist.get('name', '')} - {track.get('title', '')}".strip()
                })
            return top
        return []

    except requests.exceptions.Timeout:
        logging.error("Таймаут запроса к Deezer")
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса: {e}")
    except ValueError as e:
        logging.error(f"Ошибка парсинга ответа: {e}")
    except Exception as e:
        logging.error(f"Неизвестная ошибка: {type(e).__name__} - {e}")

    return None


def format_track_message(track, index):
    """Форматирует информацию о треке для отправки в Telegram.

    Args:
        track: Словарь с информацией о треке
        index: Номер трека в списке

    Returns:
        Отформатированная строка
    """
    duration_min = track.get('duration', 0) // 60
    duration_sec = track.get('duration', 0) % 60

    return (
        f"🎵 *{index}. {track['artist']} — {track['title']}*\n"
        f"⏱ {duration_min}:{duration_sec:02d}\n"
    )


def get_track_unique_key(track):
    """Генерирует уникальный ключ для трека на основе артиста и названия."""
    return f"{track['artist'].lower()}_{track['title'].lower()}".replace(' ', '_')
