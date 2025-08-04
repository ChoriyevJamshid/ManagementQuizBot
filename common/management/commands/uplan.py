import os
import orjson
from django.conf import settings
from django.core.management import BaseCommand
from common.models import Language, Text, TextCode
from utils.functions import clean_from_html


class Command(BaseCommand):
    help = 'Load the language files'

    def handle(self, *args, **options):
        langs = os.listdir(f'{settings.BASE_DIR}/languages')
        for lang in langs:
            code = lang.split('.')[0]
            language = Language.objects.filter(code=code).first()
            if not language:
                language  = Language.objects.create(code=code, title=code)

            with open(f'{settings.BASE_DIR}/languages/{code}.json', 'r', encoding='utf-8') as f:
                data = orjson.loads(f.read())

            for key, value in data.items():
                text_code = TextCode.objects.filter(code=key).first()
                if not text_code:
                    text_code = TextCode.objects.create(code=key)

                text = Text.objects.filter(code=text_code, language=language).first()
                if not text:
                    Text.objects.create(code=text_code, language=language, text=value)
                else:
                    if clean_from_html(text.text) != value:
                        text.text = value
                        text.save(update_fields=['text'])

        self.stdout.write(self.style.SUCCESS('Files loaded successfully!...'))

