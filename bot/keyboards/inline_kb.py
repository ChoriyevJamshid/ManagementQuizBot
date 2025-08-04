from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton, InlineKeyboardMarkup
from bot import utils
from bot.utils.functions import get_texts, get_text


async def languages_markup():
    builder = InlineKeyboardBuilder()
    languages = await utils.get_languages()
    for language in languages:
        builder.add(
            InlineKeyboardButton(
                text=language.title,
                callback_data=f"choose-language_{language.code}")
        )
    return builder.adjust(*(1,)).as_markup()


async def main_menu_markup(language: str):
    builder = InlineKeyboardBuilder()
    texts = await get_texts((
        'my_quizzes_button',
        'create_quiz_button',
        'change_language_button',
        'instruction_button',
        'categories_button',
        'support_button'
    ), language)

    builder.add(InlineKeyboardButton(
        text=texts['my_quizzes_button'], callback_data=f"menu-quizzes"
    ))
    builder.add(InlineKeyboardButton(
        text=texts['create_quiz_button'], callback_data=f"menu-create-quiz"
    ))
    builder.add(InlineKeyboardButton(
        text=texts['categories_button'], callback_data=f"menu-categories"
    ))
    builder.add(InlineKeyboardButton(
        text=texts['instruction_button'], callback_data=f"menu-instruction"
    ))
    builder.add(InlineKeyboardButton(
        text=texts['support_button'], callback_data=f"menu-support"
    ))
    builder.add(InlineKeyboardButton(
        text=texts['change_language_button'], callback_data=f"menu-change-language"
    ))

    return builder.adjust(*(2, 2, 1,)).as_markup()


async def get_quizzes_markup(quiz_data: dict, state: FSMContext, language: str):
    data = await state.get_data()
    builder = InlineKeyboardBuilder()
    _builder = InlineKeyboardBuilder()

    for quiz_number, quiz_id in quiz_data.items():
        builder.add(
            InlineKeyboardButton(
                text=f"Quiz №{quiz_number}",
                callback_data=f"quiz-list-detail_{quiz_id}"
            )
        )
    current_page = data.get('current_page', 0)
    total_pages = data.get('total_pages', 0)
    size = 1

    if current_page > total_pages:
        if current_page > 1:
            size += 1
            _builder.add(InlineKeyboardButton(text="⬅️", callback_data=f"quiz-list-paginate_{current_page - 1}"))

        _builder.add(InlineKeyboardButton(text=f"{current_page}", callback_data=f"quiz-list-paginate_{current_page}"))

        if current_page < total_pages:
            size += 1
            _builder.add(InlineKeyboardButton(text="➡️", callback_data=f"quiz-list-paginate_{current_page + 1}"))

    _builder.add(InlineKeyboardButton(text="🔙", callback_data=f"back-to-main-menu"))
    return builder.adjust(*(2,)).attach(_builder.adjust(*(size, 1))).as_markup()


async def quiz_detail_markup(quiz, language: str):
    builder = InlineKeyboardBuilder()

    texts = await get_texts(('edit_timer_button', 'edit_privacy_button', 'turn_on', 'turn_off'), language)

    builder.add(InlineKeyboardButton(
        text=f'{texts["edit_timer_button"]}', callback_data=f"quiz-list-edit-timer_{quiz.id}"
    ))

    _privacy = "🔒" if quiz.privacy else " 🔐"
    ptext = texts['turn_off'] if quiz.privacy else texts['turn_on']
    builder.add(InlineKeyboardButton(
        text=f"{_privacy} {texts['edit_privacy_button']} ({ptext}) ", callback_data=f"quiz-list-edit-privacy_{quiz.id}"
    ))

    builder.add(InlineKeyboardButton(
        text='🔙', callback_data=f"quiz-list-back-user-quizzes"
    ))
    return builder.adjust(*(1,)).as_markup()


async def quiz_detail_edit_privacy_markup(quiz: dict, texts: dict):
    builder = InlineKeyboardBuilder()

    ptext = texts['turning_off'] if quiz['privacy'] is False else texts['turning_on']
    builder.add(InlineKeyboardButton(
        text=f"✅ ({ptext})", callback_data=f"quiz-list-changed-privacy_1_{quiz['id']}"
    ))

    builder.add(InlineKeyboardButton(
        text="❌", callback_data=f"quiz-list-changed-privacy_0_{quiz['id']}"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙", callback_data=f"quiz-list-changed-privacy_2_{quiz['id']}"
    ))

    return builder.adjust(*(2,)).as_markup()


