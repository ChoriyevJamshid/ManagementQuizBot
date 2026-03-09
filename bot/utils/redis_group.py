import json
import redis.asyncio as redis
from django.conf import settings

# Initialize Redis client using from environment setup
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def add_player_to_group_quiz(group_quiz_id: str, user_id: str, username: str) -> None:
    """
    Atomically adds a player to the group quiz in Redis.
    """
    key = f"group_quiz:{group_quiz_id}:players"
    
    # Check if the player already exists to avoid overwriting their stats
    exists = await redis_client.hexists(key, user_id)
    if not exists:
        player_data = {
            'corrects': 0,
            'wrongs': 0,
            'spent_time': 0.0,
            'username': username
        }
        await redis_client.hset(key, user_id, json.dumps(player_data))

async def increment_player_score(
    group_quiz_id: str, 
    user_id: str, 
    is_correct: bool, 
    spent_time: float,
    username: str = None
) -> None:
    """
    Increments the player's score and spent time.
    """
    key = f"group_quiz:{group_quiz_id}:players"
    
    # Retrieve current data
    player_data_str = await redis_client.hget(key, user_id)
    
    if player_data_str:
        player_data = json.loads(player_data_str)
    else:
        player_data = {
            'corrects': 0,
            'wrongs': 0,
            'spent_time': 0.0,
            'username': username or "Unknown"
        }

    if is_correct:
        player_data['corrects'] += 1
    else:
        player_data['wrongs'] += 1
        
    player_data['spent_time'] += spent_time
    
    # Save it back atomically for this user
    await redis_client.hset(key, user_id, json.dumps(player_data))

async def get_all_players_data(group_quiz_id: str) -> dict:
    """
    Retrieves all players' scores when the quiz ends.
    Returns dict like { 'user_id_123': {'corrects': 5, ...}, ... }
    """
    key = f"group_quiz:{group_quiz_id}:players"
    raw_data = await redis_client.hgetall(key)
    
    parsed_data = {}
    for user_id, json_str in raw_data.items():
        parsed_data[user_id] = json.loads(json_str)
        
    return parsed_data

async def get_players_count(group_quiz_id: str) -> int:
    """
    Returns the total number of players who clicked 'Ready'.
    """
    key = f"group_quiz:{group_quiz_id}:players"
    return await redis_client.hlen(key)

async def delete_group_quiz_data(group_quiz_id: str) -> None:
    """
    Cleans up Redis memory after test is finished.
    """
    key_players = f"group_quiz:{group_quiz_id}:players"
    key_current = f"group_quiz:{group_quiz_id}:current"
    await redis_client.delete(key_players, key_current)


async def set_group_question_data(group_quiz_id: str, correct_option_id: int, start_time: float) -> None:
    """
    Saves the temporary state (current correct option & start clock) 
    into memory for fast atomic assessment by poll responders. 
    """
    key = f"group_quiz:{group_quiz_id}:current"
    
    mapping = {
        "correct_option_id": str(correct_option_id),
        "start_time": str(start_time)
    }
    
    await redis_client.hset(key, mapping=mapping)

async def get_group_question_data(group_quiz_id: str) -> dict:
    """
    Reads back the current question data.
    """
    key = f"group_quiz:{group_quiz_id}:current"
    data = await redis_client.hgetall(key)
    if not data:
        return {"correct_option_id": 10, "start_time": 0.0}

    return {
        "correct_option_id": int(data.get("correct_option_id", "10")),
        "start_time": float(data.get("start_time", "0.0"))
    }
