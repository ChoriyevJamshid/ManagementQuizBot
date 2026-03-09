#!/bin/bash
set -e

export $(grep -v '^#' .env | xargs)

echo "🔄 Ожидание PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 0.5
done

echo "✅ PostgreSQL доступен"

echo "📦 Применение миграций..."
python manage.py migrate --noinput

echo "🧼 Сборка статики..."
python manage.py collectstatic --noinput

# if [ "$WITH_BOT" = "true" ]; then
  # echo "❌ Удаление Webhook (запущен with-bot)..."
  # python manage.py deletewebhook
# else
  echo "✅ Установка Webhook (бот не активен)..."
  python manage.py setwebhook
# fi

echo "🚀 Запуск Gunicorn..."
exec gunicorn src.asgi:application \
    --worker-class=uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:$WEB_PORT
