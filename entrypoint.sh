#!/bin/bash
set -e

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "🔄 Ожидание PostgreSQL..."
until nc -z "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}"; do
    sleep 0.5
done
echo "✅ PostgreSQL доступен"

echo "📦 Применение миграций..."
python manage.py migrate --noinput

echo "🧼 Сборка статики..."
python manage.py collectstatic --noinput

echo "✅ Установка Webhook..."
python manage.py setwebhook || echo "⚠️  setwebhook завершился с ошибкой — продолжаем запуск"

echo "🚀 Запуск Gunicorn..."
exec gunicorn src.asgi:application \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${WEB_PORT:-8000}" \
    --log-level info \
    --access-logfile -
