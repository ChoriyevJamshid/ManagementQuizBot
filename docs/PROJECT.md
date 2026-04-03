# ManagementQuizBot — Project State

## What is this

Django + Aiogram 3 quiz bot. Users upload a file (Word/Excel/Txt), the bot parses questions and creates a quiz. Quizzes can be taken privately (individual) or in a group chat (multiplayer with polls). Django admin panel for management.

**Stack:** Django 5 · Aiogram 3 · PostgreSQL · Redis · Celery · Gunicorn + Uvicorn workers

---

## Architecture

```
Telegram → POST /bot/<md5(token)>/ → Django async view (common/views.py)
                                        ↓
                                  webhook.process_update()
                                        ↓
                               Aiogram Dispatcher (FSM in Redis db=2)
                                        ↓
                    ┌───────────────────┼───────────────────┐
               admin/               users/              groups/
         (admin menu)     (create, test, quizzes)   (group quiz loop)
                                        ↓
                              Django ORM (PostgreSQL)
                              Redis (group quiz scores, db=0)
```

**FSM storage:** Redis db=2 (aiogram states)  
**Group quiz state:** Redis db=0 (scores, players, current question — keys: `group_quiz:{id}:{players|scores|wrongs|times|usernames|current}`)  
**Async ORM:** mix of `.afirst()` / `.acreate()` and sync calls (some still sync — known issue)

---

## Bot flow

### Quiz creation (5 steps)
```
create_quiz_handler
  → get title         (CreateQuizState.title)
  → upload file       (CreateQuizState.file)   ← parsed in asyncio.to_thread
  → questions/part    (CreateQuizState.check)  ← 20/25/30/35
  → timer             (CreateQuizState.timer)
  → confirm & save    (CreateQuizState.save)   ← sync_to_async + bulk_create
```

### Individual quiz
```
/quiz_LINK or inline share → testing_link_handler
  → testing_start_pressed_handler
  → testing_ready_pressed_handler   ← creates UserQuiz, starts poll loop
  → testing_poll_answer_handler     ← answer → next question (asyncio.create_task for skip timer)
  → save_user_quiz (FINISHED / CANCELED)
```

### Group quiz (detailed)
```
/start LINK (in group)
    → start_handler
        → get_quiz_part(link) from DB
        → get_group_quiz(group_id) from DB
        → if no active quiz → create_group_quiz (status=INIT)
        → if INIT → reset part/message_id, reuse existing record
        → if STARTED → reply "already running"
        → send_quiz_ready_message (inline "Tayyorman" button)
              ↓
    User presses "Tayyorman" → get_ready_callback_handler
        → redis: sadd players, hset usernames
        → update message with player count
        → if players_count >= 2:
            aupdate(status=INIT→STARTED) — atomic, returns rows_updated
            if rows_updated > 0:   ← ensures only ONE task is created
                asyncio.create_task(start_quiz_after_delay, 10s)
        → Celery: get_group_invite_link.delay(pk) if no invite_link
              ↓
    After 10s → start_group_testing
        → delete_quiz_reply_markup
        → animate_texts (7 steps × 1s = 7s total)
        → generate_user_quiz_data(part) ← SYNC ORM, shuffles questions
        → run_group_quiz_loop(question_data, start_index=0)
              ↓
    run_group_quiz_loop (main question loop)
        for index in range(len(question_data)):
            arefresh_from_db()           ← DB hit every iteration
            if index>0 and not is_answered → skips += 1
            reset is_answered = False
            if skips >= 2 → handle_no_answers (send pause msg, stop loop)
            send_question (text + poll, save poll_id to DB + Redis poll:{id}=quiz_pk)
            asyncio.sleep(timer + 2)
        send_statistics()
              ↓
    Parallel: testing_group_poll_answer_handler (every poll_answer event)
        → redis: get poll:{poll_id} → quiz_id
        → if not found → raise SkipHandler (not a group quiz poll)
        → DB: update_group_quiz_is_answer (atomic: is_answered=True, answers+=1)
        → redis: increment_player_score (corrects/wrongs + spent_time)
              ↓
    send_statistics (groups/statistics.py)
        → get_group_quiz from DB
        → redis: get_all_players_data → dict {user_id: {corrects, wrongs, spent_time, username}}
        → sort by (-corrects, spent_time)
        → Celery: group_quiz_create_file.delay → Excel → saved to GroupQuiz.file
        → send leaderboard text to group (top 50)
        → DB: save GroupQuiz.data['players'], status=FINISHED, participant_count
        → redis: delete_group_quiz_data (cleanup all keys)
              ↓
    User requests Excel → send_excel_to_user_callback (handle.py)
        → get_group_quiz_for_excel by quiz_id
        → check user is registered in bot
        → if file ready → send_document to user's private chat
        → if not ready → re-trigger Celery task
```

