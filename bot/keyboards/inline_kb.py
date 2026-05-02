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


async def main_menu_markup(show_schedule: bool = False):
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
    if show_schedule:
        ss_btn = await get_text('ss_main_menu_button')
        builder.add(InlineKeyboardButton(
            text=ss_btn, callback_data="menu-scheduled-sessions"
        ))
        return builder.adjust(2, 1, 1).as_markup()

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

    texts = await get_texts(('edit_timer_button', 'edit_privacy_button', 'turn_on', 'turn_off'))

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


async def ss_groups_markup(groups: list):
    builder = InlineKeyboardBuilder()
    for i, g in enumerate(groups):
        title = g.get('title') or g.get('group_id', '')
        builder.add(InlineKeyboardButton(
            text=f"📌 {title}",
            callback_data=f"ss-group-idx_{i}"
        ))
    texts = await get_texts(('ss_btn_enter_manual', 'ss_btn_back'))
    builder.add(InlineKeyboardButton(text=texts['ss_btn_enter_manual'], callback_data="ss-group-manual"))
    return builder.adjust(1).as_markup()


async def ss_parts_markup(all_parts: list, selected_ids: list, page: int = 0, page_size: int = 10):
    total = len(all_parts)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))

    page_parts = all_parts[page * page_size: (page + 1) * page_size]

    builder = InlineKeyboardBuilder()
    for part in page_parts:
        mark = "✅" if part['id'] in selected_ids else "☐"
        raw = f"{mark} {part['quiz_title']} → [{part['from_i']} - {part['to_i']}]"
        label = raw if len(raw) <= 38 else raw[:37] + '…'
        builder.add(InlineKeyboardButton(
            text=label,
            callback_data=f"ss-part-toggle_{part['id']}"
        ))

    row_widths = [1] * len(page_parts)

    if total_pages > 1:
        prev_cb = f"ss-parts-page_{page - 1}" if page > 0 else "ss-parts-noop"
        next_cb = f"ss-parts-page_{page + 1}" if page < total_pages - 1 else "ss-parts-noop"
        builder.add(InlineKeyboardButton(text="◀", callback_data=prev_cb))
        builder.add(InlineKeyboardButton(
            text=f"{page + 1} / {total_pages}",
            callback_data="ss-parts-noop",
        ))
        builder.add(InlineKeyboardButton(text="▶", callback_data=next_cb))
        row_widths.append(3)

    texts = await get_texts(('ss_btn_done_empty', 'ss_btn_back'))
    if selected_ids:
        done_text = f"✅ Tayyor ({len(selected_ids)} ta)"
        done_cb = "ss-parts-done"
    else:
        done_text = texts['ss_btn_done_empty']
        done_cb = "ss-parts-none"

    builder.add(InlineKeyboardButton(text=done_text, callback_data=done_cb))
    builder.add(InlineKeyboardButton(text=texts['ss_btn_back'], callback_data="ss-back-to-groups"))
    row_widths += [1, 1]

    builder.adjust(*row_widths)
    return builder.as_markup()


async def ss_date_markup():
    import pytz
    from datetime import datetime, timedelta
    # Use Tashkent's current date, not the server's local date
    _tz = pytz.timezone('Asia/Tashkent')
    today = datetime.now(_tz).date()
    texts = await get_texts(('ss_date_today', 'ss_date_tomorrow', 'ss_date_day_after', 'ss_date_3days', 'ss_btn_back'))
    d3 = today + timedelta(days=3)
    days = [
        (today, texts['ss_date_today']),
        (today + timedelta(days=1), texts['ss_date_tomorrow']),
        (today + timedelta(days=2), texts['ss_date_day_after']),
        (d3, texts['ss_date_3days'].replace('__date', d3.strftime('%d.%m'))),
    ]
    builder = InlineKeyboardBuilder()
    for d, label in days:
        builder.add(InlineKeyboardButton(
            text=label,
            callback_data=f"ss-date_{d.strftime('%d.%m.%Y')}"
        ))
    builder.add(InlineKeyboardButton(text=texts['ss_btn_back'], callback_data="ss-back-to-parts"))
    return builder.adjust(2, 2, 1).as_markup()


async def ss_confirm_markup():
    texts = await get_texts(('ss_btn_confirm', 'ss_btn_cancel', 'ss_btn_back'))
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=texts['ss_btn_confirm'], callback_data="ss-confirm"))
    builder.add(InlineKeyboardButton(text=texts['ss_btn_cancel'], callback_data="ss-cancel"))
    builder.add(InlineKeyboardButton(text=texts['ss_btn_back'], callback_data="ss-back-to-time"))
    return builder.adjust(2, 1).as_markup()


async def ss_list_markup(sessions: list):
    import pytz
    tz = pytz.timezone('Asia/Tashkent')
    builder = InlineKeyboardBuilder()
    for session in sessions:
        local_dt = session.scheduled_at.astimezone(tz)
        label = f"🗓 {session.group_title or session.group_id} — {local_dt.strftime('%d.%m %H:%M')}"
        builder.add(InlineKeyboardButton(
            text=label,
            callback_data=f"ss-detail_{session.pk}"
        ))
    texts = await get_texts(('ss_btn_create_new', 'ss_btn_main_menu'))
    builder.add(InlineKeyboardButton(text=texts['ss_btn_create_new'], callback_data="ss-create"))
    builder.add(InlineKeyboardButton(text=texts['ss_btn_main_menu'], callback_data="back-to-main-menu"))
    return builder.adjust(1).as_markup()


async def ss_detail_markup(session_id: int):
    texts = await get_texts(('ss_btn_cancel_session', 'ss_btn_back_to_list'))
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=texts['ss_btn_cancel_session'], callback_data=f"ss-cancel-session_{session_id}"))
    builder.add(InlineKeyboardButton(text=texts['ss_btn_back_to_list'], callback_data="menu-scheduled-sessions"))
    return builder.adjust(1).as_markup()


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