async def test_manage_markup(part_id: int, language: str, username: str, link: str):
    builder = InlineKeyboardBuilder()

    texts = await get_texts(('testing_start_button', 'testing_start_in_group_button', 'share_quiz_button'), language)
    builder.add(
        InlineKeyboardButton(
            text=texts['testing_start_button'],
            callback_data=f"testing-start-pressed_{part_id}")
    )

    builder.add(
        InlineKeyboardButton(
            text=texts['testing_start_in_group_button'],
            url=f"https://t.me/{username}?startgroup={link}"
        )
    )

    builder.add(InlineKeyboardButton(
        text=texts['share_quiz_button'],
        switch_inline_query=f"share-quiz_{part_id}"
    ))

    return builder.adjust(*(1,)).as_markup()


async def test_start_markup(part_id: int, language: str):
    text = await get_text('testing_ready_button', language)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text, callback_data=f"testing-ready-pressed_{part_id}"
                )
            ]
        ]
    )


async def test_continue_markup(language: str, ):
    text = await get_text('testing_continue_button', language)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=f"testing-continue-quiz")]
        ]
    )


async def test_finished_markup(link: str, language: str):
    data_solo = await utils.get_data_solo()

    builder = InlineKeyboardBuilder()
    buttons = await get_texts(
        ('try_again_button', 'testing_start_in_group_button', 'share_quiz_button'),
        language
    )

    builder.add(
        InlineKeyboardButton(text=buttons['try_again_button'], callback_data=f"testing-try-quiz-retry_{link}")
    )

    builder.add(
        InlineKeyboardButton(
            text=buttons['testing_start_in_group_button'],
            url=f"https://t.me/{data_solo.username}?startgroup={link}"
        )
    )

    builder.add(
        InlineKeyboardButton(text=buttons['share_quiz_button'], switch_inline_query=f"share-quiz_{link}")
    )
    return builder.adjust(*(1,)).as_markup()


async def instruction_choice_file_type_markup(language: str):
    builder = InlineKeyboardBuilder()

    data_solo = await utils.get_data_solo()
    file_types = await get_texts(data_solo.file_types, language)

    sizes = (1, 2) if len(file_types) % 2 == 1 else (2,)
    for code, file_type in file_types.items():
        builder.add(InlineKeyboardButton(
            text=file_type, callback_data=f"instruction-file-type_{code.lower()}"
        ))
    return builder.adjust(*sizes).attach(
        InlineKeyboardBuilder().add(InlineKeyboardButton(
            text="🔙", callback_data="back-to-main-menu"
        ))
    ).as_markup()


async def instruction_back_markup():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙", callback_data="back-to-instruction"
            )]
        ]
    )


async def inline_mode_share_quiz_markup(
        start_url: str,
        start_in_group_url: str,
        parameter: int | str,
        language: str
):
    builder = InlineKeyboardBuilder()

    texts = await get_texts(
        codes=('start_this_quiz_button', 'testing_start_in_group_button', 'share_quiz_button'),
        language=language
    )

    builder.add(InlineKeyboardButton(
        text=texts['start_this_quiz_button'],
        url=start_url
    ))

    builder.add(InlineKeyboardButton(
        text=texts['testing_start_in_group_button'],
        url=start_in_group_url
    ))

    builder.add(InlineKeyboardButton(
        text=texts['share_quiz_button'],
        switch_inline_query=f"share-quiz_{parameter}"
    ))

    return builder.adjust(*(1,)).as_markup()


async def get_categories_markup(categories, language: str):
    iterator = 0
    builder = InlineKeyboardBuilder()
    texts = await get_texts([category['title'] for category in categories], language)

    for code, value in texts.items():
        builder.add(InlineKeyboardButton(
            text=value,
            callback_data=f"categories-list_{code}_{categories[iterator]['id']}"
        ))
        iterator += 1

    return builder.adjust(*(2,)).attach(InlineKeyboardBuilder().add(
        InlineKeyboardButton(text="🔙", callback_data="back-to-main-menu")
    )).as_markup()


async def categories_detail_markup(quiz_ids: list | tuple, total_pages: int, page_number: int, language: str):
    builder = InlineKeyboardBuilder()

    for number, quiz_id in enumerate(quiz_ids, start=1):
        builder.add(InlineKeyboardButton(
            text=f"Quiz #{number}", callback_data=f"categories-quizzes-detail_{quiz_id}"
        ))
    builder.adjust(*(4,))
    if total_pages > 1:
        _builder = InlineKeyboardBuilder()

        if page_number > 1:
            _builder.add(InlineKeyboardButton(
                text="⬅️", callback_data=f"categories-quizzes-paginate_{page_number - 1}"
            ))
        _builder.add(InlineKeyboardButton(
            text=f"{page_number}", callback_data=f"categories-quizzes-paginate_{page_number}"
        ))

        if page_number < total_pages:
            _builder.add(InlineKeyboardButton(
                text="➡️", callback_data=f"categories-quizzes-paginate_{page_number + 1}"
            ))

        builder.attach(_builder.adjust(*(3,)))

    return builder.attach(InlineKeyboardBuilder().add(InlineKeyboardButton(
        text="🔙", callback_data=f"categories-back-to-categories"
    ))).as_markup()