---

## Models

| Model | Purpose |
|---|---|
| `TelegramProfile` | Telegram user (chat_id, role, is_registered) |
| `Data` | Singleton config (bot username, file_types, channel_id) |
| `Quiz` | Quiz definition (owner, title, timer, quantity) |
| `QuizPart` | Part of a quiz (link, from_i, to_i, quantity) |
| `Question` | Question text |
| `Option` | Answer option (is_correct flag) |
| `UserQuiz` | Individual attempt (corrects, wrongs, skips, times, data JSON) |
| `GroupQuiz` | Group session (group_id, poll_id, index, answers, skips, is_answered, file, data JSON) |

---

## Updates made (session 1 — initial fixes)

### Removed
- `bot/handlers/users/categories.py` — categories feature removed
- `bot/handlers/users/support.py` — support feature removed
- `SupportState`, `MainState.categories` — removed from states
- All category/support ORM queries, keyboards, router registrations
- `fastapi`, `starlette` — removed from requirements.txt (uvicorn kept, used as gunicorn worker)
- Admin bot panel simplified to users count only

### Fixed (bugs)
- **`registered.py`** — critical: `user.role not in (ADMIN, MODERATOR): return False` blocked ALL regular users → webhook worked (200 OK) but bot never responded. Fixed: filter now only checks `is_registered`.
- **`settings.py`** — `REDIS_URL` formula was `f'{REDIS_HOST}://{REDIS_HOST}:...'` → generated `localhost://localhost:6379/0` (invalid). Fixed to `f'redis://{REDIS_HOST}:...'`

### Improved — `create_quizzes.py`
- File parsers moved to sync functions, called via `asyncio.to_thread` (no longer blocks event loop)
- DB write wrapped in `sync_to_async(_create_quiz_sync)` with `transaction.atomic()`
- `bulk_create` for Questions per part (was N individual creates)
- Single `bulk_create` for all Options per part
- Link uniqueness via `.exists()` check instead of catching `IntegrityError`
- "⏳ Processing..." message shown while file is parsed
- "💾 Saving..." message shown while DB write runs
- Confirmation now shows parts count (`__parts`)
- Intro message shows all 4 steps at the start

### Improved — `webhook.py`
- `AiohttpSession` timeout added (`total=30s, connect=10s`)
- Redis pool `max_connections` increased `10 → 50`
- Redis `socket_timeout=5s` added
- `dp.storage.close()` added to shutdown
- Code split into `_build_bot()` / `_build_storage()` helpers

---

## Updates made (session 2 — group testing performance rewrite)

Goal: fix all critical bugs, make group quiz work fast with 50+ participants across multiple simultaneous groups.

### `bot/utils/redis_group.py` — full rewrite

