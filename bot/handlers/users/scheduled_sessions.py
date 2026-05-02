import re
import pytz
from datetime import datetime, timezone as dt_timezone

from aiogram import types
from aiogram.fsm.context import FSMContext

from bot import utils
from bot.keyboards import inline_kb
from bot.states import ScheduledSessionState, MainState
from bot.utils.functions import get_text
from utils.choices import Role

_TZ = pytz.timezone('Asia/Tashkent')


def _is_privileged(user) -> bool:
    return user.role in (Role.ADMIN, Role.MODERATOR)


async def _require_privileged(callback: types.CallbackQuery, user) -> bool:
    if not _is_privileged(user):
        text = await get_text('ss_not_allowed')
        await callback.answer(text, show_alert=True)
        return False
    return True


# ── Список расписаний ─────────────────────────────────────────────────────────

async def ss_list_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    if not await _require_privileged(callback, user):
        return

    sessions = await utils.get_active_scheduled_sessions()
    text = await get_text('ss_list_title')
    markup = await inline_kb.ss_list_markup(sessions)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.clear()
    await callback.answer()


async def ss_detail_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    if not await _require_privileged(callback, user):
        return

    session_id = int(callback.data.split('_')[-1])
    session = await _get_session(session_id)
    if not session:
        text = await get_text('ss_not_found')
        await callback.answer(text, show_alert=True)
        return

    text = _format_session_detail(session)
    markup = await inline_kb.ss_detail_markup(session_id)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


async def ss_cancel_session_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    if not await _require_privileged(callback, user):
        return

    session_id = int(callback.data.split('_')[-1])
    session = await utils.cancel_scheduled_session(session_id)
    if not session:
        text = await get_text('ss_already_cancelled')
        await callback.answer(text, show_alert=True)
        return

    from bot.utils.methods import send_text as tg_send_text
    cancel_text = await get_text('ss_cancelled_group_notify')
    tg_send_text(chat_id=int(session.group_id), text=cancel_text)

    sessions = await utils.get_active_scheduled_sessions()
    list_text = await get_text('ss_list_title')
    markup = await inline_kb.ss_list_markup(sessions)
    await callback.message.edit_text(list_text, reply_markup=markup)
    alert_text = await get_text('ss_cancel_success_alert')
    await callback.answer(alert_text, show_alert=True)


# ── Создание: шаг 1 — группа ─────────────────────────────────────────────────

async def ss_create_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    if not await _require_privileged(callback, user):
        return

    groups = await utils.get_distinct_groups()
    await state.update_data(ss_groups=groups, ss_selected_parts=[])

    text = await get_text('ss_select_group')
    markup = await inline_kb.ss_groups_markup(groups)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduledSessionState.select_group)
    await callback.answer()


async def ss_group_selected_handler(callback: types.CallbackQuery, state: FSMContext):
    idx = int(callback.data.split('_')[-1])
    data = await state.get_data()
    groups = data.get('ss_groups', [])

    if idx >= len(groups):
        return await callback.answer()

    group = groups[idx]
    await state.update_data(
        ss_group_id=group['group_id'],
        ss_group_title=group.get('title') or group['group_id'],
    )
    await _go_to_parts(callback, state)


async def ss_group_manual_handler(callback: types.CallbackQuery, state: FSMContext):
    text = await get_text('ss_enter_group_id')
    await callback.message.edit_text(text)
    await state.set_state(ScheduledSessionState.enter_group_id)
    await callback.answer()


async def ss_group_id_entered_handler(message: types.Message, state: FSMContext):
    group_id = message.text.strip()
    if not re.match(r'^-?\d+$', group_id):
        text = await get_text('ss_group_id_invalid')
        return await message.answer(text)

    await state.update_data(ss_group_id=group_id, ss_group_title=group_id)

    class _FakeCallback:
        message = message
        async def answer(self): pass

    await _go_to_parts(_FakeCallback(), state, edit=False)


# ── Создание: шаг 2 — части квиза ────────────────────────────────────────────

async def _go_to_parts(callback, state: FSMContext, edit: bool = True):
    all_parts = await utils.get_all_quiz_parts()
    data = await state.get_data()
    selected = data.get('ss_selected_parts', [])

    await state.update_data(ss_all_parts=all_parts)

    text = await get_text('ss_select_parts')
    markup = await inline_kb.ss_parts_markup(all_parts, selected)

    if edit:
        await callback.message.edit_text(text, reply_markup=markup)
    else:
        await callback.message.answer(text, reply_markup=markup)

    await state.set_state(ScheduledSessionState.select_parts)
    await callback.answer()


async def ss_part_toggle_handler(callback: types.CallbackQuery, state: FSMContext):
    part_id = int(callback.data.split('_')[-1])
    data = await state.get_data()
    selected = list(data.get('ss_selected_parts', []))

    if part_id in selected:
        selected.remove(part_id)
    else:
        selected.append(part_id)

    await state.update_data(ss_selected_parts=selected)

    all_parts = data.get('ss_all_parts', [])
    markup = await inline_kb.ss_parts_markup(all_parts, selected)
    await callback.message.edit_reply_markup(reply_markup=markup)
    await callback.answer()


async def ss_parts_none_handler(callback: types.CallbackQuery, state: FSMContext):
    text = await get_text('ss_select_at_least_one')
    await callback.answer(text, show_alert=True)


