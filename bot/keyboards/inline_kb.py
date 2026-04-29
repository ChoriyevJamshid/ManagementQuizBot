from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton, InlineKeyboardMarkup
from bot import utils
from bot.utils.functions import get_texts, get_text


async def get_languages_markup():
    builder = InlineKeyboardBuilder()
    languages = await utils.get_languages()
    for language in languages:
        builder.add(
            InlineKeyboardButton(
                text=language.title,
                callback_data=f"choose-language_{language.code}")
        )
    return builder.adjust(*(1,)).as_markup()


async def main_menu_markup():
    builder = InlineKeyboardBuilder()
    texts = await get_texts((
        'my_quizzes_button',
        'create_quiz_button',
        'instruction_button',
    ))

    builder.add(InlineKeyboardButton(
        text=texts['my_quizzes_button'], callback_data=f"menu-quizzes"
    ))
    builder.add(InlineKeyboardButton(
        text=texts['create_quiz_button'], callback_data=f"menu-create-quiz"
    ))
    builder.add(InlineKeyboardButton(
        text=texts['instruction_button'], callback_data=f"menu-instruction"
    ))

    return builder.adjust(*(2, 1,)).as_markup()


async def get_quizzes_markup(quiz_data: dict, state: FSMContext):
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


async def quiz_detail_markup(quiz):
    builder = InlineKeyboardBuilder()

    texts = await get_texts(('edit_timer_button', 'edit_privacy_button', 'turn_on', 'turn_off', 'schedule_button'))

    builder.add(InlineKeyboardButton(
        text=f'{texts["edit_timer_button"]}', callback_data=f"quiz-list-edit-timer_{quiz.id}"
    ))

    _privacy = "🔒" if quiz.privacy else " 🔐"
    ptext = texts['turn_off'] if quiz.privacy else texts['turn_on']
    builder.add(InlineKeyboardButton(
        text=f"{_privacy} {texts['edit_privacy_button']} ({ptext}) ", callback_data=f"quiz-list-edit-privacy_{quiz.id}"
    ))

    builder.add(InlineKeyboardButton(
        text=texts['schedule_button'], callback_data=f"quiz-schedule_{quiz.id}"
    ))

    builder.add(InlineKeyboardButton(
        text='🔙', callback_data=f"quiz-list-back-user-quizzes"
    ))
    return builder.adjust(*(1,)).as_markup()


async def schedule_parts_markup(quiz_parts: list):
    builder = InlineKeyboardBuilder()
    for part in quiz_parts:
        builder.add(InlineKeyboardButton(
            text=f"[{part.from_i} - {part.to_i}]",
            callback_data=f"schedule-part_{part.id}"
        ))
    back_text = await get_text('back_text')
    builder.add(InlineKeyboardButton(text=back_text, callback_data="schedule-back-to-quiz-detail"))
    return builder.adjust(2, 1).as_markup()


async def schedule_groups_markup(groups: list):
    builder = InlineKeyboardBuilder()
    for i, g in enumerate(groups):
        title = g.get('title') or g.get('group_id', '')
        builder.add(InlineKeyboardButton(
            text=f"📌 {title}",
            callback_data=f"schedule-group-idx_{i}"
        ))
    texts = await get_texts(('schedule_other_group', 'back_text'))
    builder.add(InlineKeyboardButton(text=texts['schedule_other_group'], callback_data="schedule-group-manual"))
    builder.add(InlineKeyboardButton(text=texts['back_text'], callback_data="schedule-back-to-parts"))
    return builder.adjust(1).as_markup()


async def schedule_type_markup():
    texts = await get_texts(('schedule_one_time', 'schedule_periodic', 'back_text'))
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=texts['schedule_one_time'], callback_data="schedule-type-onetime"))
    builder.add(InlineKeyboardButton(text=texts['schedule_periodic'], callback_data="schedule-type-periodic"))
    builder.add(InlineKeyboardButton(text=texts['back_text'], callback_data="schedule-back-to-groups"))
    return builder.adjust(1).as_markup()


