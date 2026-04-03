# ManagementQuizBot

A Django-based Telegram bot application for creating, managing, and taking quizzes. Supports both individual and group quiz sessions with a full-featured web admin panel.

---

## Features

- **Quiz Management** — Create quizzes with categories, parts, questions, and answer options
- **Individual & Group Quizzes** — Users can take quizzes privately or in group chats with Telegram polls
- **Admin Panel** — Django Jazzmin-powered admin with import/export, rich text editors, and inline management
- **Async Tasks** — Celery workers for background jobs (invite links, Excel exports, file cleanup)
- **Support System** — In-bot support request flow with admin response management
- **Multi-language Support** — Locale-based translations
- **Webhook & Polling Modes** — Webhook for production, polling for development
- **Statistics Export** — Generate Excel reports for group quiz results

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web Framework | Django 5.0.6 |
| Bot Framework | Aiogram 3.17.0 |
| ASGI Server | Gunicorn + Uvicorn workers |
| Database | PostgreSQL 16 |
| Connection Pooling | PGBouncer |
| Cache / Broker | Redis 7 |
| Task Queue | Celery 5.4.0 + Django-Celery-Beat 2.7.0 |
| Admin UI | Django-Jazzmin 3.0.0 |
| Rich Text | CKEditor 6.7.1, TinyMCE 4.1.0 |
| Data Export | pandas 2.2.2, openpyxl 3.1.5 |
| Google Integration | gspread, google-auth |

---

## Project Structure

```
ManagementQuizBot/
├── src/                          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery_app.py
│
├── bot/                          # Telegram bot logic
│   ├── app.py                    # Polling mode setup
│   ├── webhook.py                # Webhook service (production)
│   ├── handlers/                 # Message & callback handlers
│   │   ├── admin.py
│   │   ├── users.py
│   │   ├── groups.py
│   │   └── channels.py
│   ├── keyboards/                # Reply & inline keyboards
│   ├── states/                   # FSM conversation states
│   ├── filters/                  # Custom message filters
│   ├── middlewares/              # Logging & access middleware
│   └── utils/                    # Bot helpers (ORM, texts, functions)
│
├── common/                       # Core app (profiles, settings, webhook)
│   ├── models.py                 # TelegramProfile, Data
│   ├── views.py                  # Webhook endpoint
│   ├── urls.py
│   ├── admin.py
│   └── management/commands/
│       ├── setwebhook.py
│       ├── deletewebhook.py
│       ├── runbot.py
│       └── language.py
│
├── quiz/                         # Quiz domain app
│   ├── models.py                 # Quiz, Question, Option, UserQuiz, GroupQuiz
│   ├── admin.py
│   ├── choices.py
│   ├── managers.py
│   └── tasks.py                  # Celery tasks
│
├── support/                      # Support request app
│   ├── models.py                 # SupportMessage
│   ├── admin.py
│   └── choices.py
│
├── utils/                        # Shared utilities
│   ├── models.py                 # BaseModel, Profile base classes
│   ├── functions.py              # HTML cleaning, file type detection
│   ├── choices.py                # Role choices
│   └── bot.py                    # Bot utility functions
│
├── templates/                    # HTML templates
├── static/                       # Static assets
├── media/                        # User-uploaded files
├── locale/                       # Translation files
├── logs/                         # Application logs
│
├── Dockerfile
├── docker-compose.yml            # Production compose
├── dev-docker-compose.yaml       # Development compose
├── entrypoint.sh
├── manage.py
├── Makefile
├── requirements.txt
├── pyproject.toml
└── env.example
```

---

## Prerequisites

