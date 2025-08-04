import unicodedata
from bs4 import BeautifulSoup

def clean_from_html(text: str) -> str:
    allowed_tags = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "span", "tg-spoiler",
                    "code", "pre", "a"}
    allowed_attrs = {"href"}


    soup = BeautifulSoup(text, "html.parser")

    for tag in soup.find_all():
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            attrs = {key: value for key, value in tag.attrs.items() if key in allowed_attrs}
            tag.attrs = attrs

    cleaned_text = str(soup)
    cleaned_text = unicodedata.normalize("NFKC", cleaned_text).replace("\xa0", " ")

    return cleaned_text


def clean_from_html_for_tinymce(text: str) -> str:
    allowed_tags = {
        "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
        "span", "tg-spoiler", "code", "pre", "a"
    }
    allowed_attrs = {"href"}

    soup = BeautifulSoup(text, "html.parser")

    for br in soup.find_all("br"):
        br.replace_with("\n")

    for tag in soup.find_all():
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            tag.attrs = {key: value for key, value in tag.attrs.items() if key in allowed_attrs}

    cleaned_text = str(soup)

    cleaned_text = unicodedata.normalize("NFKC", cleaned_text)
    cleaned_text = cleaned_text.replace("\xa0", " ")  # неразрывный пробел

    return cleaned_text


def get_file_type(extension: str) -> str:
    if extension in ('jpg', 'jpeg', 'png'):
        file_type = 'photo'
    elif extension in ('mov', 'mp4'):
        file_type = 'video'
    elif extension in ('mp3', 'ogg', 'wav', 'aac'):
        file_type = 'audio'
    else:
        file_type = 'document'
    return file_type


