# Отчёт: Система запланированных тестов для групп

**Дата:** 2026-05-02  
**Проект:** ManagementQuizBot  
**Охват:** Task 1 + Task 2 + исправление критической ошибки event loop

---

## 1. Общая архитектура

Система запланированных тестов позволяет администратору или модератору создать расписание:
выбрать группу, одну или несколько частей квиза, дату и время — и в назначенное время тест
автоматически запустится в Telegram-группе без участия человека.

**Стек:** Django 5 · Aiogram 3 · PostgreSQL · Redis · Celery  
**Доступ:** только пользователи с ролью `ADMIN` или `MODERATOR`  
**Тайм-зона:** Asia/Tashkent (UTC+5), хранение в UTC

---

## 2. Модель данных

### `ScheduledSession` (`quiz/models.py`)

| Поле | Тип | Описание |
|---|---|---|
| `created_by` | FK → TelegramProfile | Кто создал расписание |
| `group_id` | CharField | Telegram ID группы |
| `group_title` | CharField | Название группы (кэш) |
| `part_ids` | JSONField | Список ID частей квиза в порядке запуска |
| `scheduled_at` | DateTimeField | Время запуска (UTC) |
| `status` | CharField | `pending / running / completed / cancelled` |
| `celery_task_ids` | JSONField | ID Celery-задач для возможного revoke |

### Жизненный цикл статусов

```
PENDING ──► RUNNING ──► COMPLETED
   │            │
   └────────────┴──► CANCELLED
```

- **PENDING** — расписание создано, ждёт времени старта
- **RUNNING** — сессия запущена, хотя бы одна часть в процессе
- **COMPLETED** — все части успешно завершены
- **CANCELLED** — отменено: вручную, командой `/stop`, ошибкой, или из-за конфликта

---

## 3. Полный флоу выполнения

### 3.1 Создание расписания (бот → пользователь)

```
Пользователь (Admin/Moderator)
  │
  ├─ Открывает «📅 Rejalashtirilgan testlar» в главном меню
  ├─ Кнопка «➕ Yangi jadval»
  ├─ Шаг 1: выбор группы (из истории GroupQuiz или ввод вручную)
  ├─ Шаг 2: выбор частей квиза (мультивыбор ✅/☐)
  ├─ Шаг 3: выбор даты (Сегодня / Завтра / Послезавтра / +3 дня)
  ├─ Шаг 4: ввод времени текстом (HH:MM, Asia/Tashkent)
  └─ Шаг 5: подтверждение → create_scheduled_session()
```

**`create_scheduled_session()` (`bot/utils/orm.py`):**
1. Создаёт `ScheduledSession` (status=`PENDING`) в БД
2. Планирует Celery-задачи через `apply_async(eta=...)`:
   - `notify_scheduled_session(..., "1h")` — если до старта > 1 часа
   - `notify_scheduled_session(..., "10m")` — если > 10 минут
   - `notify_scheduled_session(..., "5m")` — если > 5 минут
   - `start_scheduled_session(session_id)` — точно в scheduled_at
3. Сохраняет все task_id в `session.celery_task_ids`

### 3.2 Уведомления (`notify_scheduled_session`)

Отправляет текстовое сообщение в группу за 1 ч / 10 мин / 5 мин до старта.
Перед отправкой проверяет `session.status == PENDING` — если отменена, молчит.

### 3.3 Запуск сессии (`start_scheduled_session`)

**Ключевое архитектурное решение (Task 2):**  
Один Celery-таск на всю сессию. Один `asyncio.run()` = один event loop =
один Redis-клиент на всё время выполнения.