**New Redis key layout (all keys now have TTL=86400s / 24h):**
```
group_quiz:{id}:players      SET  — player user_ids
group_quiz:{id}:usernames    HASH — user_id → display name
group_quiz:{id}:scores       HASH — user_id → correct count
group_quiz:{id}:wrongs       HASH — user_id → wrong count
group_quiz:{id}:times        HASH — user_id → total spent_time (float)
group_quiz:{id}:current      HASH — correct_option_id + start_time
group_quiz:{id}:questions    STRING — JSON list of shuffled question_data
group_quiz:{id}:is_answered  STRING — SET NX flag; exists = someone answered
group_quiz:{id}:skip_count   STRING — consecutive no-answer count
group_quiz:{id}:active       STRING — exists = quiz is running
```

**New functions:**
- `store_questions_data(quiz_id, questions)` — serializes question list to Redis
- `get_questions_data(quiz_id) -> list | None` — restores from Redis (no re-shuffle)
- `set_question_answered(quiz_id) -> bool` — `SET NX`; True only for first caller
- `is_question_answered(quiz_id) -> bool`
- `reset_question_answered(quiz_id)` — called before each new question
- `increment_skips(quiz_id) -> int` / `get_skips` / `reset_skips`
- `set_quiz_active` / `is_quiz_active` / `set_quiz_inactive`

**Performance:** `add_player_to_group_quiz` and `increment_player_score` now use `pipeline()` — batch multiple Redis commands in one round-trip.

**Cleanup:** `delete_group_quiz_data` now deletes all 10 keys including new ones; removed `print()`.

---

### `bot/utils/functions.py`
- Added module-level `_text_cache: dict | None = None` — language file loaded once into memory, all subsequent `get_text()` / `get_texts()` calls served from cache (no file I/O)
- Removed `print()` from `get_text_sync`

---

### `bot/utils/orm.py`
- Added `get_group_quiz_no_prefetch(group_id)` — lightweight version without `prefetch_related(questions/options)`, for use in `send_statistics` and `stop_handler` where question data is not needed
- `update_group_quiz_is_answer` → renamed `update_group_quiz_answers` — removed `is_answered=True` field (now tracked in Redis via SETNX), now only increments `answers` counter; called at most once per question (first-answer-wins)

---

### `bot/handlers/groups/testing.py` — rewritten

**Bug #1 fixed (re-shuffle on continue):**
- `start_group_testing` generates `question_data` once, immediately stores in Redis via `store_questions_data`
- `group_quiz_continue_callback` restores from Redis via `get_questions_data` instead of calling `generate_user_quiz_data` again
- If Redis key expired (very long pause), falls back to regenerate + re-store

**Bug #9 fixed (useless FSMContext):**
- `FSMContext` removed from `start_group_testing` and `group_quiz_continue_callback` — group quiz is entirely task-based; FSM state for one user is irrelevant

**Performance — `run_group_quiz_loop`:**
- Removed `arefresh_from_db()` call per iteration (was: 1 DB read + up to 2 DB writes per question)
- `is_answered` / `skips` now read/written via Redis (`is_question_answered`, `increment_skips`, `reset_skips`)
- Added `is_quiz_active` check at loop start → detects external stop (via `stop_handler`)
- DB writes inside loop now only: `group_quiz.asave(poll_id, index)` in `send_question`

**Performance — `testing_group_poll_answer_handler`:**
- `set_question_answered` (SETNX) gates the DB write: only the FIRST of 50+ concurrent poll answers calls `update_group_quiz_answers`. All others skip the DB write entirely
- `voter_chat` handled (anonymous channel votes)
- All `print()` removed

---

### `bot/handlers/groups/main.py` — rewritten

**Bug #2 fixed (message_id + 1 hack):**
- `start_handler` now calls `send_quiz_ready_message` first, then uses the **actual returned `message.message_id`** when creating/updating `GroupQuiz` record
- No more off-by-one risk if another message arrives between /start and bot reply

**FSMContext removed:**
- `get_ready_callback_handler` no longer declares `state: FSMContext` (not needed)
- `start_quiz_after_delay` no longer takes `state` argument