- Docker & Docker Compose
- A Telegram Bot token (from [@BotFather](https://t.me/BotFather))
- A publicly accessible domain with HTTPS (for webhook mode)

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/ChoriyevJamshid/ManagementQuizBot.git
cd ManagementQuizBot
```

### 2. Configure environment variables

```bash
cp env.example .env
```

Edit `.env` and fill in all required values (see [Environment Variables](#environment-variables) section below).

### 3. Build and start containers

```bash
make start
```

Or manually:

```bash
docker compose up -d --build
```

### 4. Run database migrations

```bash
docker compose exec django python manage.py migrate
```

### 5. Create a Django superuser

```bash
docker compose exec django python manage.py createsuperuser
```

### 6. Set Telegram webhook (production)

```bash
docker compose exec django python manage.py setwebhook
```

The admin panel is available at `https://<your-domain>/admin/`.

---

## Development Setup

Use the development compose file which includes hot-reload and the Django debug toolbar:

```bash
docker compose -f dev-docker-compose.yaml up -d --build
```

Run the bot in polling mode (no domain required):

```bash
docker compose -f dev-docker-compose.yaml exec django python manage.py runbot
```

---

## Environment Variables

Copy `env.example` to `.env` and configure the following:

```dotenv
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,localhost

# Telegram Bot
API_TOKEN=123456789:AABBCCDDEEFFaabbccddeeff
ADMIN=123456789                    # Telegram user ID of the admin
WEB_DOMAIN=https://yourdomain.com  # Must be HTTPS for webhooks
WEB_PORT=8000

# Database (PostgreSQL)
DJANGO_DB=pgbouncer                # sqlite | postgresql | pgbouncer
DB_NAME=quizbot
DB_USER=quizbot
DB_PASSWORD=strongpassword
DB_HOST=postgres
DB_PORT=5432

# PGBouncer (connection pooling)
PGBOUNCER_HOST=pgbouncer
PGBOUNCER_PORT=6432
POOL_MODE=transaction
MAX_CLIENT_CONN=100
DEFAULT_POOL_SIZE=20

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Security
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
```

---

## Makefile Commands

```bash
make start       # Build and start all containers
make up          # Start containers without rebuild
make down        # Stop containers
make down-v      # Stop containers and remove volumes
make build       # Build Docker images
```

---

## Django Management Commands

| Command | Description |
|---|---|
| `python manage.py setwebhook` | Register the bot webhook with Telegram |
| `python manage.py deletewebhook` | Remove the registered webhook |
| `python manage.py runbot` | Run the bot in polling mode (development) |
| `python manage.py language` | Manage translations |

---

## Docker Services

| Service | Description |
|---|---|
| `postgres` | PostgreSQL 16 database |
| `pgbouncer` | Connection pool manager |
| `redis` | Cache and Celery message broker |
| `django` | Django app (Gunicorn + Uvicorn) |
| `bot` | Telegram bot in polling mode (optional) |
| `celery` | Async task worker |
| `celery_beat` | Scheduled task runner |

---

## Database Models

### `quiz` app

| Model | Description |
|---|---|
| `Category` | Quiz categories with active/pending status |
| `Quiz` | Quiz definition linked to an owner |
| `QuizPart` | Section of a quiz |
| `Question` | Individual question in a part |
| `Option` | Answer option for a question |
| `UserQuiz` | User quiz attempt (score, timing, status) |
| `GroupQuiz` | Group quiz instance with Telegram poll |
| `TelegramCommand` | Configurable bot commands |

### `common` app

| Model | Description |
|---|---|
| `TelegramProfile` | Extended Telegram user profile (chat_id, username, role) |
| `Data` | Singleton app configuration (file types, bot username) |

### `support` app

| Model | Description |
|---|---|
| `SupportMessage` | User support requests with admin responses |

---

## Bot Conversation States (FSM)

| State Group | Description |
|---|---|
| `MainState` | Main menu, language selection, instructions |
| `CreateQuizState` | Quiz creation workflow |
| `QuizState` | Taking a quiz or admin test run |
| `SupportState` | Support request submission |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/bot/<webhook_token>/` | Telegram webhook receiver |
| `GET/POST` | `/admin/` | Django admin panel |
| `POST` | `/ckeditor/upload/` | CKEditor file upload |

---

## Celery Tasks

| Task | Description |
|---|---|
| `get_group_invite_link` | Fetch invite link for a group chat |
| `group_quiz_create_file` | Generate Excel statistics for a group quiz |
| `remove_quiz_files` | Clean up old uploaded quiz files |

---

## Logging

Logs are written to `logs/django.log` at `WARNING` level and above with full timestamp and module information.

---

## Dependencies

Full list is in `requirements.txt`. Key packages:

```
aiogram==3.17.0
Django==5.0.6
uvicorn==0.35.0
celery==5.4.0
django-celery-beat==2.7.0
django-jazzmin==3.0.0
beautifulsoup4==4.12.3
pandas==2.2.2
openpyxl==3.1.5
python-docx==1.1.2
gspread==6.1.4
google-auth==2.34.0
psycopg2-binary==2.9.9
redis==5.0.8
```

---

## License

This project is private. All rights reserved.