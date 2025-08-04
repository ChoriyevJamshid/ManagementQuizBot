import asyncio
import logging
from asgiref.sync import async_to_sync
from django.http.request import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.http.response import HttpResponse


from bot.webhook import webhook



@csrf_exempt
async def telegram_webhook(request: HttpRequest):
    logging.info(f"Webhook received: {request}\n")
    try:
        # если webhook.process — sync функция, обернем её
        body = request.body.decode("utf-8")
        asyncio.create_task(webhook.process_body(body))
    except Exception as e:
        print(e)
        logging.error(e)
    return HttpResponse(status=200)


