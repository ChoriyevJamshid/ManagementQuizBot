import json
import logging
import mimetypes

import httpx

from src.settings import API_TOKEN

URL = f'https://api.telegram.org/bot{API_TOKEN}/'


def send_text(
        chat_id: int | str,
        text: str,
        parse_mode: str = 'HTML',
        reply_markup: dict = None,
):
    url = URL + 'sendMessage'
    params = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
    }
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)

    response = httpx.post(url, params=params, timeout=15)
    return response


def send_multi_file_by_file_id(
        chat_id: int,
        file_type: str,
        file_ids: list[str],
        caption: str = None,
):
    url = URL + f"sendMediaGroup"

    medias = []
    for file_id in file_ids:
        medias.append({
            'type': file_type,
            'media': file_id
        })

    if caption:
        medias[-1]['caption'] = caption
        medias[-1]['parse_mode'] = 'HTML'

    payload = {
        'chat_id': chat_id,
        'media': medias,
    }

    timeout = httpx.Timeout(connect=10.0, read=30.0, write=60.0, pool=10.0)
    response = httpx.post(url, json=payload, timeout=timeout)
    return response


def send_file(
        chat_id: int,
        file_type: str,  # e.g. "photo", "document"
        file_path: str = None,
        file_id: str = None,
        caption: str = None,
        reply_markup: dict = None,
):
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=60.0, pool=10.0)
    url = URL + f"send{file_type.capitalize()}"
    data = {'chat_id': chat_id}

    if file_id:
        data[file_type] = file_id
        if caption:
            data['caption'] = caption
            data['parse_mode'] = 'HTML'
        if reply_markup:
            data['reply_markup'] = reply_markup

        print(f"{data = }")
        return httpx.post(url, json=data, timeout=timeout)

    else:
        files = {}
        mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        with open(file_path, 'rb') as f:
            files[file_type] = (file_path, f.read(), mime_type)

        if caption:
            data['caption'] = caption
            data['parse_mode'] = 'HTML'
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)

        return httpx.post(url, data=data, files=files, timeout=timeout)


def get_chat(chat_id: int):
    url = URL + f"getChat"
    params = {"chat_id": chat_id}
    response = httpx.get(url, params=params)
    return response

