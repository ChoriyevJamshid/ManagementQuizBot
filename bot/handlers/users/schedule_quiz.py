import re
from datetime import date as date_type

from aiogram import types
from aiogram.fsm.context import FSMContext

from bot import utils
from bot.keyboards import inline_kb
from bot.states import ScheduleQuizState, QuizState
from bot.utils.functions import get_text, get_texts
from utils.choices import Role


def _days_display(days_value: str) -> str:
    mapping = {
        '*': 'Har kuni',
        '1,2,3,4,5': 'Ish kunlari (Du-Ju)',
        '0': 'Yakshanba',
        '1': 'Dushanba',
        '2': 'Seshanba',
        '3': 'Chorshanba',
        '4': 'Payshanba',
        '5': 'Juma',
        '6': 'Shanba',
    }
    return mapping.get(days_value, days_value)


async def _is_allowed(user) -> bool:
    return user.role in (Role.ADMIN, Role.MODERATOR)


# ── Entry: "📅 Jadval" clicked on quiz detail ────────────────────────────────

async def schedule_quiz_start_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)

    if not await _is_allowed(user):
        text = await get_text('schedule_not_allowed')
        return await callback.answer(text, show_alert=True)

    quiz_id = int(callback.data.split('_')[-1])
    quiz_parts = await utils.get_quiz_parts(quiz_id)

    await state.update_data(schedule_quiz_id=quiz_id)

    text = await get_text('schedule_select_part')
    markup = await inline_kb.schedule_parts_markup(quiz_parts)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduleQuizState.select_part)
    await callback.answer()


# ── Part selected ────────────────────────────────────────────────────────────

async def schedule_part_selected_handler(callback: types.CallbackQuery, state: FSMContext):
    part_id = int(callback.data.split('_')[-1])
    await state.update_data(schedule_part_id=part_id)

    groups = await utils.get_distinct_groups()
    await state.update_data(schedule_groups=groups)

    text = await get_text('schedule_select_group')
    markup = await inline_kb.schedule_groups_markup(groups)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduleQuizState.select_group)
    await callback.answer()


# ── Group selected from list ─────────────────────────────────────────────────

async def schedule_group_selected_handler(callback: types.CallbackQuery, state: FSMContext):
    idx = int(callback.data.split('_')[-1])
    data = await state.get_data()
    groups = data.get('schedule_groups', [])

    if idx >= len(groups):
        return await callback.answer()

    group = groups[idx]
    await state.update_data(
        schedule_group_id=group['group_id'],
        schedule_group_title=group.get('title') or group['group_id'],
    )

    text = await get_text('schedule_select_type')
    markup = await inline_kb.schedule_type_markup()
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduleQuizState.select_type)
    await callback.answer()


# ── Manual group input ───────────────────────────────────────────────────────

async def schedule_group_manual_handler(callback: types.CallbackQuery, state: FSMContext):
    text = await get_text('schedule_enter_group_id')
    await callback.message.edit_text(text)
    await state.set_state(ScheduleQuizState.enter_group_id)
    await callback.answer()


async def schedule_group_id_entered_handler(message: types.Message, state: FSMContext):
    group_id = message.text.strip()

    if not re.match(r'^-?\d+$', group_id):
        text = await get_text('schedule_group_id_invalid')
        return await message.answer(text)

    await state.update_data(schedule_group_id=group_id, schedule_group_title=group_id)

    text = await get_text('schedule_select_type')
    markup = await inline_kb.schedule_type_markup()
    await message.answer(text, reply_markup=markup)
    await state.set_state(ScheduleQuizState.select_type)


# ── Type selected ────────────────────────────────────────────────────────────

async def schedule_type_onetime_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(schedule_is_periodic=False)
    text = await get_text('schedule_select_date')
    await callback.message.edit_text(text)
    await state.set_state(ScheduleQuizState.select_date)
    await callback.answer()


async def schedule_type_periodic_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(schedule_is_periodic=True)
    text = await get_text('schedule_select_days')
    markup = await inline_kb.schedule_days_markup()
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduleQuizState.select_days)
    await callback.answer()


# ── Days selected (periodic) ─────────────────────────────────────────────────

async def schedule_days_selected_handler(callback: types.CallbackQuery, state: FSMContext):
    # callback_data = "schedule-days_*" or "schedule-days_1,2,3,4,5" etc.
    days_value = callback.data[len("schedule-days_"):]
    await state.update_data(schedule_days_of_week=days_value)

    text = await get_text('schedule_select_time')
    await callback.message.edit_text(text)
    await state.set_state(ScheduleQuizState.select_time)
    await callback.answer()


# ── Date entered (one_time) ──────────────────────────────────────────────────