async def ss_parts_done_handler(callback: types.CallbackQuery, state: FSMContext):
    text = await get_text('ss_select_date')
    markup = await inline_kb.ss_date_markup()
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduledSessionState.select_date)
    await callback.answer()


# ── Создание: шаг 3 — дата ───────────────────────────────────────────────────

async def ss_date_selected_handler(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split('_')[-1]
    await state.update_data(ss_date=date_str)

    text = await get_text('ss_select_time')
    await callback.message.edit_text(text)
    await state.set_state(ScheduledSessionState.select_time)
    await callback.answer()


# ── Создание: шаг 4 — время ──────────────────────────────────────────────────

async def ss_time_entered_handler(message: types.Message, state: FSMContext):
    time_str = message.text.strip()

    if not re.match(r'^([01]?\d|2[0-3]):[0-5]\d$', time_str):
        text = await get_text('ss_time_invalid')
        return await message.answer(text)

    data = await state.get_data()
    date_str = data.get('ss_date', '')

    try:
        day, month, year = map(int, date_str.split('.'))
        hour, minute = map(int, time_str.split(':'))
        local_dt = _TZ.localize(datetime(year, month, day, hour, minute))
        now_utc = datetime.now(dt_timezone.utc)
        if local_dt.astimezone(dt_timezone.utc) <= now_utc:
            text = await get_text('ss_time_in_past')
            return await message.answer(text)
    except Exception:
        text = await get_text('ss_time_invalid')
        return await message.answer(text)

    await state.update_data(ss_time=time_str)
    await _show_confirmation(message, data, date_str, time_str)
    await state.set_state(ScheduledSessionState.confirm)


async def _show_confirmation(message: types.Message, data: dict, date_str: str, time_str: str):
    group_title = data.get('ss_group_title') or data.get('ss_group_id', '')
    all_parts = data.get('ss_all_parts', [])
    selected_ids = data.get('ss_selected_parts', [])

    parts_lines = [
        f"  • {p['quiz_title']} → [{p['from_i']} - {p['to_i']}]"
        for p in all_parts if p['id'] in selected_ids
    ]
    parts_text = '\n'.join(parts_lines) if parts_lines else '—'

    text = await get_text('ss_confirm_text', {
        'group': group_title,
        'parts': parts_text,
        'date': date_str,
        'time': time_str,
    })
    markup = await inline_kb.ss_confirm_markup()
    await message.answer(text, reply_markup=markup)


# ── Создание: подтверждение ───────────────────────────────────────────────────

async def ss_confirm_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    data = await state.get_data()

    date_str = data['ss_date']
    time_str = data['ss_time']
    day, month, year = map(int, date_str.split('.'))
    hour, minute = map(int, time_str.split(':'))

    local_dt = _TZ.localize(datetime(year, month, day, hour, minute))
    scheduled_at_utc = local_dt.astimezone(dt_timezone.utc)

    await utils.create_scheduled_session(
        created_by_id=user.id,
        group_id=data['ss_group_id'],
        group_title=data.get('ss_group_title', ''),
        part_ids=data.get('ss_selected_parts', []),
        scheduled_at=scheduled_at_utc,
    )

    text = await get_text('ss_created')
    await callback.message.edit_text(text)
    await state.clear()
    await callback.answer()


async def ss_cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    text = await get_text('ss_cancelled')
    await callback.message.edit_text(text)
    await state.clear()
    await callback.answer()


# ── Навигация назад ───────────────────────────────────────────────────────────

async def ss_back_to_groups_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    groups = data.get('ss_groups', [])
    text = await get_text('ss_select_group')
    markup = await inline_kb.ss_groups_markup(groups)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduledSessionState.select_group)
    await callback.answer()


async def ss_back_to_parts_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    all_parts = data.get('ss_all_parts', [])
    selected = data.get('ss_selected_parts', [])
    text = await get_text('ss_select_parts')
    markup = await inline_kb.ss_parts_markup(all_parts, selected)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduledSessionState.select_parts)
    await callback.answer()


async def ss_back_to_time_handler(callback: types.CallbackQuery, state: FSMContext):
    text = await get_text('ss_select_time')
    await callback.message.edit_text(text)
    await state.set_state(ScheduledSessionState.select_time)
    await callback.answer()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_session(session_id: int):
    from asgiref.sync import sync_to_async
    from quiz.models import ScheduledSession

    return await sync_to_async(
        lambda: ScheduledSession.objects.select_related('created_by').filter(pk=session_id).first()
    )()


def _format_session_detail(session) -> str:
    from bot.utils.functions import get_text_sync
    local_dt = session.scheduled_at.astimezone(_TZ)
    status_key_map = {
        'pending': 'ss_status_pending',
        'running': 'ss_status_running',
        'completed': 'ss_status_completed',
        'cancelled': 'ss_status_cancelled',
    }
    status_text = get_text_sync(status_key_map.get(session.status, 'ss_status_pending'))
    return get_text_sync('ss_detail_text', {
        'id': str(session.pk),
        'group': session.group_title or session.group_id,
        'count': str(len(session.part_ids)),
        'date': local_dt.strftime('%d.%m.%Y'),
        'time': local_dt.strftime('%H:%M'),
        'status': status_text,
    })
