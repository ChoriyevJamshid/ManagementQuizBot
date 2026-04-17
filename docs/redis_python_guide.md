# Redis + Python — практическое руководство

## Подключение

```python
import redis.asyncio as redis

# Одно соединение
client = redis.from_url("redis://localhost:6379", decode_responses=True)

# Пул соединений (для production — всегда используй пул)
client = redis.from_url(
    "redis://localhost:6379",
    decode_responses=True,   # bytes → str автоматически
    max_connections=50,
    socket_timeout=5,
)
```

> `decode_responses=True` — Redis хранит всё как bytes, эта опция декодирует в str автоматически.

---

## Базовые операции

### GET / SET

```python
await client.set("key", "value")          # сохранить
await client.set("key", "value", ex=60)   # сохранить с TTL 60 секунд

value = await client.get("key")           # получить → str или None
exists = await client.exists("key")       # → 1 (есть) или 0 (нет)
await client.delete("key")               # удалить
```

### Числа (атомарные счётчики)

```python
await client.set("counter", 0)
await client.incr("counter")             # +1  → возвращает новое значение
await client.incrby("counter", 5)        # +5
await client.decr("counter")             # -1
```

### Hash (словарь внутри ключа)

```python
# Запись
await client.hset("user:42", "name", "Jamshid")
await client.hset("user:42", mapping={"name": "Jamshid", "score": "0"})

# Чтение
name = await client.hget("user:42", "name")       # одно поле
data = await client.hgetall("user:42")             # весь словарь → dict

# Инкремент поля (атомарно)
await client.hincrby("user:42", "score", 1)        # целое число
await client.hincrbyfloat("user:42", "time", 0.5)  # float
```

### Set (множество уникальных значений)

```python
await client.sadd("players", "user1", "user2")    # добавить
await client.scard("players")                      # количество
members = await client.smembers("players")         # все элементы → set
await client.srem("players", "user1")              # удалить элемент
```

---

## Pipeline — несколько команд за 1 запрос

Используй когда нужно выполнить несколько команд сразу. Уменьшает latency в несколько раз.

```python
pipe = client.pipeline()
pipe.hset("user:42", "name", "Jamshid")
pipe.hincrby("user:42", "score", 1)
pipe.expire("user:42", 3600)
results = await pipe.execute()   # список результатов каждой команды
```

---

## SETNX — атомарный "первый выигрывает"

Главный инструмент для предотвращения дублирования при конкурентных запросах.

```python
# SET if Not eXists — вернёт True только ПЕРВОМУ вызову
result = await client.set("lock:question:poll123", "1", nx=True, ex=60)
is_first = result is not None   # True → первый, False → уже был

if is_first:
    # выполняется только один раз, даже при 100 одновременных запросах
    await save_first_answer_to_db()
```

> Используется в этом проекте для подсчёта первого ответа на каждый вопрос.

---

## TTL — время жизни ключа

```python
await client.set("key", "value", ex=3600)      # 1 час при создании
await client.expire("key", 3600)               # установить TTL на существующий ключ
ttl = await client.ttl("key")                  # оставшееся время → int (-1 если нет TTL, -2 если нет ключа)
await client.persist("key")                    # убрать TTL (сделать постоянным)
```

---

## Поиск ключей по шаблону

```python
# SCAN — безопасный поиск (не блокирует Redis)
async for key in client.scan_iter("group_quiz:42:poll:*"):
    print(key)

# Собрать список
keys = [key async for key in client.scan_iter("session:*")]
await client.delete(*keys)   # удалить все найденные
```

> Никогда не используй `KEYS *` в production — блокирует Redis на время поиска.

---

## JSON в Redis (через orjson)

Redis не знает про JSON — храни как строку.

```python
import orjson

# Сохранить
data = [{"question": "Q1", "answer": "A"}]
await client.set("questions:42", orjson.dumps(data).decode(), ex=86400)

# Загрузить
raw = await client.get("questions:42")
data = orjson.loads(raw) if raw else None
```

---

## Паттерны используемые в проекте

| Задача | Паттерн | Пример ключа |
|--------|---------|--------------|
| Первый ответ на вопрос | SETNX | `group_quiz:42:poll:abc123:is_answered` |
| Флаг активности квиза | SET/DELETE | `group_quiz:42:active` |
| Очки игрока | HINCRBY | `group_quiz:42:scores` → hash `{user_id: score}` |
| Список вопросов | SET + orjson | `group_quiz:42:questions` → JSON строка |
| Счётчик пропусков | INCR | `group_quiz:42:skip_count` |
| Поиск poll_id → quiz | SET | `poll:abc123` → quiz_id |

---

## AOF — персистентность данных

Настроено в `redis.conf`:

```
appendonly yes          # включает AOF
appendfsync everysec    # сброс на диск каждую секунду (максимум 1 сек потерь при краше)
```

Данные хранятся в Docker volume `redis_data`. При перезапуске контейнера — данные восстановятся автоматически.

---

## Быстрая шпаргалка

```
SET key value [EX seconds]    → сохранить
GET key                        → получить
DEL key [key ...]              → удалить
EXISTS key                     → проверить
EXPIRE key seconds             → установить TTL
INCR / INCRBY key [n]         → атомарный счётчик
HSET key field value           → hash: записать поле
HGET key field                 → hash: прочитать поле
HGETALL key                    → hash: весь словарь
HINCRBY key field n            → hash: инкремент
SADD key member                → set: добавить
SCARD key                      → set: размер
SET key value NX EX seconds   → SETNX: первый побеждает
```