**Bug #7 partial fix:**
- `stop_handler` now uses `get_group_quiz_no_prefetch` (questions not needed)
- `stop_handler` now calls `redis_group.set_quiz_inactive` before `send_statistics` to immediately signal the running loop to stop

**Cleanup:** all `print()` statements removed

---

### `bot/handlers/groups/common.py`
**Animation reduced from 7s → ~3s (Bug #6):**
- Sequence changed from 7 steps (5-4-3-2-1-GO + header) × 1s to 4 steps (3-2-1-GO) × 0.75s
- Combined with 10s wait: total lag before first question = 10s + 3s = **13s** (was 17s)

---

### `bot/handlers/groups/statistics.py` — TODO (not yet applied, interrupted)
- Remove ~80 lines of commented-out dead code (old version)
- Remove all `print()` statements
- Switch to `get_group_quiz_no_prefetch` (questions not needed)
- Add `logging.getLogger` for exception handling

### `bot/handlers/groups/handle.py` — TODO (not yet applied)
- Remove ~45 lines of commented-out dead code (old version)

---

## Group quiz Redis state — new flow diagram (session 2)

```
start_handler
  → send_quiz_ready_message → returns msg → save msg.message_id (Bug #2 fixed)
  → create_group_quiz(message_id=actual_id)

get_ready_callback_handler (no FSMContext)
  → redis: add_player (pipeline, TTL set)
  → if players >= 2: atomic DB update INIT→STARTED
    → asyncio.create_task(start_quiz_after_delay(group_quiz, bot))   # no state

start_quiz_after_delay → sleep(10) → start_group_testing(group_quiz, bot)

start_group_testing
  → delete_quiz_reply_markup
  → animate_texts (3s total)
  → generate_user_quiz_data(part)           # in-memory shuffle from prefetched data
  → redis: store_questions_data(quiz_id)    # persist order, fixes Bug #1
  → redis: set_quiz_active(quiz_id)
  → run_group_quiz_loop(question_data, start_index=0)

run_group_quiz_loop
  for each question:
    redis: is_quiz_active?  → False → return  (stop_handler signaled)
    if index>0:
      redis: is_question_answered? → No → increment_skips
        skips>=2 → handle_no_answers (send pause msg, reset skips, exit loop)
      redis: reset_question_answered
    send_question (DB: save poll_id + index; Redis: current + poll:{id}=quiz_pk)
    asyncio.sleep(timer + 2)
  redis: set_quiz_inactive
  send_statistics()

testing_group_poll_answer_handler (fires for EVERY poll answer, up to 50+ concurrent)
  redis: get poll:{id} → quiz_id
  redis: set_question_answered (SETNX) → True only for first answer
    → DB: update_group_quiz_answers (answers += 1)   # called once per question
  redis: get_group_question_data → correct_option_id, start_time
  redis: increment_player_score (pipeline)

stop_handler
  DB: get_group_quiz_no_prefetch
  redis: set_quiz_inactive → loop sees this on next iteration
  send_statistics(is_cancelled=True)

group_quiz_continue_callback (no FSMContext)
  redis: get_questions_data → restored list (Bug #1 fixed)
  if None: regenerate + store
  redis: reset_skips, set_quiz_active
  asyncio.create_task(run_group_quiz_loop(start_index=index))

send_statistics (statistics.py)
  DB: get_group_quiz_no_prefetch   (TODO: not yet switched)
  redis: get_all_players_data (pipeline: 5 commands in 1 round-trip)
  sort players, build leaderboard
  Celery: group_quiz_create_file.delay
  send message to group
  DB: save status=FINISHED/CANCELED, data['players'], participant_count
  redis: delete_group_quiz_data (all 10 keys)
```

---

## Known issues — remaining (after session 2)

| # | File | Issue | Status |
|---|---|---|---|
| 1 | `groups/statistics.py` | Dead code (~80 lines commented), print() statements, uses heavy `get_group_quiz` | TODO |
| 2 | `groups/handle.py` | Dead code (~45 lines commented) | TODO |
| 3 | `groups/statistics.py` | `skips` penalty formula: `quantity - corrects - wrongs` is wrong for mid-game joiners | TODO |
| 4 | `groups/main.py` | No "quiz starts in 10 seconds" UX message when 2nd player joins | TODO |
| 5 | `bot/utils/orm.py` | Many `async def` functions still call sync ORM (`.first()`, `.create()`) — `DJANGO_ALLOW_ASYNC_UNSAFE=true` masks this | Backlog |
| 6 | `users/testing.py` | `user_quiz.save()` still sync | Backlog |
| 7 | `middlewares/logging.py` | `event.from_user` can be None for anon group messages | Backlog |

## Known issues — other (not yet fixed)

| File | Issue |
|---|---|
| `bot/utils/orm.py` | Most `async def` functions call sync ORM (`.first()`, `.create()`, `.count()`) — blocks event loop. Works only because `DJANGO_ALLOW_ASYNC_UNSAFE=true`. Needs `.afirst()`, `.acreate()`, `.acount()` etc. |
| `bot/utils/functions.py` | `get_text()` / `get_texts()` open and parse `uz.json` from disk on every call — should load once into memory at startup |
| `bot/utils/functions.py` | `testing_animation()` uses `time.sleep()` (sync) inside async — blocks event loop. Should be `asyncio.sleep()` |
| `bot/handlers/users/testing.py` | `user_quiz.save()` calls are sync — should be `await user_quiz.asave()` |
| `bot/middlewares/logging.py` | `event.from_user` can be `None` for anonymous group messages — raises `AttributeError` |

---

## Running locally

```bash
# Set webhook (needs WEB_DOMAIN in .env pointing to ngrok URL)
python manage.py setwebhook

# Run in polling mode (no webhook needed)
python manage.py runbot

# Docker (production)
make start
```

**Ports:** Django on `WEB_PORT` (from .env) · ngrok forwards to it

---

## File structure (key files)

```
bot/
  webhook.py              ← WebhookService (production entry point)
  app.py                  ← polling mode (dev)
  handlers/
    admin/main.py         ← /admin command, user count
    users/
      main.py             ← start, cancel, registration
      create_quizzes.py   ← quiz creation flow (5 steps)
      testing.py          ← individual quiz poll loop
      quizzes.py          ← user's quiz list, timer/privacy edit
      instruction.py      ← file format guides
      inline_mode.py      ← inline share
    groups/
      main.py             ← /start LINK, ready button, /stop
      testing.py          ← run_group_quiz_loop, poll answer handler
      statistics.py       ← send_statistics, leaderboard, Celery trigger
      handle.py           ← send Excel to user
      common.py           ← animate_texts, delete_markup, check_user_role
  filters/
    registered.py         ← registration gate (checks is_registered only)
    main.py               ← CancelFilter, ChatTypeFilter
  middlewares/
    logging.py            ← logs handler name + execution time
    checking.py           ← (disabled) admin-only middleware
  utils/
    orm.py                ← all DB queries
    redis_group.py        ← Redis ops for group quiz state
    functions.py          ← get_text/get_texts, file parsers, generate_user_quiz_data
    methods.py            ← raw HTTP calls to Telegram API (used in Celery tasks)
common/
  views.py                ← async Django view receiving webhook POST
  models.py               ← TelegramProfile, Data (singleton)
quiz/
  models.py               ← Quiz, QuizPart, Question, Option, UserQuiz, GroupQuiz
  tasks.py                ← Celery: get_group_invite_link, group_quiz_create_file, remove_quiz_files
src/
  settings.py             ← Django config, WEBHOOK_PATH=bot/md5(token), REDIS_URL
languages/
  uz.json                 ← all bot UI texts (Uzbek)
docs/
  PROJECT.md              ← this file
```
