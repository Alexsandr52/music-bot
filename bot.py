import telebot
import telebot.types as types
from telebot import formatting
import os
import time

from config import BOT_TOKEN, PROXY, SEARCH_LIMIT, TRACKS_DIR, validate_config
from logger import setup_logger
from deezer import search_deezer, format_track_message
from downloader import download_audio_yt, cleanup_old_files

# Настройка логирования
logger = setup_logger("music_bot", level="INFO")

# Проверяем конфигурацию
validate_config()

# Создаем папку для треков
if not os.path.exists(TRACKS_DIR):
    os.makedirs(TRACKS_DIR)

# Инициализируем бота с прокси
if PROXY:
    from telebot import apihelper
    apihelper.proxy = {'http': PROXY, 'https': PROXY}
    logger.info(f"Используется прокси: {PROXY}")

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище для последних результатов поиска пользователей
user_search_results = {}


def create_tracks_keyboard(tracks, user_id):
    """Создает inline клавиатуру с найденными треками."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, track in enumerate(tracks, 1):
        button_text = f"{i}. {track['artist']} - {track['title']}"
        callback_data = f"track_{user_id}_{i-1}"
        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))

    markup.add(types.InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{user_id}"))

    return markup


@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Обработчик команды /start."""
    text = (
        "🎵 *Музыкальный бот*\n\n"
        "Доступные команды:\n"
        "/search <запрос> - поиск музыки\n"
        "/help - справка\n\n"
        "Пример: `/search Ice Nine Kills - Funerary`"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['help'])
def cmd_help(message):
    """Обработчик команды /help."""
    text = (
        "📖 *Справка*\n\n"
        "1. Отправьте `/search <исполнитель - трек>`\n"
        "2. Выберите трек из списка\n"
        "3. Дождитесь загрузки\n\n"
        "*Примеры запросов:*\n"
        "• `/search Imagine Dragons - Believer`\n"
        "• `/search Кино - Группа крови`\n"
        "• `/search Eminem`"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['search'])
def cmd_search(message):
    """Обработчик команды /search."""
    # Проверяем, есть ли текст после команды
    args = message.text.split(' ', 1)
    if len(args) < 2 or not args[1].strip():
        bot.send_message(
            message.chat.id,
            "❌ Укажите запрос для поиска!\nПример: `/search Artist - Song`",
            parse_mode='Markdown'
        )
        return

    query = args[1].strip()

    # Отправляем сообщение о поиске
    status_msg = bot.send_message(message.chat.id, "🔎 Поиск...")

    # Ищем треки через Deezer
    results = search_deezer(query, limit=SEARCH_LIMIT)

    if results is None:
        bot.edit_message_text(
            "❌ Произошла ошибка при поиске. Попробуйте позже.",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id
        )
        return

    if not results:
        bot.edit_message_text(
            "📭 Ничего не найдено. Попробуйте изменить запрос.",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id
        )
        return

    # Сохраняем результаты для пользователя
    user_search_results[message.from_user.id] = results

    # Формируем сообщение с результатами
    response_text = f"✅ *Найдено треков: {len(results)}*\n\n"
    for i, track in enumerate(results, 1):
        response_text += format_track_message(track, i)

    response_text += "\n_Выберите трек для скачивания_"

    # Создаем клавиатуру
    keyboard = create_tracks_keyboard(results, message.from_user.id)

    bot.edit_message_text(
        response_text,
        chat_id=status_msg.chat.id,
        message_id=status_msg.message_id,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('track_'))
