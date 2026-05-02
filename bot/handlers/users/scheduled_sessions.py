import logging
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

logger = logging.getLogger(__name__)
_TZ = pytz.timezone('Asia/Tashkent')
_SS_PAGE_SIZE = 10


def _build_parts_message(
    page_parts: list,
    selected_ids: list,
    page: int,
    total_pages: int,
) -> str:
    lines = ["📚 <b>Quiz qismlarini tanlang:</b>\n"]
    for i, part in enumerate(page_parts):
        global_num = page * _SS_PAGE_SIZE + i + 1
        mark = "✅" if part['id'] in selected_ids else "☐"
        lines.append(
            f"{mark} <b>{global_num}.</b> {part['quiz_title']} "
            f"→ [{part['from_i']} - {part['to_i']}]"
        )
    if total_pages > 1:
        lines.append(f"\n<i>Sahifa {page + 1} / {total_pages}</i>")
    return "\n".join(lines)


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

    logger.info("ss_create: user_id=%s started schedule creation", callback.from_user.id)

    groups = await utils.get_distinct_groups()
    logger.info("ss_create: user_id=%s fetched %d groups", callback.from_user.id, len(groups))

    await state.update_data(ss_groups=groups, ss_selected_parts=[])

    text = await get_text('ss_select_group')
    markup = await inline_kb.ss_groups_markup(groups)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduledSessionState.select_group)
    await callback.answer()


async def ss_group_selected_handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(
        "ss_group_selected: user_id=%s callback_data=%r",
        callback.from_user.id, callback.data,
    )

    try:
        idx = int(callback.data.split('_')[-1])
    except (ValueError, IndexError):
        logger.warning(
            "ss_group_selected: user_id=%s failed to parse idx from callback_data=%r",
            callback.from_user.id, callback.data,
        )
        await callback.answer("⚠️ Noto'g'ri ma'lumot.", show_alert=True)
        return

    data = await state.get_data()
    groups = data.get('ss_groups', [])

    logger.info(
        "ss_group_selected: user_id=%s idx=%d groups_count=%d state_keys=%s",
        callback.from_user.id, idx, len(groups), list(data.keys()),
    )

    if not groups:
        logger.warning(
            "ss_group_selected: user_id=%s ss_groups is empty — FSM state likely lost",
            callback.from_user.id,
        )
        text = await get_text('ss_state_expired')
        await callback.answer(text, show_alert=True)
        return

    if idx >= len(groups):
        logger.warning(
            "ss_group_selected: user_id=%s idx=%d out of range (groups_count=%d)",
            callback.from_user.id, idx, len(groups),
        )
        await callback.answer()
        return

    group = groups[idx]
    logger.info(
        "ss_group_selected: user_id=%s selected group_id=%s title=%r",
        callback.from_user.id, group['group_id'], group.get('title'),
    )

    await state.update_data(
        ss_group_id=group['group_id'],
        ss_group_title=group.get('title') or group['group_id'],
    )

    try:
        await _go_to_parts(callback, state)
    except Exception:
        logger.exception(
            "ss_group_selected: user_id=%s exception in _go_to_parts", callback.from_user.id,
        )
        await callback.answer("⚠️ Xatolik yuz berdi.", show_alert=True)


async def ss_group_manual_handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info("ss_group_manual: user_id=%s chose manual group_id entry", callback.from_user.id)
    text = await get_text('ss_enter_group_id')
    await callback.message.edit_text(text)
    await state.set_state(ScheduledSessionState.enter_group_id)
    await callback.answer()


async def ss_group_id_entered_handler(message: types.Message, state: FSMContext):
    group_id = message.text.strip()
    logger.info("ss_group_id_entered: user_id=%s entered group_id=%r", message.from_user.id, group_id)

    if not re.match(r'^-?\d+$', group_id):
        logger.warning("ss_group_id_entered: user_id=%s invalid group_id=%r", message.from_user.id, group_id)
        text = await get_text('ss_group_id_invalid')
        return await message.answer(text)

    await state.update_data(ss_group_id=group_id, ss_group_title=group_id)
    logger.info("ss_group_id_entered: user_id=%s saved group_id=%s, proceeding to parts", message.from_user.id, group_id)

    class _FakeCallback:
        def __init__(self, msg):
            self.message = msg
        async def answer(self, *args, **kwargs): pass

    try:
        await _go_to_parts(_FakeCallback(message), state, edit=False)
    except Exception:
        logger.exception("ss_group_id_entered: user_id=%s exception in _go_to_parts", message.from_user.id)
        await message.answer("⚠️ Xatolik yuz berdi.")


