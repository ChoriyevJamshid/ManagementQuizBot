import httpx
from django.conf import settings

URL = f'https://api.telegram.org/bot{settings.API_TOKEN}/'


def send_message(chat_id, text):
    url = URL + 'sendMessage'
    params = {
        'chat_id': chat_id,
        'text': text
    }
    response = httpx.post(url, params=params)
    if response.status_code == 200:
        print(f"Message sent to chat_id {chat_id}")
    else:
        print(f"Failed to send message to chat_id {chat_id}: {response.text}")
    return response


def set_my_commands(commands: list[dict[str, str]], scope: dict = None):
    url = URL + f"setMyCommands"
    payload = {
        'commands': commands,
        'scope': scope if scope else {'type': 'default'},
    }
    response = httpx.post(url, json=payload, timeout=15)
    return response


