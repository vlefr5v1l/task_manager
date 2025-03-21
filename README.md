# Task Management System
![CI/CD Pipeline](https://github.com/username/task-management/actions/workflows/main.yml/badge.svg)

Система для отслеживания и управления задачами, где пользователи могут создавать, обновлять и отслеживать прогресс своих задач. Система поддерживает проекты, группы пользователей, очереди задач и уведомления.

## Технологии

- **FastAPI**: для создания API для работы с задачами, проектами и пользователями
- **PostgreSQL**: для хранения данных о задачах, проектах, пользователях и комментариях
- **Kafka**: для обработки событий (создание задачи, изменение статуса, назначение задачи)
- **Redis**: для кэширования текущего статуса задач и списка активных пользователей
- **SQLAlchemy**: для ORM и работы с базой данных
- **Alembic**: для миграций базы данных
- **Pydantic**: для валидации данных
- **JWT**: для аутентификации и авторизации

## Функционал

- Создание и управление задачами
- Разделение задач на проекты, назначение пользователей
- Отслеживание статуса задач и их прогресса
- Комментирование задач
- Система прав доступа (роли пользователей)
- Управление группами и проектами
- Отправка уведомлений о новых задачах или изменениях статуса через Kafka

## Установка и запуск

### Требования

- Python 3.11+
- PostgreSQL
- Redis
- Apache Kafka

### Установка

1. Клонировать репозиторий:

```bash
git clone https://github.com/yourusername/task-manager.git
cd task-manager
```

2. Создать и активировать виртуальное окружение:

```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

3. Установить зависимости:

```bash
pip install -e .
```

4. Создать файл `.env` на основе примера и заполнить необходимые параметры:

```
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=task_manager
POSTGRES_PORT=5432

REDIS_HOST=localhost
REDIS_PORT=6379

KAFKA_BOOTSTRAP_SERVERS=localhost:9092

SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 часа
```

5. Применить миграции:

```bash
alembic upgrade head
```

6. Запустить сервер:

```bash
uvicorn src.main:app --reload
```

### API-документация

После запуска сервера, документация API доступна по следующим адресам:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Тестирование

### Запуск тестов

```bash
# Запуск всех тестов
pytest

# Запуск конкретного модуля тестов
pytest tests/api/test_auth.py

# Запуск тестов с покрытием
pytest --cov=src/ tests/
```

### Структура тестов

- **Unit-тесты** - тестирование отдельных функций и методов
- **Интеграционные тесты** - тестирование взаимодействия между компонентами
- **End-to-End тесты** - тестирование API-эндпоинтов

## Структура проекта

```
task-manager/
├── alembic/                  # Миграции базы данных
├── src/                      # Исходный код
│   ├── api/                  # API-эндпоинты
│   │   └── v1/               # Версия API
│   │       ├── endpoints/    # Обработчики запросов
│   │       └── router.py     # Маршрутизация API
│   ├── core/                 # Ядро приложения
│   │   ├── config.py         # Конфигурация
│   │   └── security.py       # Безопасность (JWT, пароли)
│   ├── db/                   # Работа с базой данных
│   │   ├── base.py           # Базовая модель
│   │   └── session.py        # Сессия БД
│   ├── models/               # Модели данных (SQLAlchemy)
│   ├── schemas/              # Схемы данных (Pydantic)
│   ├── services/             # Бизнес-логика
│   └── main.py               # Точка входа
├── tests/                    # Тесты
│   ├── conftest.py           # Конфигурация тестов
│   ├── api/                  # Тесты API
│   └── unit/                 # Модульные тесты
├── .env                      # Переменные окружения
├── alembic.ini               # Конфигурация Alembic
├── pyproject.toml            # Конфигурация проекта
└── README.md                 # Документация
```