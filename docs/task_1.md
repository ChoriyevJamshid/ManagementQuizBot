# Задача 1: Переработка системы запланированных тестов

**Дата:** 2026-05-01

---

## Что удаляем

| Файл | Что удаляем |
|---|---|
| `bot/handlers/users/schedule_quiz.py` | Весь файл |
| `bot/states/main.py` | Класс `ScheduleQuizState` |
| `bot/utils/orm.py` | Функции `get_distinct_groups`, `create_scheduled_quiz` |
| `quiz/tasks.py` | 4 задачи: `run_scheduled_quiz`, `notify_before_quiz`, `start_scheduled_group_quiz`, `launch_scheduled_group_quiz` |
| `bot/keyboards/inline_kb.py` | Маркапы: `schedule_parts_markup`, `schedule_groups_markup`, `schedule_type_markup`, `schedule_days_markup`, `schedule_confirm_markup`; кнопка `schedule_button` из `quiz_detail_markup` |
| `bot/handlers/users/__init__.py` | Все регистрации из `schedule_quiz.*` и импорт `ScheduleQuizState` |
| `quiz/models.py` | Модель `ScheduledQuiz` (вместе с FK на `PeriodicTask`) |

---

## Новая модель

### `ScheduledSession` (`quiz/models.py`)

```python
class ScheduledSession(BaseModel):
    created_by      = ForeignKey(TelegramProfile, on_delete=CASCADE)
    group_id        = CharField(max_length=63)
    group_title     = CharField(max_length=255, blank=True)
    part_ids        = JSONField(default=list)        # [part_id, ...] — порядок важен
    scheduled_at    = DateTimeField()                # хранится в UTC
    status          = CharField(max_length=31)       # PENDING / RUNNING / COMPLETED / CANCELLED
    celery_task_ids = JSONField(default=list)        # для отмены через revoke()
```

Требуется новая миграция: добавить `ScheduledSession`, удалить `ScheduledQuiz`.

---

## Celery-задачи (новые, `quiz/tasks.py`)

| Задача | Назначение |
|---|---|
| `notify_scheduled_session(session_id, label)` | Отправляет уведомление в группу (за 1ч / 10м / 5м) |
| `start_scheduled_session(session_id)` | Запускает часть с индексом 0 |
| `continue_scheduled_session(session_id, index)` | Запускает следующую часть (после паузы 120с) |

### Логика планирования при создании расписания

При сохранении `ScheduledSession` через `apply_async(eta=...)` планируются:
- уведомление за 1 час — только если до старта **более 60 минут**
- уведомление за 10 минут — только если **более 10 минут**
- уведомление за 5 минут — только если **более 5 минут**
- старт — **всегда**

Все `task_id` сохраняются в `celery_task_ids`. При отмене — `revoke()` каждого.

### Логика выполнения нескольких частей

Если выбраны `[part1, part2]` и старт в 20:00:
- 20:00 → `start_scheduled_session` → запускает part1
- part1 завершён → `continue_scheduled_session.apply_async(countdown=120)` → запускает part2
- part2 завершён → `status = COMPLETED`

---

## FSM-состояния (`ScheduledSessionState`)

```
select_group → select_parts → select_date → select_time → confirm
```

---

## Флоу создания расписания

### Шаг 1 — Выбор группы
- Список групп из истории `GroupQuiz` (последние уникальные)
- Кнопка «Ввести вручную» → пользователь вводит `group_id` текстом

### Шаг 2 — Выбор частей квиза
- Показываются все `QuizPart` всех квизов
- Формат отображения: `Quiz Title → [from_i - to_i]`
- Мультивыбор: ✅ / ❌ по каждой части
- Кнопка «Готово ✅» внизу (активна только если выбрана хотя бы одна часть)

### Шаг 3 — Выбор даты
- 4 инлайн-кнопки: **Сегодня / Завтра / Послезавтра / +3 дня**

### Шаг 4 — Выбор времени
- Пользователь вводит текстом в формате `HH:MM`
- Валидация: корректный формат + время не в прошлом

### Шаг 5 — Подтверждение
Сводка выбранного:
```
Группа:  My Group
Части:   Quiz A → [1-50]
         Quiz B → [1-30]
Дата:    01.05.2026
Время:   20:00 (Asia/Tashkent)
```
Кнопки: **✅ Подтвердить** / **❌ Отмена**

---

## Экран списка расписаний

Показываются все сессии со статусом `PENDING` или `RUNNING`.

Каждая запись:
```
📅 My Group
   Quiz A → [1-50], Quiz B → [1-30]
   🕐 01.05.2026 в 20:00
   [❌ Отменить]
```

При нажатии «Отменить»:
1. `revoke()` для всех `celery_task_ids`
2. `status = CANCELLED`
3. Уведомление в группу об отмене

---

## Изменения в главном меню

Кнопка **«📅 Запланированные тесты»** добавляется в `main_menu_markup()`.  
Показывается **только** пользователям с ролью `ADMIN` или `MODERATOR`.

---

## Уведомления (только в группу, не в личку)

| Когда | Текст |
|---|---|
| За 1 час | «⏰ Через 1 час начнётся тест: ...» |
| За 10 минут | «⚡️ До начала теста осталось 10 минут!» |
| За 5 минут | «🔔 До начала теста осталось 5 минут!» |
| При отмене | «❌ Запланированный тест отменён.» |

---

## Затронутые файлы

| Действие | Файл |
|---|---|
| Создать | `bot/handlers/users/scheduled_sessions.py` |
| Создать | `quiz/migrations/XXXX_add_scheduled_session.py` |
| Изменить | `quiz/models.py` |
| Изменить | `quiz/tasks.py` |
| Изменить | `bot/states/main.py` |
| Изменить | `bot/utils/orm.py` |
| Изменить | `bot/keyboards/inline_kb.py` |
| Изменить | `bot/handlers/users/__init__.py` |
| Изменить | `bot/handlers/users/main.py` |
| Удалить | `bot/handlers/users/schedule_quiz.py` |

---

## Технические ограничения / решения

- **Тайм-зона**: Asia/Tashkent (UTC+5). Время хранится в UTC, отображается в локальной зоне.
- **Доступ**: только `ADMIN` и `MODERATOR`.
- **История**: завершённые и отменённые сессии не удаляются — остаются с соответствующим статусом.
- **Список**: показываем все расписания (не только свои).
- **Уведомления**: только в группу, не в личку.
