FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем yt-dlp последней версии
RUN wget -O /usr/local/bin/yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файлы проекта
COPY bot.py .
COPY config.py .
COPY logger.py .
COPY deezer.py .
COPY downloader.py .

# Создаем необходимые директории
RUN mkdir -p tracks logs

# Устанавливаем переменную окружения для Python
ENV PYTHONUNBUFFERED=1

# Запуск бота
CMD ["python", "bot.py"]
