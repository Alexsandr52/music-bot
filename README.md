# 🎵 Telegram Music Bot

Telegram бот для поиска и скачивания музыки с помощью Deezer API и yt-dlp.

## ✨ Возможности

- 🔍 **Поиск музыки** через Deezer API
- 📥 **Скачивание треков** с YouTube через yt-dlp
- ⚡ **Inline режим** - используйте `@botname query` в любом чате
- 💾 **Кэширование** - скачанные треки отправляются мгновенно
- 👥 **Работа в группах** - добавляйте бота в чаты
- 🎧 **Высокое качество** - MP3 128kbps
- 📊 **Rotating logs** - автоматическая ротация логов
- 🐳 **Docker support** - легкое развертывание

## 📋 Требования

- Python 3.11+
- FFmpeg
- Telegram Bot Token
- Прокси (для регионов без доступа к YouTube)

## 🚀 Быстрый старт

### Локальная установка

1. **Клонируйте репозиторий**
```bash
git clone https://github.com/yourusername/music-bot.git
cd music-bot
```

2. **Создайте виртуальное окружение**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. **Установите зависимости**
```bash
pip install -r requirements.txt
```

4. **Создайте файл `.env`**
```bash
cp .env.example .env
```

5. **Получите токен бота**
- Откройте [@BotFather](https://t.me/BotFather) в Telegram
- Отправьте `/newbot`
- Следуйте инструкциям
- **Важно:** Включите **inline mode** через `/setinline`
- Скопируйте токен в `.env`:
```
BOT_TOKEN=your_bot_token_here
```

6. **Настройте прокси** (если yt-dlp не работает в вашем регионе)
```
PROXY=http://user:password@host:port
# или
PROXY=socks5://user:password@host:port
```

7. **Запустите бота**
```bash
python bot.py
```

### Docker deployment

1. **Создайте `.env` файл**
```bash
cp .env.example .env
# Отредактируйте .env с вашими данными
```

2. **Запустите через Docker Compose**
```bash
docker-compose up -d
```

3. **Проверьте логи**
```bash
docker-compose logs -f
```

## 📖 Использование

### Личные сообщения

- `/search <запрос>` - поиск музыки
  - Пример: `/search Imagine Dragons - Believer`
- `/start` - начало работы
- `/help` - справка

### Inline режим (в любом чате)

```
@botname Imagine Dragons - Believer
```

**Как работает inline режим:**
1. Введите `@botname запрос` в любом чате
2. Если трек уже скачивали → **отправится сразу как аудиофайл** (бот не нужен в чате!)
3. Если трек новый → появится кнопка "Скачать трек" (бот должен быть в чате)
4. После скачивания трек кэшируется и будет работать мгновенно

### В группах

- Добавьте бота в группу
- Используйте `/search <запрос>`
- Бот предложит написать в личку для скачивания

## 🔧 Настройка прокси для yt-dlp

**Проблема:** yt-dlp не работает в некоторых регионах (РФ, др.) без VPN.

### Решение 1: Cloudflare WARP (бесплатно)

```bash
# Установка WARP
brew install --cask cloudflare-warp  # Mac
# Или скачайте с https://1.1.1.1/

# Подключение
warp-cli register
warp-cli connect

# Установка warp-socks
pip install warp-socks

# Запуск SOCKS прокси
warp-socks --port 4000

# В .env:
PROXY=socks5://127.0.0.1:4000
```

### Решение 2: Платный прокси (рекомендуется)

- **proxy6.net** - от ~30 руб/мес
- **astraproxy.com** - качественные прокси
- **proxy-seller.com** - есть SOCKS5

```
PROXY=socks5://user:pass@host:port
```

### Решение 3: TOR (бесплатно, медленно)

```bash
# Установка TOR
brew install tor  # Mac
apt install tor   # Linux

# В .env:
PROXY=socks5://127.0.0.1:9050
```

## 📁 Структура проекта

```
music-bot/
├── bot.py              # Главный файл бота
├── config.py           # Конфигурация
├── logger.py           # Настройка логирования
├── deezer.py           # Поиск через Deezer API
├── downloader.py       # Скачивание через yt-dlp
├── tracks/             # Папка для треков (создается автоматически)
├── logs/               # Логи (создаются автоматически)
├── .env                # Переменные окружения (создается вами)
├── .env.example        # Пример конфигурации
├── Dockerfile          # Docker образ
├── docker-compose.yml  # Docker Compose конфиг
├── requirements.txt    # Зависимости Python
└── README.md           # Этот файл
```

## 🔐 Безопасность

- **Никогда не коммитьте** `.env` файл (он в .gitignore)
- **Используйте сложные пароли** для прокси
- **Ограничьте доступ** к логам на сервере
- **Используйте файрвол** для ограничения сетевого доступа

## 🐛 Troubleshooting

### Бот не запускается

- Проверьте токен в `.env`
- Убедитесь, что все зависимости установлены: `pip install -r requirements.txt`
- Проверьте наличие FFmpeg: `ffmpeg -version`

### Не находит музыку

- Попробуйте изменить запрос (английский/русский)
- Проверьте подключение к интернету
- Проверьте логи: `tail -f logs/bot.log`

### Не скачивает музыку

- **Убедитесь что прокси настроен** в `.env`
- Проверьте работу прокси: `curl -x proxy_url https://youtube.com`
- yt-dlp может быть заблокирован - используйте прокси
- Проверьте логи ошибок: `tail -f logs/errors.log`

### Inline режим не работает

1. Откройте @BotFather
2. `/setinline`
3. Выберите вашего бота
4. Отправьте текст-заглушку или оставьте пустым

## 📦 Зависимости

```
pyTelegramBotAPI>=4.14.0
yt-dlp>=2023.0.0
requests>=2.31.0
python-dotenv>=1.0.0
```

## 🚀 Развертывание на VPS

### Требования к VPS

- 1 CPU core
- 512MB RAM
- 10GB дисковое пространство
- Ubuntu 20.04+ / Debian 11+

### Установка

1. **Установите Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

2. **Клонируйте репозиторий**
```bash
git clone https://github.com/yourusername/music-bot.git
cd music-bot
```

3. **Настройте конфигурацию**
```bash
cp .env.example .env
nano .env  # Отредактируйте
```

4. **Запустите**
```bash
docker-compose up -d
```

5. **Проверьте статус**
```bash
docker-compose ps
docker-compose logs -f
```

## 📝 Лицензия

MIT License

## 🤝 Вклад

Pull requests приветствуются!

1. Fork проект
2. Создайте ветку (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add AmazingFeature'`)
4. Push в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## ❓ FAQ

**Q: Почему нужен прокси?**
A: yt-dlp не работает в некоторых регионах без доступа к YouTube.

**Q: Можно ли без прокси?**
A: Да, если у вас есть доступ к YouTube.

**Q: Какое качество музыки?**
A: MP3 128kbps (баланс качества и размера).

**Q: Сколько места занимают треки?**
A: ~1-2MB за минуту, 3-5MB за трек.

**Q: Бот бесплатный?**
A: Да, но нужен платный или бесплатный прокси для yt-dlp.

**Q: Как работает кэширование?**
A: После первого скачивания трек сохраняется на серверах Telegram и при повторном запросе отправляется мгновенно в любой чат без бота. Кэш хранится в памяти и очищается при перезапуске.

**Q: Трек отправляется сразу в inline?**
A: Только если он был скачан ранее. Новые треки требуют нажатия кнопки "Скачать" и присутствия бота в чате.

## 📞 Поддержка

- Создайте **Issue** для багов
- **Pull Request** для улучшений
- Звездочка ⭐ если нравится проект

---

**Сделано с ❤️ для музыкального сообщества**
