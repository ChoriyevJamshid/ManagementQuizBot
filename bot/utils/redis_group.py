import orjson
import redis.asyncio as redis
from django.conf import settings

# Explicit pool: 50+ players × multiple groups → need headroom for concurrent commands.
# Each active group quiz can fire 50+ poll_answer events simultaneously.
redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=100,
    socket_timeout=5,
    socket_connect_timeout=5,
)

_QUIZ_TTL = 86400  # 24 hours


# -----------------------------
# PLAYERS
# -----------------------------

async def add_player_to_group_quiz(group_quiz_id: str, user_id: str, username: str) -> None:
    """
    Adds player to quiz if not exists.
    """
    players_key = f"group_quiz:{group_quiz_id}:players"
    usernames_key = f"group_quiz:{group_quiz_id}:usernames"

    pipe = redis_client.pipeline()
    pipe.sadd(players_key, user_id)
    pipe.hset(usernames_key, user_id, username)
    pipe.expire(players_key, _QUIZ_TTL)
    pipe.expire(usernames_key, _QUIZ_TTL)
    await pipe.execute()


async def get_players_count(group_quiz_id: str) -> int:
    """
    Returns players count.
    """
    players_key = f"group_quiz:{group_quiz_id}:players"
    return await redis_client.scard(players_key)


# -----------------------------
# SCORING
# -----------------------------

async def increment_player_score(
    group_quiz_id: str,
    user_id: str,
    is_correct: bool,
    spent_time: float,
    username: str = None
) -> None:
    """
    Atomically increments player statistics using a pipeline.
    """

    players_key = f"group_quiz:{group_quiz_id}:players"
    scores_key = f"group_quiz:{group_quiz_id}:scores"
    wrongs_key = f"group_quiz:{group_quiz_id}:wrongs"
    times_key = f"group_quiz:{group_quiz_id}:times"
    usernames_key = f"group_quiz:{group_quiz_id}:usernames"

    pipe = redis_client.pipeline()

    pipe.sadd(players_key, user_id)
    pipe.expire(players_key, _QUIZ_TTL)

    if username:
        pipe.hset(usernames_key, user_id, username)
        pipe.expire(usernames_key, _QUIZ_TTL)

    if is_correct:
        pipe.hincrby(scores_key, user_id, 1)
    else:
        pipe.hincrby(wrongs_key, user_id, 1)

    pipe.hincrbyfloat(times_key, user_id, spent_time)
    pipe.expire(scores_key, _QUIZ_TTL)
    pipe.expire(wrongs_key, _QUIZ_TTL)
    pipe.expire(times_key, _QUIZ_TTL)

    await pipe.execute()


# -----------------------------
# GET ALL PLAYERS DATA
# -----------------------------

async def get_all_players_data(group_quiz_id: str) -> dict:
    """
    Builds players statistics dict.
    """

    scores_key = f"group_quiz:{group_quiz_id}:scores"
    wrongs_key = f"group_quiz:{group_quiz_id}:wrongs"
    times_key = f"group_quiz:{group_quiz_id}:times"
    usernames_key = f"group_quiz:{group_quiz_id}:usernames"
    players_key = f"group_quiz:{group_quiz_id}:players"

    pipe = redis_client.pipeline()
    pipe.smembers(players_key)
    pipe.hgetall(scores_key)
    pipe.hgetall(wrongs_key)
    pipe.hgetall(times_key)
    pipe.hgetall(usernames_key)
    players, scores, wrongs, times, usernames = await pipe.execute()

    result = {}
    for user_id in players:
        result[user_id] = {
            "corrects": int(scores.get(user_id, 0)),
            "wrongs": int(wrongs.get(user_id, 0)),
            "spent_time": float(times.get(user_id, 0.0)),
            "username": usernames.get(user_id, "Unknown"),
        }

    return result


# -----------------------------
# QUESTION STATE
# -----------------------------

async def set_group_question_data(group_quiz_id: str, correct_option_id: int, start_time: float) -> None:
    """
    Saves question state.
    """

    key = f"group_quiz:{group_quiz_id}:current"

    pipe = redis_client.pipeline()
    pipe.hset(key, mapping={
        "correct_option_id": str(correct_option_id),
        "start_time": str(start_time)
    })
    pipe.expire(key, _QUIZ_TTL)
    await pipe.execute()


