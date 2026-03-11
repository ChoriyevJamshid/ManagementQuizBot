import redis.asyncio as redis
from django.conf import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


# -----------------------------
# PLAYERS
# -----------------------------

async def add_player_to_group_quiz(group_quiz_id: str, user_id: str, username: str) -> None:
    """
    Adds player to quiz if not exists.
    """
    players_key = f"group_quiz:{group_quiz_id}:players"
    usernames_key = f"group_quiz:{group_quiz_id}:usernames"

    await redis_client.sadd(players_key, user_id)
    await redis_client.hset(usernames_key, user_id, username)


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
    Atomically increments player statistics.
    """

    scores_key = f"group_quiz:{group_quiz_id}:scores"
    wrongs_key = f"group_quiz:{group_quiz_id}:wrongs"
    times_key = f"group_quiz:{group_quiz_id}:times"
    usernames_key = f"group_quiz:{group_quiz_id}:usernames"

    if username:
        await redis_client.hset(usernames_key, user_id, username)

    if is_correct:
        await redis_client.hincrby(scores_key, user_id, 1)
    else:
        await redis_client.hincrby(wrongs_key, user_id, 1)

    await redis_client.hincrbyfloat(times_key, user_id, spent_time)


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

    players = await redis_client.smembers(players_key)

    scores = await redis_client.hgetall(scores_key)
    wrongs = await redis_client.hgetall(wrongs_key)
    times = await redis_client.hgetall(times_key)
    usernames = await redis_client.hgetall(usernames_key)

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

    await redis_client.hset(
        key,
        mapping={
            "correct_option_id": str(correct_option_id),
            "start_time": str(start_time)
        }
    )


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
    ]

    await redis_client.delete(*keys)