import telebot
import telebot.types as types
from telebot import formatting
import os
import time

from config import BOT_TOKEN, PROXY, SEARCH_LIMIT, TRACKS_DIR, validate_config
from logger import setup_logger
from deezer import search_deezer, format_track_message
from downloader import download_audio_yt, cleanup_old_files

logger = setup_logger("music_bot", level="INFO")
validate_config()

if not os.path.exists(TRACKS_DIR):
    os.makedirs(TRACKS_DIR)

if PROXY:
    from telebot import apihelper
    apihelper.proxy = {'http': PROXY, 'https': PROXY}
    logger.info(f"Используется прокси: {PROXY}")

bot = telebot.TeleBot(BOT_TOKEN)

user_search_results = {}
inline_tracks = {}
track_file_cache = {}


def create_tracks_keyboard(tracks, user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, track in enumerate(tracks, 1):
        button_text = f"{i}. {track['artist']} - {track['title']}"
        callback_data = f"track_{user_id}_{i-1}"
        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))
    markup.add(types.InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{user_id}"))
    return markup


@bot.message_handler(commands=['start'])
def cmd_start(message):
    params = message.text.split(' ', 1)

    if len(params) > 1 and params[1].startswith('search_'):
        query = params[1].replace('search_', '', 1).strip()
        logger.info(f"Пользователь {message.from_user.id} из inline: {query}")

        class FakeMessage:
            def __init__(self, chat_id, from_user, text):
                self.chat = type('obj', (object,), {'id': chat_id})()
                self.from_user = from_user
                self.text = text

        fake_msg = FakeMessage(message.chat.id, message.from_user, f"/search {query}")
        cmd_search(fake_msg)
        return

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
    args = message.text.split(' ', 1)
    if len(args) < 2 or not args[1].strip():
        bot.send_message(
            message.chat.id,
            "❌ Укажите запрос для поиска!\nПример: `/search Artist - Song`",
            parse_mode='Markdown'
        )
        return

    query = args[1].strip()
    status_msg = bot.send_message(message.chat.id, "🔎 Поиск...")
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

    user_search_results[message.from_user.id] = results

    response_text = f"✅ *Найдено треков: {len(results)}*\n\n"
    for i, track in enumerate(results, 1):
        response_text += format_track_message(track, i)
    response_text += "\n_Выберите трек для скачивания_"

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
    user_id = callback.from_user.id

    logger.info("=" * 60)
    logger.info(f"CALLBACK: пользователь {user_id} выбирает трек")

    if user_id not in user_search_results:
        logger.warning(f"Пользователь {user_id} не имеет результатов поиска")
        bot.answer_callback_query(callback.id, "❌ Срок действия поиска истек. Выполните поиск заново.", show_alert=True)
        return

    try:
        data = callback.data.split('_')
        track_index = int(data[2])
        logger.info(f"Выбран трек индекс: {track_index}")

        tracks = user_search_results[user_id]
        if track_index >= len(tracks):
            logger.error(f"Неверный индекс трека: {track_index}, всего треков: {len(tracks)}")
            bot.answer_callback_query(callback.id, "❌ Неверный выбор", show_alert=True)
            return

        track = tracks[track_index]
        logger.info(f"Трек: {track['artist']} - {track['title']}")
        logger.info(f"Query для yt-dlp: {track['query']}")

        bot.edit_message_text(
            f"⏳ Загрузка: *{track['artist']} - {track['title']}*\n\nЭто может занять время...",
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            parse_mode='Markdown'
        )

        logger.info(f"Скачивание: {track['query']}")
        filename = download_audio_yt(track['query'], proxy=PROXY)

        if filename and os.path.exists(filename):
            file_size = os.path.getsize(filename)
            logger.info(f"Файл: {filename} ({file_size / (1024 * 1024):.2f} MB)")

            start_time = time.time()

            try:
                with open(filename, 'rb') as audio:
                    result = bot.send_audio(
                        callback.message.chat.id,
                        audio,
                        title=track['title'],
                        performer=track['artist'],
                        timeout=300
                    )

                    logger.info(f"✅ Файл отправлен за {time.time() - start_time:.2f} сек")

                    if result.audio and result.audio.file_id:
                        from deezer import get_track_unique_key
                        track_key = get_track_unique_key(track)
                        track_file_cache[track_key] = result.audio.file_id
                        logger.info(f"💾 Сохранен file_id: {track_key}")

                bot.delete_message(callback.message.chat.id, callback.message.message_id)
                logger.info(f"✅ Трек отправлен: {track['artist']} - {track['title']}")
                cleanup_old_files()

            except Exception as send_error:
                logger.error(f"❌ Ошибка отправки: {type(send_error).__name__}: {send_error}")
                raise

        else:
            logger.error(f"Файл не найден")
            bot.edit_message_text(
                "❌ Не удалось скачать трек.\n\n_Возможно, yt_dlp недоступен в вашем регионе._",
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                parse_mode='Markdown'
            )

        bot.answer_callback_query(callback.id)
        logger.info("=" * 60)

    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка callback: {e}", exc_info=True)
        bot.answer_callback_query(callback.id, "❌ Ошибка при выборе трека", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка: {type(e).__name__} - {e}", exc_info=True)
        bot.answer_callback_query(callback.id, "❌ Произошла ошибка", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def callback_cancel_handler(callback):
    user_id = callback.from_user.id

    if user_id in user_search_results:
        del user_search_results[user_id]

    bot.edit_message_text(
        "❌ Поиск отменен",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id
    )
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('inline_download_'))
def callback_inline_download_handler(callback):
    track_id = callback.data.replace('inline_download_', '')

    logger.info("=" * 60)
    logger.info(f"INLINE DOWNLOAD: {track_id}")

    if track_id not in inline_tracks:
        logger.warning(f"Трек {track_id} не найден")
        bot.answer_callback_query(callback.id, "❌ Срок действия ссылки истек. Попробуйте снова.", show_alert=True)
        return

    track = inline_tracks[track_id]
    logger.info(f"Трек: {track['artist']} - {track['title']}")

    if callback.message:
        chat_id = callback.message.chat.id
        message_id = callback.message.message_id
        logger.info(f"Отправляем в чат: {chat_id}")
    else:
        chat_id = callback.from_user.id
        message_id = None
        logger.info(f"Отправляем в личку: {chat_id}")

    try:
        if message_id:
            bot.edit_message_text(
                f"⏳ Загрузка: *{track['artist']} - {track['title']}*\n\nЭто может занять время...",
                chat_id=chat_id,
                message_id=message_id,
                parse_mode='Markdown'
            )
        else:
            msg = bot.send_message(
                chat_id,
                f"⏳ Загрузка: *{track['artist']} - {track['title']}*\n\nЭто может занять время...",
                parse_mode='Markdown'
            )
            message_id = msg.message_id

        logger.info(f"Скачивание: {track['query']}")
        filename = download_audio_yt(track['query'], proxy=PROXY)

        if filename and os.path.exists(filename):
            logger.info(f"Файл: {filename} ({os.path.getsize(filename) / (1024 * 1024):.2f} MB)")

            start_time = time.time()

            try:
                with open(filename, 'rb') as audio:
                    result = bot.send_audio(
                        chat_id,
                        audio,
                        title=track['title'],
                        performer=track['artist'],
                        timeout=300
                    )

                    logger.info(f"✅ Отправлено за {time.time() - start_time:.2f} сек")

                    if result.audio and result.audio.file_id:
                        from deezer import get_track_unique_key
                        track_key = get_track_unique_key(track)
                        track_file_cache[track_key] = result.audio.file_id
                        logger.info(f"💾 Сохранен file_id: {track_key}")

                if message_id:
                    try:
                        bot.delete_message(chat_id, message_id)
                    except Exception as del_err:
                        logger.warning(f"Не удалось удалить сообщение: {del_err}")

                logger.info(f"✅ Трек отправлен: {track['artist']} - {track['title']}")
                cleanup_old_files()

                if track_id in inline_tracks:
                    del inline_tracks[track_id]

            except Exception as send_error:
                logger.error(f"❌ Ошибка: {type(send_error).__name__}: {send_error}")
                raise

        else:
            logger.error(f"Файл не найден")
            error_msg = "❌ Не удалось скачать трек.\n\n_Возможно, yt_dlp недоступен в вашем регионе._"
            if message_id:
                bot.edit_message_text(error_msg, chat_id=chat_id, message_id=message_id, parse_mode='Markdown')
            else:
                bot.send_message(chat_id, error_msg, parse_mode='Markdown')

        bot.answer_callback_query(callback.id, "✅ Трек отправлен!" if filename else "❌ Ошибка")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка: {type(e).__name__} - {e}", exc_info=True)
        bot.answer_callback_query(callback.id, "❌ Произошла ошибка", show_alert=True)


@bot.inline_handler(lambda query: len(query.query) > 0)
def inline_query(inline_query):
    query = inline_query.query.strip()
    logger.info(f"INLINE запрос от {inline_query.from_user.id}: {query}")

    try:
        results = search_deezer(query, limit=10)

        if results is None or not results:
            answer = types.InlineQueryResultArticle(
                id='0',
                title='🔍 Ничего не найдено',
                description='Попробуйте другой запрос',
                input_message_content=types.InputTextMessageContent(
                    message_text=f"🔍 Поиск: {query}\n\n❌ Ничего не найдено."
                )
            )
            try:
                bot.answer_inline_query(inline_query.id, [answer], cache_time=1)
            except Exception as ans_err:
                logger.error(f"Ошибка answer_inline_query: {ans_err}")
            return

        inline_results = []
        from deezer import get_track_unique_key

        for i, track in enumerate(results[:10], 1):
            duration_min = track.get('duration', 0) // 60
            duration_sec = track.get('duration', 0) % 60
            track_key = get_track_unique_key(track)
            cached_file_id = track_file_cache.get(track_key)

            if cached_file_id:
                logger.info(f"✅ Кэш: {track_key}")
                result = types.InlineQueryResultCachedAudio(
                    id=str(i),
                    audio_file_id=cached_file_id,
                )
            else:
                logger.info(f"📝 Нет кэша: {track_key}")

                track_id = f"{inline_query.from_user.id}_{i}"
                inline_tracks[track_id] = track

                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(
                        text="📥 Скачать трек",
                        callback_data=f"inline_download_{track_id}"
                    )
                )

                result = types.InlineQueryResultArticle(
                    id=str(i),
                    title=f"{track['artist']} - {track['title']}",
                    description=f"⏱ {duration_min}:{duration_sec:02d}",
                    input_message_content=types.InputTextMessageContent(
                        message_text=f"🎵 *{track['artist']} - {track['title']}*\n\n"
                                     f"⏱ {duration_min}:{duration_sec:02d}\n\n"
                                     f"Нажмите кнопку ниже для скачивания 👇",
                        parse_mode='Markdown'
                    ),
                    reply_markup=keyboard,
                    thumbnail_url=track.get('cover', '')
                )

            inline_results.append(result)

        try:
            bot.answer_inline_query(inline_query.id, inline_results, cache_time=5)
            logger.info(f"Отправлено {len(inline_results)} результатов")
        except Exception as ans_err:
            logger.error(f"Ошибка отправки: {ans_err}")

    except Exception as e:
        logger.error(f"Ошибка inline: {type(e).__name__}: {e}", exc_info=True)


@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_members(message):
    if message.new_chat_members:
        for member in message.new_chat_members:
            if member.id == bot.get_me().id:
                bot.send_message(
                    message.chat.id,
                    "👋 Привет! Я музыкальный бот.\n\n"
                    "Команды:\n"
                    "/search <запрос> - поиск музыки\n"
                    "/help - справка\n\n"
                    "Также можете использовать меня через @username в любом чате!"
                )
                logger.info(f"Бот добавлен в группу {message.chat.id}")


@bot.message_handler(commands=['search'], chat_types=['group', 'supergroup'])
def cmd_search_group(message):
    args = message.text.split(' ', 1)
    if len(args) < 2 or not args[1].strip():
        bot.reply_to(message, "❌ Укажите запрос: /search Artist - Song")
        return

    query = args[1].strip()
    bot.send_message(message.chat.id, f"🔎 Поиск: {query}\n\n⏳ Пожалуйста, напишите мне в личку для скачивания.")

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
