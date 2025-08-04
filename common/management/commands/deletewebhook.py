import asyncio
from django.core.management.base import BaseCommand
from bot.webhook import webhook as wh


class Command(BaseCommand):
    help = 'Удаление webhook у Telegram-бота'

    def handle(self, *args, **options):
        asyncio.run(self._delete_webhook())

    async def _delete_webhook(self):
        webhook = await wh.bot.get_webhook_info()
        if webhook.url:
            await wh.bot.delete_webhook(drop_pending_updates=True)
            self.stdout.write(self.style.SUCCESS('✅ Webhook успешно удалён!'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ Webhook не установлен.'))