async def get_group_question_data(group_quiz_id: str) -> dict:
    """
    Reads question state.
    """

    key = f"group_quiz:{group_quiz_id}:current"
    data = await redis_client.hgetall(key)

    if not data:
        return {"correct_option_id": 10, "start_time": 0.0}

    return {
        "correct_option_id": int(data.get("correct_option_id", "10")),
        "start_time": float(data.get("start_time", "0.0")),
    }


# -----------------------------
# QUESTIONS DATA (fixes re-shuffle on continue)
# -----------------------------

async def store_questions_data(group_quiz_id: str, questions: list) -> None:
    """
    Serializes and stores full question list in Redis.
    Prevents re-shuffling on quiz continue.
    """
    key = f"group_quiz:{group_quiz_id}:questions"
    await redis_client.set(key, orjson.dumps(questions).decode(), ex=_QUIZ_TTL)


async def get_questions_data(group_quiz_id: str) -> list | None:
    """
    Restores question list from Redis.
    Returns None if key is missing.
    """
    key = f"group_quiz:{group_quiz_id}:questions"
    raw = await redis_client.get(key)
    if not raw:
        return None
    return orjson.loads(raw)


# -----------------------------
# IS_ANSWERED FLAG (atomic, per-question)
# -----------------------------

async def set_question_answered(group_quiz_id: str) -> bool:
    """
    Atomically marks the current question as answered.
    Returns True only for the FIRST caller (via SET NX).
    Subsequent callers get False — no duplicate DB writes.
    """
    key = f"group_quiz:{group_quiz_id}:is_answered"
    result = await redis_client.set(key, "1", nx=True, ex=600)
    return result is not None


async def is_question_answered(group_quiz_id: str) -> bool:
    key = f"group_quiz:{group_quiz_id}:is_answered"
    return await redis_client.exists(key) == 1


async def reset_question_answered(group_quiz_id: str) -> None:
    key = f"group_quiz:{group_quiz_id}:is_answered"
    await redis_client.delete(key)


# -----------------------------
# SKIPS COUNTER
# -----------------------------

async def increment_skips(group_quiz_id: str) -> int:
    key = f"group_quiz:{group_quiz_id}:skip_count"
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, _QUIZ_TTL)
    results = await pipe.execute()
    return int(results[0])


async def get_skips(group_quiz_id: str) -> int:
    key = f"group_quiz:{group_quiz_id}:skip_count"
    val = await redis_client.get(key)
    return int(val) if val else 0


async def reset_skips(group_quiz_id: str) -> None:
    key = f"group_quiz:{group_quiz_id}:skip_count"
    await redis_client.delete(key)


# -----------------------------
# ACTIVE FLAG (detect external stop)
# -----------------------------

async def set_quiz_active(group_quiz_id: str) -> None:
    key = f"group_quiz:{group_quiz_id}:active"
    await redis_client.set(key, "1", ex=_QUIZ_TTL)


async def is_quiz_active(group_quiz_id: str) -> bool:
    key = f"group_quiz:{group_quiz_id}:active"
    return await redis_client.exists(key) == 1


async def set_quiz_inactive(group_quiz_id: str) -> None:
    key = f"group_quiz:{group_quiz_id}:active"
    await redis_client.delete(key)


# -----------------------------
# CLEANUP
# -----------------------------

async def delete_group_quiz_data(group_quiz_id: str) -> None:
    """
    Deletes all quiz related redis keys.
    """

    keys = [
        f"group_quiz:{group_quiz_id}:players",
        f"group_quiz:{group_quiz_id}:scores",
        f"group_quiz:{group_quiz_id}:wrongs",
        f"group_quiz:{group_quiz_id}:times",
        f"group_quiz:{group_quiz_id}:usernames",
        f"group_quiz:{group_quiz_id}:current",
        f"group_quiz:{group_quiz_id}:questions",
        f"group_quiz:{group_quiz_id}:is_answered",
        f"group_quiz:{group_quiz_id}:skip_count",
        f"group_quiz:{group_quiz_id}:active",
    ]

    await redis_client.delete(*keys)