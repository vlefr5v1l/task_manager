#!/bin/bash

# Копируем пример .env, если не существует
if [ ! -f .env ]; then
    cp .env.example .env
    echo ".env file created from .env.example"
fi

# Создаем сеть Docker, если она не существует
if ! docker network inspect backend &>/dev/null; then
    docker network create backend
    echo "Docker network 'backend' created"
fi

# Запускаем docker-compose
docker-compose up -d

# Применяем миграции
echo "Waiting for PostgreSQL to start..."
sleep 5
docker-compose exec app alembic upgrade head

echo "============================================="
echo "Task Management System is running!"
echo "API: http://localhost:8000/docs"
echo "pgAdmin: http://localhost:5050"
echo "============================================="