import asyncio

from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bot.webhook import webhook as wh


class Command(BaseCommand):
    help = 'Setting webhook'

    def handle(self, *args, **options):
        asyncio.run(self.set_webhook())

    async def set_webhook(self):
        webhook_url = settings.WEBHOOK_URL
        webhook = await wh.bot.get_webhook_info()
        if webhook.url != settings.WEBHOOK_URL or webhook.max_connections != 100:
            await wh.bot.set_webhook(
                webhook_url,
                drop_pending_updates=True,
                max_connections=100,
                allowed_updates=[
                    "message", "edited_message", "channel_post", "edited_channel_post",
                    "inline_query", "chosen_inline_result", "callback_query",
                    "shipping_query", "pre_checkout_query", "poll", "poll_answer",
                    "chat_member", "my_chat_member", "chat_join_request"
                ]
            )
            self.stdout.write(self.style.SUCCESS('✅ Webhook успешно установлен!'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ Webhook уже установлен.'))