FROM python:3.11-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Зависимости ОС (psycopg2 требует libpq-dev)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

EXPOSE 8000