# ── Создание: шаг 2 — части квиза ────────────────────────────────────────────

async def _go_to_parts(callback, state: FSMContext, edit: bool = True, page: int = 0):
    all_parts = await utils.get_all_quiz_parts()
    data = await state.get_data()
    selected = data.get('ss_selected_parts', [])

    total_pages = max(1, (len(all_parts) + _SS_PAGE_SIZE - 1) // _SS_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_parts = all_parts[page * _SS_PAGE_SIZE: (page + 1) * _SS_PAGE_SIZE]

    logger.info(
        "_go_to_parts: all_parts_count=%d selected_count=%d page=%d total_pages=%d",
        len(all_parts), len(selected), page, total_pages,
    )

    await state.update_data(ss_all_parts=all_parts, ss_parts_page=page)

    text = _build_parts_message(page_parts, selected, page, total_pages)
    markup = await inline_kb.ss_parts_markup(
        page_parts, selected, page, total_pages,
        start_index=page * _SS_PAGE_SIZE,
    )

    if edit:
        await callback.message.edit_text(text, reply_markup=markup)
    else:
        await callback.message.answer(text, reply_markup=markup)

    await state.set_state(ScheduledSessionState.select_parts)
    await callback.answer()


async def ss_part_toggle_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        part_id = int(callback.data.split('_')[-1])
    except (ValueError, IndexError):
        logger.warning(
            "ss_part_toggle: user_id=%s failed to parse part_id from callback_data=%r",
            callback.from_user.id, callback.data,
        )
        await callback.answer()
        return

    data = await state.get_data()
    selected = list(data.get('ss_selected_parts', []))
    page = data.get('ss_parts_page', 0)

    if part_id in selected:
        selected.remove(part_id)
    else:
        selected.append(part_id)

    logger.info(
        "ss_part_toggle: user_id=%s part_id=%d selected_count=%d selected=%s",
        callback.from_user.id, part_id, len(selected), selected,
    )

    await state.update_data(ss_selected_parts=selected)

    all_parts = data.get('ss_all_parts', [])
    total_pages = max(1, (len(all_parts) + _SS_PAGE_SIZE - 1) // _SS_PAGE_SIZE)
    page_parts = all_parts[page * _SS_PAGE_SIZE: (page + 1) * _SS_PAGE_SIZE]

    text = _build_parts_message(page_parts, selected, page, total_pages)
    markup = await inline_kb.ss_parts_markup(
        page_parts, selected, page, total_pages,
        start_index=page * _SS_PAGE_SIZE,
    )
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


async def ss_parts_page_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        page = int(callback.data.split('_')[-1])
    except (ValueError, IndexError):
        logger.warning(
            "ss_parts_page: user_id=%s failed to parse page from callback_data=%r",
            callback.from_user.id, callback.data,
        )
        await callback.answer()
        return

    logger.info("ss_parts_page: user_id=%s navigating to page=%d", callback.from_user.id, page)

    data = await state.get_data()
    all_parts = data.get('ss_all_parts', [])
    selected = data.get('ss_selected_parts', [])

    total_pages = max(1, (len(all_parts) + _SS_PAGE_SIZE - 1) // _SS_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_parts = all_parts[page * _SS_PAGE_SIZE: (page + 1) * _SS_PAGE_SIZE]

    await state.update_data(ss_parts_page=page)

    text = _build_parts_message(page_parts, selected, page, total_pages)
    markup = await inline_kb.ss_parts_markup(
        page_parts, selected, page, total_pages,
        start_index=page * _SS_PAGE_SIZE,
    )
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


async def ss_parts_noop_handler(callback: types.CallbackQuery):
    await callback.answer()


async def ss_parts_none_handler(callback: types.CallbackQuery, state: FSMContext):
    text = await get_text('ss_select_at_least_one')
    await callback.answer(text, show_alert=True)


async def ss_parts_done_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('ss_selected_parts', [])
    logger.info(
        "ss_parts_done: user_id=%s confirmed parts=%s", callback.from_user.id, selected,
    )
    text = await get_text('ss_select_date')
    markup = await inline_kb.ss_date_markup()
    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(ScheduledSessionState.select_date)
    await callback.answer()


# ── Создание: шаг 3 — дата ───────────────────────────────────────────────────

async def ss_date_selected_handler(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split('_')[-1]
    logger.info("ss_date_selected: user_id=%s date=%s", callback.from_user.id, date_str)
    await state.update_data(ss_date=date_str)

    text = await get_text('ss_select_time')
    await callback.message.edit_text(text)
    await state.set_state(ScheduledSessionState.select_time)
    await callback.answer()


# ── Создание: шаг 4 — время ──────────────────────────────────────────────────

async def ss_time_entered_handler(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    logger.info("ss_time_entered: user_id=%s time=%r", message.from_user.id, time_str)

    if not re.match(r'^([01]?\d|2[0-3]):[0-5]\d$', time_str):
        logger.warning("ss_time_entered: user_id=%s invalid time format=%r", message.from_user.id, time_str)
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
            logger.warning(
                "ss_time_entered: user_id=%s time is in the past date=%s time=%s",
                message.from_user.id, date_str, time_str,
            )
            text = await get_text('ss_time_in_past')
            return await message.answer(text)
    except Exception:
        logger.exception(
            "ss_time_entered: user_id=%s failed to parse date=%r time=%r",
            message.from_user.id, date_str, time_str,
        )
        text = await get_text('ss_time_invalid')
        return await message.answer(text)

    logger.info(
        "ss_time_entered: user_id=%s date=%s time=%s scheduled_at_local=%s",
        message.from_user.id, date_str, time_str, local_dt.isoformat(),
    )
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

    logger.info(
        "ss_confirm: user_id=%s group_id=%s group_title=%r parts=%s date=%s time=%s",
        callback.from_user.id,
        data.get('ss_group_id'),
        data.get('ss_group_title'),
        data.get('ss_selected_parts'),
        data.get('ss_date'),
        data.get('ss_time'),
    )

    try:
        date_str = data['ss_date']
        time_str = data['ss_time']
        day, month, year = map(int, date_str.split('.'))
        hour, minute = map(int, time_str.split(':'))

        local_dt = _TZ.localize(datetime(year, month, day, hour, minute))
        scheduled_at_utc = local_dt.astimezone(dt_timezone.utc)

        session = await utils.create_scheduled_session(
            created_by_id=user.id,
            group_id=data['ss_group_id'],
            group_title=data.get('ss_group_title', ''),
            part_ids=data.get('ss_selected_parts', []),
            scheduled_at=scheduled_at_utc,
        )

        logger.info(
            "ss_confirm: user_id=%s session created pk=%s scheduled_at_utc=%s task_ids=%s",
            callback.from_user.id, session.pk, scheduled_at_utc.isoformat(), session.celery_task_ids,
        )
    except Exception:
        logger.exception("ss_confirm: user_id=%s failed to create session", callback.from_user.id)
        await callback.answer("⚠️ Jadval yaratishda xatolik yuz berdi.", show_alert=True)
        return

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
    page = data.get('ss_parts_page', 0)

    total_pages = max(1, (len(all_parts) + _SS_PAGE_SIZE - 1) // _SS_PAGE_SIZE)
    page_parts = all_parts[page * _SS_PAGE_SIZE: (page + 1) * _SS_PAGE_SIZE]

    text = _build_parts_message(page_parts, selected, page, total_pages)
    markup = await inline_kb.ss_parts_markup(
        page_parts, selected, page, total_pages,
        start_index=page * _SS_PAGE_SIZE,
    )
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
