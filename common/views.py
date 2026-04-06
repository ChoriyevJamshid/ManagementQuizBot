import logging

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from bot.webhook import webhook


logger = logging.getLogger(__name__)


@csrf_exempt
async def telegram_webhook(request: HttpRequest) -> HttpResponse:
    """
    Telegram webhook endpoint
    """

    if request.method != "POST":
        return HttpResponse(status=405)

    try:

        await webhook.process_update(request.body)

        return HttpResponse(status=200)

    except Exception:
        logger.exception("Webhook error")
        return HttpResponse(status=500)