async def schedule_date_entered_handler(message: types.Message, state: FSMContext):
    date_str = message.text.strip()

    try:
        parts = date_str.split('.')
        if len(parts) != 3:
            raise ValueError
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        entered = date_type(year, month, day)
        if entered < date_type.today():
            raise ValueError("past date")
    except Exception:
        text = await get_text('schedule_date_invalid')
        return await message.answer(text)

    await state.update_data(schedule_date=date_str)
    text = await get_text('schedule_select_time')
    await message.answer(text)
    await state.set_state(ScheduleQuizState.select_time)


# ── Time entered ─────────────────────────────────────────────────────────────

async def schedule_time_entered_handler(message: types.Message, state: FSMContext):
    time_str = message.text.strip()

    if not re.match(r'^([01]?\d|2[0-3]):[0-5]\d$', time_str):
        text = await get_text('schedule_time_invalid')
        return await message.answer(text)

    await state.update_data(schedule_time=time_str)
    data = await state.get_data()
    await _show_confirmation(message, data)
    await state.set_state(ScheduleQuizState.confirm)


async def _show_confirmation(message: types.Message, data: dict):
    part_id = data['schedule_part_id']
    quiz_part = await utils.get_quiz_part_by_id(part_id)

    group_title = data.get('schedule_group_title') or data.get('schedule_group_id', '')
    time_str = data['schedule_time']
    is_periodic = data.get('schedule_is_periodic', False)

    if is_periodic:
        days_str = data.get('schedule_days_of_week', '*')
        type_text = await get_text('schedule_periodic_type_text', {'days': _days_display(days_str)})
    else:
        date_str = data.get('schedule_date', '')
        type_text = await get_text('schedule_one_time_type_text', {'date': date_str})

    text = await get_text('schedule_confirm_text', {
        'quiz': quiz_part.quiz.title,
        'from_i': str(quiz_part.from_i),
        'to_i': str(quiz_part.to_i),
        'group': group_title,
        'time': time_str,
        'type': type_text,
    })

    markup = await inline_kb.schedule_confirm_markup()
    await message.answer(text, reply_markup=markup)


# ── Confirmed ────────────────────────────────────────────────────────────────

async def schedule_confirm_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    data = await state.get_data()

    hour, minute = map(int, data['schedule_time'].split(':'))

    start_date = None
    if date_str := data.get('schedule_date'):
        day, month, year = map(int, date_str.split('.'))
        start_date = date_type(year, month, day)

    await utils.create_scheduled_quiz(
        quiz_part_id=data['schedule_part_id'],
        created_by_id=user.id,
        group_id=data['schedule_group_id'],
        group_title=data.get('schedule_group_title', ''),
        is_periodic=data.get('schedule_is_periodic', False),
        hour=hour,
        minute=minute,
        days_of_week=data.get('schedule_days_of_week', '*'),
        start_date=start_date,
    )

    text = await get_text('schedule_created')
    await callback.message.edit_text(text)
    await state.clear()
    await callback.answer()


# ── Cancelled ────────────────────────────────────────────────────────────────

async def schedule_cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    text = await get_text('schedule_cancelled')
    await callback.message.edit_text(text)
    await state.clear()
    await callback.answer()


# ── Back navigation ───────────────────────────────────────────────────────────

async def schedule_back_to_quiz_detail_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    quiz_id = data.get('schedule_quiz_id')
    if not quiz_id:
        return await callback.answer()

    quiz = await utils.get_quiz_by_id(quiz_id)
    quiz_parts = await utils.get_quiz_parts(quiz_id)

    text = await get_text('quiz_list_detail_quiz_parts')
    markup = await inline_kb.quiz_detail_markup(quiz)
    text += "\n"
    for index, part in enumerate(quiz_parts, start=1):
        text += f"\n<b>{index}. [{part.from_i} - {part.to_i}]</b> 👉 /quiz_{part.link}"

    await callback.message.edit_text(text=text, reply_markup=markup)
    await state.set_state(QuizState.quizzes)
    await callback.answer()


async def schedule_back_to_parts_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    quiz_parts = await utils.get_quiz_parts(data.get('schedule_quiz_id'))

    text = await get_text('schedule_select_part')
    markup = await inline_kb.schedule_parts_markup(quiz_parts)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduleQuizState.select_part)
    await callback.answer()


async def schedule_back_to_groups_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    groups = data.get('schedule_groups', [])

    text = await get_text('schedule_select_group')
    markup = await inline_kb.schedule_groups_markup(groups)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduleQuizState.select_group)
    await callback.answer()


async def schedule_back_to_type_handler(callback: types.CallbackQuery, state: FSMContext):
    text = await get_text('schedule_select_type')
    markup = await inline_kb.schedule_type_markup()
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduleQuizState.select_type)
    await callback.answer()
