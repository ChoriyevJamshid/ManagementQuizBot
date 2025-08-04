import asyncio
from django.conf import settings
from django.core.management import BaseCommand
from utils.bot import send_message
from bot.app import main


class Command(BaseCommand):
    help = 'Run the bot'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting bot...'))
        # send_message(chat_id=settings.ADMIN, text='Bot has been started!')
        main()
