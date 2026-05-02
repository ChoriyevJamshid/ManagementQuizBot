# Задача 2: Исправление багов в системе запланированных тестов

**Дата:** 2026-05-02

---

## Описание проблем

После реализации Task 1 были обнаружены три критических бага, при которых `ScheduledSession`
зависает в статусе `RUNNING` навсегда, и одно замечание по качеству кода.

---

## Баг 1 — `/stop` в группе ломает сессию

**Файл:** `bot/handlers/groups/testing.py`, строки 87–121  
**Файл:** `bot/handlers/groups/main.py`, `stop_handler`

### Что происходит

1. Идёт запланированная сессия, квиз запущен в группе.
2. Кто-то вводит `/stop`.
3. `stop_handler` вызывает `redis_group.set_quiz_inactive()`.
4. `run_group_quiz_loop` на следующей итерации видит `is_quiz_active() == False` и делает `return`.
5. Блок с расписанием следующей части (строки 109–121) **не достигается**.
6. `send_statistics()` вызывается напрямую из `stop_handler`, но о `ScheduledSession` он ничего не знает.
7. **Итог**: `ScheduledSession` остаётся в статусе `RUNNING` навсегда.

### Решение

Добавить в `run_group_quiz_loop` обработку досрочного выхода:

```
for index in range(start_index, total_questions):
    if not is_quiz_active:
        # досрочный выход — сессия прервана вручную
        if session_id is not None:
            session.status = CANCELLED
        return   # send_statistics вызовет stop_handler
    ...
```

Конкретно: перед каждым `return` внутри цикла проверять `session_id`.  
Если `session_id` задан — обновлять `ScheduledSession.status = CANCELLED` и  
отправлять уведомление об отмене в группу.

---

## Баг 2 — Исключение в `_launch_session_part` → сессия зависает

**Файл:** `quiz/tasks.py`, строки 300–311

### Что происходит

Если `asyncio.run(_run())` падает с исключением:
- `GroupQuiz` корректно отменяется (строки 307–311).
- Но `ScheduledSession.status` **не обновляется** — остаётся `RUNNING`.
- Следующие части никогда не запустятся.

### Решение

В блоке `except` в `_launch_session_part` дополнительно обновлять статус сессии:

```python
except Exception:
    logger.exception("Session %d part %d failed", session_id, part_index)
    GQ.objects.filter(...).update(status=CANCELED)
    # Новое: помечаем сессию как CANCELLED
    ScheduledSession.objects.filter(pk=session_id).update(status=SessionStatus.CANCELLED)
```

---

## Баг 3 — Существующий активный квиз в группе → сессия зависает

**Файл:** `quiz/tasks.py`, строки 187–228

### Что происходит

Если в группе уже идёт другой тест (status=`INIT` или `PAUSED`) и `_launch_session_part`
делает `return` (строки 222–228):
- Текущая часть пропускается.
- Следующая часть не планируется.
- Сессия остаётся в `RUNNING` навсегда.

Аналогично — если `STARTED` + Redis активен (строки 214–219): тот же `return` без
обновления сессии.

### Решение

При любом `return` в блоке `if existing:` — пометить сессию как `CANCELLED` и
отправить уведомление в группу о том, что тест не удалось запустить (в группе уже
идёт другой квиз).

```python
if existing:
    if ...:  # все ветки, которые раньше делали просто return
        logger.warning("Session %d part %d: blocked by existing quiz", ...)
        if session_id:
            ScheduledSession.objects.filter(pk=session_id).update(status=SessionStatus.CANCELLED)
            send_text(chat_id=..., text=get_text_sync('ss_cancelled_due_to_active_quiz'))
        return
```

Добавить новый текст `ss_cancelled_due_to_active_quiz` в `languages/uz.json`.

---

## Замечание — тип возврата `cancel_scheduled_session`

**Файл:** `bot/utils/orm.py`, строка 287

Аннотация `-> bool` не соответствует реальному возвращаемому типу `ScheduledSession | None`.  
Исправить аннотацию на `-> 'quiz_models.ScheduledSession | None'`.

---

## Замечание — `__import__` антипаттерн

**Файл:** `bot/utils/orm.py`, строки 256–264

`__import__('datetime').timedelta` заменить на нормальный импорт `timedelta` в начале вложенной функции `_inner`.

---

## Затронутые файлы

| Файл | Изменение |
|---|---|
| `quiz/tasks.py` | Баг 2: обновлять `session.status=CANCELLED` в `except`; Баг 3: обновлять статус при блокировке существующим квизом |
| `bot/handlers/groups/testing.py` | Баг 1: при досрочном выходе из `run_group_quiz_loop` помечать сессию CANCELLED |
| `bot/utils/orm.py` | Замечание: исправить аннотацию; убрать `__import__` антипаттерн |
| `languages/uz.json` | Добавить ключ `ss_cancelled_due_to_active_quiz` |

---

## Технические ограничения / решения

- **Статус при ручной остановке**: `CANCELLED` (не `COMPLETED`), так как тест не завершён штатно.
- **Статус при ошибке**: `CANCELLED` — безопаснее, чем оставлять `RUNNING`.
- **Статус при блокировке**: `CANCELLED` — администратор должен создать новое расписание.
- **Уведомление в группу**: при любой нештатной отмене (баги 1, 3) отправляется сообщение `ss_cancelled_group_notify`.
- **Обратная совместимость**: все изменения только добавляют обновления статуса — не меняют основной флоу.