async def schedule_days_markup():
    texts = await get_texts((
        'schedule_days_every', 'schedule_days_weekdays',
        'schedule_day_mon', 'schedule_day_tue', 'schedule_day_wed',
        'schedule_day_thu', 'schedule_day_fri', 'schedule_day_sat',
        'schedule_day_sun', 'back_text',
    ))
    days = [
        ('*', texts['schedule_days_every']),
        ('1,2,3,4,5', texts['schedule_days_weekdays']),
        ('1', texts['schedule_day_mon']),
        ('2', texts['schedule_day_tue']),
        ('3', texts['schedule_day_wed']),
        ('4', texts['schedule_day_thu']),
        ('5', texts['schedule_day_fri']),
        ('6', texts['schedule_day_sat']),
        ('0', texts['schedule_day_sun']),
    ]
    builder = InlineKeyboardBuilder()
    for value, label in days:
        builder.add(InlineKeyboardButton(
            text=label,
            callback_data=f"schedule-days_{value}"
        ))
    builder.add(InlineKeyboardButton(text=texts['back_text'], callback_data="schedule-back-to-type"))
    return builder.adjust(2, 2, 2, 2, 1, 1).as_markup()


async def schedule_confirm_markup():
    texts = await get_texts(('schedule_confirm_btn', 'schedule_cancel_btn'))
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=texts['schedule_confirm_btn'], callback_data="schedule-confirm"))
    builder.add(InlineKeyboardButton(text=texts['schedule_cancel_btn'], callback_data="schedule-cancel"))
    return builder.adjust(2).as_markup()


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


async def test_manage_markup(part_id: int, username: str, link: str):
    builder = InlineKeyboardBuilder()

    texts = await get_texts(('testing_start_button', 'testing_start_in_group_button', 'share_quiz_button'))
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


async def test_start_markup(part_id: int):
    text = await get_text('testing_ready_button')
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text, callback_data=f"testing-ready-pressed_{part_id}"
                )
            ]
        ]
    )


async def test_continue_markup():
    text = await get_text('testing_continue_button')
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=f"testing-continue-quiz")]
        ]
    )


async def test_finished_markup(link: str):
    data_solo = await utils.get_data_solo()

    builder = InlineKeyboardBuilder()
    buttons = await get_texts(
        ('try_again_button', 'testing_start_in_group_button', 'share_quiz_button')
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


async def instruction_choice_file_type_markup():
    builder = InlineKeyboardBuilder()

    data_solo = await utils.get_data_solo()
    file_types = await get_texts(data_solo.file_types)

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
        parameter: int | str
):
    builder = InlineKeyboardBuilder()

    texts = await get_texts(
        codes=('start_this_quiz_button', 'testing_start_in_group_button', 'share_quiz_button')
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


# admin.py keyboards

async def admin_menu_markup(texts: dict):
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text=f"{texts['admin_user_count_button']}",
        callback_data=f"admin-users-count"
    ))

    builder.add(InlineKeyboardButton(
        text=f"🔙",
        callback_data=f"back-to-main-menu"
    ))

    return builder.adjust(*(1, 1)).as_markup()


# group handlers keyboards


async def group_ready_markup(group_id: str):
    text = await get_text('testing_ready_button')

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


async def test_group_continue_markup(group_id: str, index: int):
    text = await get_text('testing_continue_button')
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=f"testing-group-continue-quiz_{group_id}_{index}")]
        ]
    )


async def test_group_share_quiz(texts: dict, link: str, group_quiz_id: int = 0):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts['get_excel_button'],
                    callback_data=f"testing-group-get-excel_{group_quiz_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=texts['share_quiz_button'],
                    switch_inline_query=f"share-quiz_{link}"
                )
            ]
        ]
    )