def callback_track_handler(callback):
    """Обработчик нажатия на кнопку трека."""
    user_id = callback.from_user.id

    logger.info("=" * 60)
    logger.info(f"CALLBACK: пользователь {user_id} выбирает трек")

    # Проверяем, есть ли результаты поиска для этого пользователя
    if user_id not in user_search_results:
        logger.warning(f"Пользователь {user_id} не имеет результатов поиска")
        bot.answer_callback_query(callback.id, "❌ Срок действия поиска истек. Выполните поиск заново.", show_alert=True)
        return

    try:
        # Парсим callback_data
        data = callback.data.split('_')
        track_index = int(data[2])
        logger.info(f"Выбран трек индекс: {track_index}")

        # Получаем выбранный трек
        tracks = user_search_results[user_id]
        if track_index >= len(tracks):
            logger.error(f"Неверный индекс трека: {track_index}, всего треков: {len(tracks)}")
            bot.answer_callback_query(callback.id, "❌ Неверный выбор", show_alert=True)
            return

        track = tracks[track_index]
        logger.info(f"Трек: {track['artist']} - {track['title']}")
        logger.info(f"Query для yt-dlp: {track['query']}")

        # Отправляем сообщение о начале загрузки
        bot.edit_message_text(
            f"⏳ Загрузка: *{track['artist']} - {track['title']}*\n\nЭто может занять время...",
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            parse_mode='Markdown'
        )

        # Скачиваем трек
        logger.info(f"Начало скачивания через yt-dlp с прокси: {PROXY if PROXY else 'без прокси'}")
        filename = download_audio_yt(track['query'], proxy=PROXY)

        logger.info(f"Результат скачивания: {filename}")

        if filename and os.path.exists(filename):
            file_size = os.path.getsize(filename)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"Файл существует: {filename}")
            logger.info(f"Размер файла: {file_size} bytes ({file_size_mb:.2f} MB)")

            # Отправляем аудио файл
            logger.info(f"Начало отправки в Telegram...")
            logger.info(f"Chat ID: {callback.message.chat.id}")

            import time
            start_time = time.time()

            try:
                with open(filename, 'rb') as audio:
                    logger.info(f"Файл открыт для чтения")
                    logger.info(f"Вызов bot.send_audio()...")

                    result = bot.send_audio(
                        callback.message.chat.id,
                        audio,
                        title=track['title'],
                        performer=track['artist'],
                        caption=f"🎵 {track['artist']} - {track['title']}",
                        timeout=300
                    )

                    elapsed = time.time() - start_time
                    logger.info(f"✅ УСПЕХ! Файл отправлен за {elapsed:.2f} секунд")
                    logger.info(f"Message ID: {result.message_id}")

                bot.delete_message(callback.message.chat.id, callback.message.message_id)
                logger.info(f"Сообщение загрузки удалено")
                logger.info(f"✅ Трек отправлен: {track['artist']} - {track['title']}")

                # Очищаем старые файлы
                cleanup_old_files()

            except Exception as send_error:
                elapsed = time.time() - start_time
                logger.error(f"❌ ОШИБКА отправки через {elapsed:.2f} секунд")
                logger.error(f"Тип: {type(send_error).__name__}")
                logger.error(f"Сообщение: {str(send_error)}")
                logger.error(f"Args: {send_error.args}")
                raise

        else:
            logger.error(f"Файл не найден или скачивание не удалось")
            bot.edit_message_text(
                "❌ Не удалось скачать трек.\n\n_Возможно, yt_dlp недоступен в вашем регионе._",
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                parse_mode='Markdown'
            )

        bot.answer_callback_query(callback.id)
        logger.info("=" * 60)

    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        logger.error(f"Traceback:", exc_info=True)
        bot.answer_callback_query(callback.id, "❌ Ошибка при выборе трека", show_alert=True)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {type(e).__name__} - {e}")
        logger.error(f"Traceback:", exc_info=True)
        bot.answer_callback_query(callback.id, "❌ Произошла ошибка", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def callback_cancel_handler(callback):
    """Обработчик кнопки Отмена."""
    user_id = callback.from_user.id

    if user_id in user_search_results:
        del user_search_results[user_id]

    bot.edit_message_text(
        "❌ Поиск отменен",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id
    )
    bot.answer_callback_query(callback.id)


# Inline mode для использования через @botname в любом чате
@bot.inline_handler(lambda query: len(query.query) > 0)
def inline_query(inline_query):
    """Обработчик inline запросов для @botname."""
    query = inline_query.query.strip()
    logger.info(f"INLINE запрос от {inline_query.from_user.id}: {query}")

    try:
        # Ищем треки
        results = search_deezer(query, limit=5)

        if results is None or not results:
            # Если ничего не найдено
            answer = types.InlineQueryResultArticle(
                id='1',
                title='❌ Ничего не найдено',
                description='Попробуйте изменить запрос',
                input_message_content=types.InputTextMessageContent(
                    message_text=f"❌ Ничего не найдено по запросу: {query}"
                )
            )
            bot.answer_inline_query(inline_query.id, [answer])
            return

        # Формируем результаты
        inline_results = []
        for i, track in enumerate(results[:5], 1):  # Максимум 5 результатов
            result = types.InlineQueryResultArticle(
                id=str(i),
                title=f"{i}. {track['artist']} - {track['title']}",
                description=f"⏱ {track.get('duration', 0) // 60}:{track.get('duration', 0) % 60:02d}",
                input_message_content=types.InputTextMessageContent(
                    message_text=f"🎵 *{track['artist']} - {track['title']}*\n\n"
                                 f"Отправьте команду /search в личку бота для скачивания.",
                    parse_mode='Markdown'
                ),
                thumb_url=track.get('cover', ''),
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton(
                        text="🔍 Скачать",
                        url=f"https://t.me/{bot.get_me().username}?start=search_{track['query']}"
                    )
                )
            )
            inline_results.append(result)

        bot.answer_inline_query(inline_query.id, inline_results, cache_time=300)
        logger.info(f"Отправлено {len(inline_results)} результатов inline")

    except Exception as e:
        logger.error(f"Ошибка inline запроса: {type(e).__name__}: {e}")


# Обработчик добавления в группы
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_members(message):
    """Приветствие при добавлении в группу."""
    if message.new_chat_members:
        for member in message.new_chat_members:
            if member.id == bot.get_me().id:
                # Бота добавили в группу
                bot.send_message(
                    message.chat.id,
                    "👋 Привет! Я музыкальный бот.\n\n"
                    "Команды:\n"
                    "/search <запрос> - поиск музыки\n"
                    "/help - справка\n\n"
                    "Также можете использовать меня через @username в любом чате!"
                )
                logger.info(f"Бот добавлен в группу {message.chat.id}")


# Сообщения в группах
@bot.message_handler(commands=['search'], chat_types=['group', 'supergroup'])
def cmd_search_group(message):
    """Поиск музыки в группах."""
    args = message.text.split(' ', 1)
    if len(args) < 2 or not args[1].strip():
        bot.reply_to(message, "❌ Укажите запрос: /search Artist - Song")
        return

    query = args[1].strip()
    bot.send_message(message.chat.id, f"🔎 Поиск: {query}\n\n⏳ Пожалуйста, напишите мне в личку для скачивания.")

    # Отправляем запрос в личку
    try:
        bot.send_message(
            message.from_user.id,
            f"🔍 Вы искали в группе: {query}\n\n"
            f"Используйте /search {query} для скачивания."
        )
    except Exception as e:
        logger.warning(f"Не могу написать пользователю: {e}")
        bot.reply_to(message, "❌ Напишите мне в личку, чтобы я мог отправлять файлы.")


if __name__ == "__main__":
    try:
        logger.info("Бот запускается...")
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {type(e).__name__} - {e}")