async def categories_quiz_parts_markup(quiz_parts, category: str, category_id: int, language: str):
    builder = InlineKeyboardBuilder()

    if len(quiz_parts) <= 10:
        sizes = (1,)
    if 10 < len(quiz_parts) <= 20:
        sizes = (2,)
    if 20 < len(quiz_parts) <= 30:
        sizes = (3,)
    else:
        sizes = (4,)

    text = await get_text("questions_text", language)
    for quiz_part in quiz_parts:
        builder.add(InlineKeyboardButton(
            text=f"[{quiz_part.from_i} - {quiz_part.to_i}]",
            callback_data=f"categories-quizzes-parts_{quiz_part.link}"
        ))

    return builder.adjust(*sizes).attach(InlineKeyboardBuilder().add(
        InlineKeyboardButton(text="🔙", callback_data=f"categories-back-to-quizzes_{category}_{category_id}"))
    ).as_markup()


async def support_menu_markup(texts: dict):
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text=f"{texts['appeal_to_admin_button']}",
        callback_data=f"support-appeal-to-admin-menu"
    ))

    builder.add(InlineKeyboardButton(
        text=f"{texts['add_category_button']}",
        callback_data=f"support-add-new-category"
    ))

    builder.add(InlineKeyboardButton(
        text=f"{texts['testing_questions_file']}",
        callback_data=f"support-testing-questions-file"
    ))

    builder.add(InlineKeyboardButton(
        text="🔙", callback_data=f"back-to-main-menu"
    ))

    return builder.adjust(*(1,)).as_markup()


async def support_appeal_to_admin_markup(texts: dict):
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text=f"{texts['writen_messages_button']}",
        callback_data=f"support-appeal-to-admin_messages"
    ))

    builder.add(InlineKeyboardButton(
        text=f"{texts['write_new_message_button']}",
        callback_data=f"support-appeal-to-admin_newMessage"
    ))

    builder.add(InlineKeyboardButton(
        text="🔙", callback_data=f"support-back-to-support-menu"
    ))

    return builder.adjust(*(2,)).as_markup()


async def support_message_markup(message_id: int, texts: dict):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{texts['me_read_text']}",
                callback_data=f"support-mark-message-as-read_{message_id}"
            )]
        ]
    )


# admin.py keyboards

async def admin_menu_markup(texts: dict):
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text=f"{texts['admin_user_count_button']}",
        callback_data=f"admin-users-count"
    ))

    builder.add(InlineKeyboardButton(
        text=f"{texts['admin_support_messages_count_button']}",
        callback_data=f"admin-support-messages-count"
    ))

    builder.add(InlineKeyboardButton(
        text=f"{texts['admin_support_pending_messages_button']}",
        callback_data=f"admin-support-pending-messages"
    ))

    builder.add(InlineKeyboardButton(
        text=f"🔙",
        callback_data=f"back-to-main-menu"
    ))

    return builder.adjust(*(2, 1, 1)).as_markup()


async def admin_pending_message_markup(ids: list):
    builder = InlineKeyboardBuilder()

    for number, _id in enumerate(ids, start=1):
        builder.add(
            InlineKeyboardButton(
                text=f"#{number}",
                callback_data=f"admin-pending-message-check_{_id}"
            )
        )

    return builder.adjust(*(5,)).attach(
        InlineKeyboardBuilder().add(InlineKeyboardButton(
            text="🔙",
            callback_data=f"back-to-admin-menu"
        ))
    ).as_markup()


# group handlers keyboards


async def group_ready_markup(group_id: str, language: str):
    text = await get_text('testing_ready_button', language)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"group-ready_{group_id}"
                )
            ]
        ]
    )


async def test_group_continue_markup(group_id: str, index: int, language: str, ):
    text = await get_text('testing_continue_button', language)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=f"testing-group-continue-quiz_{group_id}_{index}")]
        ]
    )


async def test_group_share_quiz(link: str):
    text = await get_text('share_quiz_button', 'en')
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, switch_inline_query=f"share-quiz_{link}")]
        ]
    )