```
start_scheduled_session(session_id)          [Celery task, soft_limit=3h]
  └─ _run_session(session_id)                [sync]
       └─ asyncio.run(_run())                [ОДИН event loop на всю сессию]
            ├─ redis_group.redis_client = новый aioredis клиент
            ├─ bot = Bot(token=...)
            └─ _run_all_parts(session_id, bot)
                 ├─ session.status: PENDING → RUNNING
                 │
                 ├─ [часть 0]
                 │   ├─ проверка статуса (CANCELLED? → выход)
                 │   ├─ _launch_one_part() → GroupQuiz (STARTED)
                 │   ├─ start_group_testing(group_quiz, bot) → bool
                 │   │   ├─ animate_texts() (обратный отсчёт ~10 сек)
                 │   │   ├─ run_group_quiz_loop() → True/False
                 │   │   │   ├─ вопрос 1 → sleep(timer+2)
                 │   │   │   ├─ вопрос 2 → sleep(timer+2)
                 │   │   │   └─ ... → send_statistics() → return True
                 │   │   └─ return True
                 │   └─ completed_normally = True
                 │
                 ├─ _sleep_interruptible(120s)  ← пауза с проверкой каждые 5с
                 │
                 ├─ [часть 1]
                 │   └─ (аналогично)
                 │
                 └─ session.status: RUNNING → COMPLETED
```

### 3.4 Логика `_launch_one_part()`

Перед запуском каждой части выполняется проверка группы:

| Состояние существующего GroupQuiz | Действие |
|---|---|
| FINISHED / CANCELED | Не найден — запускаем нормально |
| STARTED + Redis-ключ активен | Группа занята → сессия CANCELLED, уведомление в группу |
| STARTED + Redis-ключ не активен | Stale-запись — чистим, запускаем нормально |
| INIT или PAUSED | Квиз в процессе → сессия CANCELLED, уведомление в группу |

### 3.5 Обработка остановки (`/stop` в группе)

```
stop_handler (aiogram, бот-процесс):
  └─ redis_group.set_quiz_inactive()          ← помечает Redis-ключ удалённым
  └─ send_statistics(is_cancelled=True)       ← GroupQuiz.status = CANCELED

run_group_quiz_loop (Celery-воркер, тот же event loop):
  └─ следующая итерация: is_quiz_active() == False
  └─ return False

_run_all_parts:
  └─ completed_normally = False
  └─ ScheduledSession.status = CANCELLED
  └─ выход из цикла, остальные части не запускаются
```

### 3.6 Отмена через панель администратора

```
ss_cancel_session_handler (бот)
  └─ cancel_scheduled_session(session_id)     (orm.py)
       ├─ revoke() всех task_ids из celery_task_ids
       │   (эффективно только если задача ещё не запущена)
       └─ ScheduledSession.status = CANCELLED

_sleep_interruptible (Celery, пауза между частями):
  └─ каждые 5 сек читает DB статус
  └─ status != RUNNING → return False → выход из _run_all_parts

_run_all_parts (начало следующей части):
  └─ проверка статуса перед каждой частью → CANCELLED → выход
```

---

## 4. Затронутые файлы и изменения

### Task 1 (создание системы)

| Файл | Изменение |
|---|---|
| `quiz/models.py` | Добавлена модель `ScheduledSession` |
| `quiz/choices.py` | Добавлен `SessionStatus` |
| `quiz/tasks.py` | Добавлены `notify_scheduled_session`, `start_scheduled_session` |
| `bot/states/main.py` | Добавлен `ScheduledSessionState` |
| `bot/utils/orm.py` | Добавлены `create_scheduled_session`, `cancel_scheduled_session`, `get_active_scheduled_sessions`, `get_distinct_groups`, `get_all_quiz_parts` |
| `bot/keyboards/inline_kb.py` | Добавлены маркапы: `ss_groups_markup`, `ss_parts_markup`, `ss_date_markup`, `ss_confirm_markup`, `ss_list_markup`, `ss_detail_markup` |
| `bot/handlers/users/scheduled_sessions.py` | Новый файл — все хендлеры создания/просмотра/отмены расписаний |
| `bot/handlers/users/__init__.py` | Регистрация хендлеров scheduled_sessions |
| `languages/uz.json` | Все тексты для SS-экранов |
| `quiz/migrations/0029_*.py` | Миграция: добавлена `ScheduledSession` |

### Task 2 (исправление багов)

| Файл | Что исправлено |
|---|---|
| `bot/handlers/groups/testing.py` | **Баг 1**: `run_group_quiz_loop` теперь возвращает `bool`; сессия помечается CANCELLED при `/stop` через caller (`_run_all_parts`), а не внутри loop |
| `quiz/tasks.py` | **Баг 2**: исключение в ходе выполнения квиза помечает сессию CANCELLED |
| `quiz/tasks.py` | **Баг 3**: конфликт с существующим квизом помечает сессию CANCELLED + уведомление |
| `bot/utils/orm.py` | Аннотация `cancel_scheduled_session` исправлена: `bool` → `ScheduledSession \| None` |
| `bot/utils/orm.py` | Убран `__import__('datetime').timedelta` антипаттерн |
| `languages/uz.json` | Добавлен ключ `ss_cancelled_due_to_active_quiz` |

