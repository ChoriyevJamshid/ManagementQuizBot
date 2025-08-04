import os
import orjson
from django.conf import settings
from django.core.management import BaseCommand
from common.models import Language, Text
from utils.functions import clean_from_html


class Command(BaseCommand):
    help = 'Load the language files'

    def handle(self, *args, **options):
        os.makedirs(f'{settings.BASE_DIR}/languages', exist_ok=True)
        languages = Language.objects.all().values_list('code', flat=True)
        file_names = os.listdir(f"{settings.BASE_DIR}/languages")

        for language in languages:
            if language not in file_names:
                with open(f'{settings.BASE_DIR}/languages/{language}.json', 'wb') as f:
                    f.write(orjson.dumps({}, option=4))


        texts = Text.objects.all().select_related("language")
        for text in texts:
            with open(f'{settings.BASE_DIR}/languages/{text.language.code}.json', 'rb') as f:
                data = orjson.loads(f.read())

            data[f'{text.code}'] = clean_from_html(text.text)

            with open(f'{settings.BASE_DIR}/languages/{text.language.code}.json', 'wb') as f:
                f.write(orjson.dumps(data, option=4))

        self.stdout.write(self.style.SUCCESS('Files loaded successfully!...'))

