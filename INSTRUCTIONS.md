# Полная инструкция по развёртыванию и использованию

## 1. Настройка окружения

### 1.1 Переменные окружения (файл `.env`)

Скопируйте `.env.example` в `.env` и заполните:

| Переменная | Описание | Значение по умолчанию |
|-----------|----------|-----------------------|
| `POSTGRES_USER` | Пользователь PostgreSQL | `game_suggestions_user` |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | **обязательно смените** |
| `POSTGRES_DB` | Имя базы данных | `game_suggestions` |
| `DATABASE_URL` | Строка подключения SQLAlchemy | формируется из предыдущих |
| `SECRET_KEY` | Секретный ключ для JWT | **обязательно смените** |
| `ALGORITHM` | Алгоритм JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена | `30` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Настройки почтового сервера | оставьте пустыми для консольного вывода |
| `EMAIL_VERIFICATION_REQUIRED` | Требовать подтверждение email | `False` (в production `True`) |
| `UPLOAD_DIR` | Папка для загруженных файлов | `uploads` |
| `MAX_UPLOAD_SIZE_MB` | Максимальный размер файла (МБ) | `10` |

### 1.2 Email-верификация

В режиме разработки (`EMAIL_VERIFICATION_REQUIRED=False`) пользователи могут входить без подтверждения email. Для включения проверки установите `True` и настройте SMTP-сервер. При отсутствии SMTP-настроек письма выводятся в консоль (логи `app` контейнера).

## 2. Запуск с Docker

```bash
docker compose up -d --build
```

Приложение будет доступно на [http://localhost:8000](http://localhost:8000).

При первом запуске автоматически создаются таблицы базы данных и администратор по умолчанию:

- Email: `admin@example.com`
- Пароль: `admin123`

**Немедленно измените пароль через веб-интерфейс (личный кабинет)** или через команду в контейнере (см. раздел 5).

## 3. Локальная разработка (без Docker)

### 3.1 Установка зависимостей

```
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 3.2 Локальная PostgreSQL

Убедитесь, что PostgreSQL запущен, и создайте базу данных:

```
sudo -u postgres createdb game_suggestions
```

Настройте `.env`, указав локальный `DATABASE_URL`:

```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/game_suggestions
```

### 3.3 Запуск

```
uvicorn app.main:app --reload
```

## 4. Управление миграциями (Alembic)

При использовании Docker таблицы создаются автоматически через `Base.metadata.create_all`. Для production и контроля версий базы данных используйте Alembic:

1. Инициализация (однократно):

```
alembic init -t async migrations
```
1. Настройте `alembic.ini` и `migrations/env.py` (пример в проекте).
1. Создание миграции после изменения моделей:

```
alembic revision --autogenerate -m "описание"
alembic upgrade head
```

Для Docker-окружения выполните:

```
docker compose exec app alembic upgrade head
```

## 5. Управление пользователями через CLI

### Создание администратора вручную

Зайдите в контейнер приложения и выполните Python-скрипт:

```
docker compose exec app python -c "
from app.database import async_session_maker
from app.services.user_service import create_admin

import asyncio
async def main():
    async with async_session_maker() as session:
        await create_admin(session, 'newadmin@example.com', 'securepassword')
        await session.commit()

asyncio.run(main())
"
```

Или используйте встроенный скрипт `scripts/create_admin.py` (создайте при необходимости).

## 6. Структура проекта

```
game-suggestions/
├── app/
│   ├── api/                  # Роутеры (auth, suggestions, admin)
│   ├── models/               # SQLAlchemy модели
│   ├── schemas/              # Pydantic схемы
│   ├── services/             # Бизнес-логика
│   ├── templates/            # Jinja2 шаблоны
│   ├── static/               # CSS, JS
│   ├── dependencies.py       # Зависимости FastAPI
│   ├── config.py             # Конфигурация
│   ├── database.py           # Подключение к БД
│   └── main.py               # Точка входа
├── uploads/                  # Загруженные файлы
├── migrations/               # Alembic (если используется)
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
└── INSTRUCTIONS.md
```

## 7. API Документация

Интерактивная документация доступна после запуска:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

Основные эндпоинты:

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `POST` | `/auth/register` | Все | Регистрация |
| `POST` | `/auth/login` | Все | Вход |
| `GET` | `/` | Все | Главная (список предложений) |
| `POST` | `/suggestions` | Авторизованные | Создать предложение |
| `GET` | `/suggestions/my` | Авторизованные | Мои предложения |
| `GET` | `/admin/dashboard` | Админ | Статистика |
| `GET` | `/admin/suggestions` | Админ | Все предложения |
| `PATCH` | `/admin/suggestions/{id}/status` | Админ | Изменить статус |
| `DELETE` | `/admin/suggestions/{id}` | Админ | Удалить предложение |
| `GET` | `/admin/users` | Админ | Список пользователей |
| `PUT` | `/admin/users/{id}/ban` | Админ | Забанить/разбанить |

## 8. Переход на облачное хранилище (S3/MinIO)

Для использования S3 замените сервис хранилища в `app/dependencies.py`:

1. Реализуйте класс `S3Storage` с интерфейсом `StorageInterface`.
1. Измените зависимость `get_storage` на возврат экземпляра `S3Storage`.
1. Конфигурация доступа через переменные окружения.

Пример (потребуется `aiobotocore`):

```
class S3Storage(StorageInterface):
    def __init__(self, bucket: str, ...):
        self.bucket = bucket
        # инициализация клиента

    async def upload(self, content: bytes, filename: str) -> str:
        # загрузка в S3, возврат URL
        ...
```

## 9. Часто задаваемые вопросы

**Q: Не отправляются письма подтверждения.**
A: Проверьте настройки SMTP или установите `EMAIL_VERIFICATION_REQUIRED=False` для разработки. Письма также логируются в консоль.

**Q: Как добавить другую роль?**
A: В модели пользователя есть поле `role`, по умолчанию `"user"`. Для добавления новой роли измените Enum в `app/models/user.py` и обновите проверки в `RoleChecker`.

**Q: Где хранятся загруженные файлы?**
A: В папке `uploads/` (примонтирована к контейнеру как volume). Пути к файлам сохраняются в БД.

**Q: Как обновить пароль администратора по умолчанию?**
A: Войдите как админ, перейдите в профиль (/profile) и измените пароль. Либо через CLI (раздел 5).

**Q: Как запустить без Docker?**
A: Следуйте разделу 3.

## 10. Безопасность в production

- Сгенерируйте надёжный `SECRET_KEY`: `openssl rand -hex 32`
- Установите `EMAIL_VERIFICATION_REQUIRED=True`
- Используйте HTTPS (например, через nginx или Traefik)
- Настройте брандмауэр для PostgreSQL (закрыть порт 5432)
- Регулярно обновляйте зависимости
- Включите ограничение частоты запросов (middleware)