### Архитектурная реструктуризация (критическая ошибка event loop)

| Файл | Изменение |
|---|---|
| `quiz/tasks.py` | **Удалены**: `continue_scheduled_session`, `_launch_session_part`, `_cancel_session_blocked` (sync) |
| `quiz/tasks.py` | **Добавлены**: `_run_session`, `_run_all_parts`, `_sleep_interruptible`, `_launch_one_part`, `_cancel_session_blocked` (async) |
| `bot/handlers/groups/testing.py` | Удалены параметры `session_id`, `next_part_index` из `start_group_testing` и `run_group_quiz_loop` |
| `bot/handlers/groups/testing.py` | Прямой импорт `redis_client` заменён на `redis_group.redis_client` |

---

## 5. Решённые технические проблемы

### Проблема: `RuntimeError: Future attached to a different loop`

**Причина:** Старая архитектура вызывала `asyncio.run()` **для каждой части квиза** отдельной Celery-задачей (`start_scheduled_session` → часть 0, `continue_scheduled_session` → часть 1, …). Каждый `asyncio.run()` создаёт **новый event loop**, а затем закрывает его. Модульный `redis.asyncio` клиент в `redis_group.py` создаётся один раз и хранит TCP-соединения, привязанные к event loop первого вызова. При втором `asyncio.run()` Redis-клиент пытается использовать объекты закрытого loop → ошибка.

Дополнительный нюанс: в `testing.py` был прямой импорт `from bot.utils.redis_group import redis_client` — при пересоздании модульного атрибута `redis_group.redis_client` этот локальный псевдоним оставался указателем на старый объект.

**Решение:** Единый `asyncio.run()` на всю сессию. Свежий Redis-клиент и Bot создаются внутри `_run()` и живут до конца сессии, после чего корректно закрываются в `finally`. `testing.py` теперь обращается к Redis только через `redis_group.redis_client` (модульный атрибут), а не через локальный псевдоним.

---

## 6. Производительность и ограничения

| Параметр | Значение | Примечание |
|---|---|---|
| `soft_time_limit` | 10 800 с (3 ч) | Максимальное время одной сессии |
| `time_limit` | 11 100 с | Hard kill по истечении |
| Пауза между частями | 120 с (2 мин) | С проверкой отмены каждые 5 с |
| Параллельные сессии | = concurrency воркера | Каждая сессия блокирует 1 воркер |
| Celery concurrency | Рекомендуется ≥ N групп | Где N — максимум одновременных сессий |

**Рекомендация по масштабированию:** при использовании расписаний на нескольких группах одновременно установить `CELERY_WORKER_CONCURRENCY` равным или больше максимального числа параллельных сессий. Например, для 5 групп одновременно — `concurrency=6` (5 сессий + 1 для прочих задач).

---

## 7. Текущий статус

| Компонент | Статус |
|---|---|
| Создание расписания (бот) | ✅ Работает |
| Уведомления (-1ч, -10м, -5м) | ✅ Работает |
| Запуск одной части | ✅ Работает |
| Запуск нескольких частей последовательно | ✅ Исправлено (event loop fix) |
| Пауза 120 с между частями | ✅ Работает |
| Отмена через панель (PENDING) | ✅ Работает (Celery revoke) |
| Отмена через панель (RUNNING) | ✅ Работает (DB статус, до 5 с задержки) |
| Остановка через `/stop` | ✅ Исправлено (Task 2, Баг 1) |
| Ошибка во время квиза | ✅ Исправлено (Task 2, Баг 2) |
| Конфликт с активным квизом | ✅ Исправлено (Task 2, Баг 3) |
| Stale GroupQuiz (STARTED, нет в Redis) | ✅ Автоматическая очистка |
| Статистика после каждой части | ✅ Работает |
| Финальный статус COMPLETED | ✅ Работает |
