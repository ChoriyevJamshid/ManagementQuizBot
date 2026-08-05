import os
import asyncio
import logging
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from quiz.models import GroupQuiz, Quiz

from bot.utils.methods import get_chat, send_text
from bot.utils.functions import create_excel_statistics, get_texts_sync, get_text_sync
from quiz.choices import QuizStatus

logger = logging.getLogger(__name__)


@shared_task
def get_group_invite_link(pk: int):

    group = GroupQuiz.objects.filter(pk=pk).first()
    if group is None:
        return None

    response = get_chat(chat_id=int(group.group_id))
    if response.status_code == 200:
        data = response.json()
        group.invite_link = data.get('result', {}).get('invite_link')
        group.save(update_fields=['invite_link'])
        return group.invite_link

    return None


@shared_task
def group_quiz_create_file(
        quiz_id: int,
        sorted_players: list | tuple,
        quantity: int,
        timer: int = 0,
):
    quiz = GroupQuiz.objects.filter(pk=quiz_id).first()
    if not quiz:
        return None

    if quiz.file:
        return None

    file_bytes = create_excel_statistics(
        sorted_players=sorted_players,
        quantity=quantity,
        timer=timer,
    )

    quiz.file.save("statistics.xlsx", ContentFile(file_bytes), save=False)
    quiz.save(update_fields=['file', 'updated_at'])

    return None


@shared_task
def cleanup_stale_group_quizzes():
    import redis as _sync_redis
    from django.utils import timezone
    from quiz.models import GroupQuiz as GQ
    from quiz.choices import QuizStatus

    # Grace period: a GroupQuiz sits in INIT/STARTED with no Redis "active" key
    # for a short, expected window right after creation — up to ~10s waiting
    # for a second player (manual /start) plus the ~3s start_group_testing
    # animation, before `set_quiz_active` actually runs. Without this cutoff a
    # cleanup tick landing in that window would cancel a quiz that is genuinely
    # just starting. 60s is comfortably above that worst case.
    grace_cutoff = timezone.now() - timezone.timedelta(seconds=60)

    # `group_quiz:{pk}:active` is set once with an 86400s TTL and is only ever
    # *deleted* by the loop's own natural-finish/stop path — nothing refreshes
    # it and nothing clears it if the process running the quiz crashes. So its
    # mere presence does NOT mean "still running": a STARTED quiz whose worker
    # died would read as active for up to 24h. `updated_at` is the actual
    # heartbeat — every question sent bumps it via
    # `group_quiz.asave(update_fields=["poll_id", "index"])` in send_question.
    heartbeat_cutoff = timezone.now() - timezone.timedelta(seconds=300)

    rows = list(
        GQ.objects.filter(
            status__in=[QuizStatus.STARTED, QuizStatus.INIT],
            created_at__lt=grace_cutoff,
        ).values('pk', 'status', 'updated_at')
    )
    if not rows:
        return

    _r = _sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        stale_pks = []
        for row in rows:
            pk = row['pk']
            active_in_redis = _r.exists(f"group_quiz:{pk}:active") == 1
            if not active_in_redis:
                stale_pks.append(pk)
            elif row['status'] == QuizStatus.STARTED and row['updated_at'] < heartbeat_cutoff:
                # Redis still thinks it's active, but nothing has touched this
                # quiz in 5+ minutes — the process running it is gone.
                stale_pks.append(pk)
        if not stale_pks:
            return

        GQ.objects.filter(pk__in=stale_pks).update(status=QuizStatus.CANCELED)

        for pk in stale_pks:
            _r.delete(
                f"group_quiz:{pk}:players",
                f"group_quiz:{pk}:scores",
                f"group_quiz:{pk}:wrongs",
                f"group_quiz:{pk}:times",
                f"group_quiz:{pk}:usernames",
                f"group_quiz:{pk}:current",
                f"group_quiz:{pk}:questions",
                f"group_quiz:{pk}:active",
                f"group_quiz:{pk}:answered",
                f"group_quiz:{pk}:skip_count",
            )
        logger.warning("cleanup_stale_group_quizzes: cancelled %d stale records: %s", len(stale_pks), stale_pks)
    finally:
        _r.close()


@shared_task
def remove_quiz_files():
    base_dir = settings.MEDIA_ROOT
    files = os.listdir(base_dir)

    for file in files:
        extension = file.split(".")[-1]
        if extension in ("xlsx", "xls", "doc", "docx", "txt"):
            if os.path.exists(f"{base_dir}/{file}"):
                os.remove(f"{base_dir}/{file}")

    return None


# ── Daily / Weekly statistics tasks ──────────────────────────────────────────

@shared_task
def send_daily_group_stats():
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    groups = _collect_group_stats(since=now - timedelta(hours=24))
    header = get_text_sync('daily_stats_header', {'date': now.strftime('%d.%m.%Y')})
    _dispatch_group_stats(groups, header)


@shared_task
def send_weekly_group_stats():
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    since = now - timedelta(days=7)
    groups = _collect_group_stats(since=since)
    week_str = f"{since.strftime('%d.%m.%Y')} – {now.strftime('%d.%m.%Y')}"
    header = get_text_sync('weekly_stats_header', {'week': week_str})
    _dispatch_group_stats(groups, header)


def _collect_group_stats(since) -> dict:
    finished_quizzes = (
        GroupQuiz.objects
        .filter(
            status=QuizStatus.FINISHED,
            updated_at__gte=since,
            data__isnull=False,
        )
        .values('group_id', 'data')
    )
    groups: dict = {}
    for quiz in finished_quizzes:
        group_id = quiz['group_id']
        players = (quiz['data'] or {}).get('players', {})
        group_agg = groups.setdefault(group_id, {})
        for user_id, stats in players.items():
            if user_id not in group_agg:
                group_agg[user_id] = {
                    'username': stats.get('username', 'Unknown'),
                    'corrects': 0,
                    'wrongs': 0,
                    'spent_time': 0.0,
                }
            entry = group_agg[user_id]
            entry['corrects'] += stats.get('corrects', 0)
            entry['wrongs'] += stats.get('wrongs', 0)
            entry['spent_time'] += stats.get('spent_time', 0.0)
    return groups


def _dispatch_group_stats(groups: dict, header: str) -> None:
    for group_id, players in groups.items():
        sorted_players = sorted(
            players.items(),
            key=lambda item: (
                -(item[1]['corrects'] / (item[1]['corrects'] + item[1]['wrongs'])
                  if (item[1]['corrects'] + item[1]['wrongs']) > 0 else 0.0),
                -item[1]['corrects'],
                item[1]['spent_time'],
            ),
        )[:20]
        text = header + "\n\n" + _build_daily_stats_rows(sorted_players)
        send_text(chat_id=int(group_id), text=text)


def _build_daily_stats_rows(players: list) -> str:
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    rows = []
    for rank, (_, stats) in enumerate(players, 1):
        total = stats['corrects'] + stats['wrongs']
        accuracy = round(stats['corrects'] / total * 100) if total else 0
        hours = int(stats['spent_time'] // 3600)
        mins = int((stats['spent_time'] % 3600) // 60)
        secs = int(stats['spent_time'] % 60)
        prefix = medals.get(rank, "🔸")
        rows.append(
            f"{prefix} {rank}. {stats['username']} — {stats['corrects']} ball\n"
            f"       (Javoblar: {total}, Aniqlik: {accuracy}%, Vaqt: {hours:02d}:{mins:02d}:{secs:02d})"
        )
    return "\n".join(rows)


# ── Scheduled Session tasks ───────────────────────────────────────────────────

@shared_task
def notify_scheduled_session(session_id: int, label: str):
    import redis as _sync_redis
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    # Idempotency guard: if multiple worker threads picked up this task due to
    # visibility_timeout cycling, only the first one actually sends the message.
    _r = _sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        lock_key = f"session:{session_id}:notified:{label}"
        acquired = _r.set(lock_key, '1', nx=True, ex=86400)
        if not acquired:
            logger.info(
                "notify_scheduled_session: session=%d label=%s already sent — skipping duplicate",
                session_id, label,
            )
            return
    finally:
        _r.close()

    session = ScheduledSession.objects.filter(
        pk=session_id, status=SessionStatus.PENDING
    ).first()
    if not session:
        return

    key_map = {'1h': 'schedule_notify_1h', '10m': 'schedule_notify_10m', '5m': 'schedule_notify_5m'}
    text_key = key_map.get(label)
    if not text_key:
        return

    text = get_text_sync(text_key)
    send_text(chat_id=int(session.group_id), text=text)


# One quiz part's worst case: 35 questions * (120s timer + 2s gap) ≈ 71 min.
# Give it a wide margin above that instead of hardcoding the exact bound.
_PART_HARD_TIMEOUT = 5400  # 90 min

# Gap between parts. Also used as the countdown for scheduling the next part.
_INTER_PART_PAUSE = 120

# Sentinel returned by _launch_one_part to mean "this part was already fully
# completed by an earlier (crashed/redelivered) attempt — advance past it",
# as distinct from `None` which means "stop, don't schedule anything further"
# (session cancelled / fatal error). Do not conflate the two.
_PART_ALREADY_DONE = object()


@shared_task(acks_late=True, reject_on_worker_lost=True)
def start_scheduled_session(session_id: int):
    """
    Launches part 0 of a ScheduledSession.

    `acks_late` + `reject_on_worker_lost`: if the celery worker process dies
    (crash, OOM, restart on deploy) while this task is executing, the broker
    redelivers it instead of silently losing it — this is what closes the
    "session stuck in RUNNING forever" gap the previous single-3h-task design
    had. Redelivery is safe because `_run_session_part` checks
    `session.current_part_index` before doing any work (see below) and
    `_launch_one_part` recognizes its own already-created GroupQuiz instead of
    blindly resending the part.
    """
    _run_session_part(session_id, expected_part_index=0)


@shared_task(acks_late=True, reject_on_worker_lost=True)
def continue_scheduled_session(session_id: int, part_index: int):
    """Launches one later part of a ScheduledSession. See start_scheduled_session."""
    _run_session_part(session_id, expected_part_index=part_index)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _run_session_part(session_id: int, expected_part_index: int) -> None:
    """
    Sync entry point: one short-lived event loop per part (not per session).
    Keeps the "single loop while this part runs" property that avoids
    "Future attached to a different loop" errors, without tying up one
    Celery task — and one worker thread — for the entire multi-hour session.
    """
    import redis.asyncio as aioredis
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from bot.utils import redis_group
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    async def _run():
        # Fresh Redis client for this event loop, scoped via contextvars so it
        # never leaks into (or gets clobbered by) another ScheduledSession
        # running concurrently in a different worker thread. See
        # bot/utils/redis_group.py for why a plain module attribute is unsafe
        # under --pool=threads.
        session_redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        redis_token = redis_group.bind_redis_client(session_redis_client)
        bot = Bot(
            token=settings.API_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            await asyncio.wait_for(
                _run_one_part(session_id, expected_part_index, bot),
                timeout=_PART_HARD_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Session %d part %d: timed out after %ds — cancelling",
                session_id, expected_part_index, _PART_HARD_TIMEOUT,
            )
            ScheduledSession.objects.filter(
                pk=session_id,
                status__in=[SessionStatus.PENDING, SessionStatus.RUNNING],
            ).update(status=SessionStatus.CANCELLED, active_group_quiz_id=None)
        finally:
            await bot.session.close()
            await session_redis_client.aclose()
            redis_group.unbind_redis_client(redis_token)

    try:
        asyncio.run(_run())
    except Exception:
        logger.exception("Session %d part %d: unhandled exception", session_id, expected_part_index)
        ScheduledSession.objects.filter(
            pk=session_id,
            status__in=[SessionStatus.PENDING, SessionStatus.RUNNING],
        ).update(status=SessionStatus.CANCELLED, active_group_quiz_id=None)


async def _run_one_part(session_id: int, expected_part_index: int, bot) -> None:
    """
    Runs exactly one quiz part, then either schedules the next part (durable
    resume-point saved first) or marks the session COMPLETED.
    """
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    session = await (
        ScheduledSession.objects
        .select_related('created_by')
        .filter(pk=session_id)
        .afirst()
    )
    if not session:
        logger.warning("Session %d not found", session_id)
        return
    if session.status == SessionStatus.CANCELLED:
        logger.info("Session %d already cancelled — skipping part %d", session_id, expected_part_index)
        return

    # Redelivery / stale-eta guard: this part was already advanced past by an
    # earlier (successful) run of this exact task. Nothing to do.
    if session.current_part_index != expected_part_index:
        logger.info(
            "Session %d: part %d already processed (current_part_index=%d) — skipping duplicate delivery",
            session_id, expected_part_index, session.current_part_index,
        )
        return

    part_ids = session.part_ids
    if not part_ids or expected_part_index >= len(part_ids):
        await ScheduledSession.objects.filter(pk=session_id).aupdate(status=SessionStatus.COMPLETED)
        return

    if session.status == SessionStatus.PENDING:
        updated = await ScheduledSession.objects.filter(
            pk=session_id, status=SessionStatus.PENDING
        ).aupdate(status=SessionStatus.RUNNING)
        if not updated:
            # Another worker already claimed this session (concurrent redelivery race).
            logger.info("Session %d: not in PENDING state — skipping duplicate worker", session_id)
            return
        session = await ScheduledSession.objects.select_related('created_by').filter(pk=session_id).afirst()

    part_id = part_ids[expected_part_index]
    group_quiz = await _launch_one_part(session, expected_part_index, part_id, bot)

    if group_quiz is _PART_ALREADY_DONE:
        # Crashed/redelivered attempt: this part fully finished before, only
        # the resume-point save didn't make it. Still need to advance —
        # falling through to `return` here would leave current_part_index
        # stuck forever with nothing left to schedule the next part.
        logger.info(
            "Session %d part %d: already completed by an earlier attempt — advancing without replay",
            session_id, expected_part_index,
        )
        await _advance_to_next_part(session_id, session, expected_part_index, part_ids)
        return

    if group_quiz is None:
        # _launch_one_part already resolved a terminal outcome: session was
        # cancelled (foreign quiz blocked it / part not found / another
        # worker is genuinely still processing this same part).
        return

    await ScheduledSession.objects.filter(pk=session_id).aupdate(active_group_quiz_id=group_quiz.pk)

    from bot.handlers.groups.testing import start_group_testing
    completed_normally = await start_group_testing(group_quiz=group_quiz, bot=bot)

    await ScheduledSession.objects.filter(
        pk=session_id, active_group_quiz_id=group_quiz.pk
    ).aupdate(active_group_quiz_id=None)

    # An explicit cancel (ss_cancel_session_handler) during this part flips
    # status away from RUNNING immediately (and stops the live quiz loop via
    # Redis) — re-check here so we don't schedule a next part after that.
    current_status = await (
        ScheduledSession.objects.filter(pk=session_id).values_list('status', flat=True).afirst()
    )
    if not completed_normally or current_status != SessionStatus.RUNNING:
        logger.info("Session %d part %d: stopped/cancelled — not scheduling further parts", session_id, expected_part_index)
        await ScheduledSession.objects.filter(
            pk=session_id, status=SessionStatus.RUNNING
        ).aupdate(status=SessionStatus.CANCELLED)
        return

    await _advance_to_next_part(session_id, session, expected_part_index, part_ids)


async def _advance_to_next_part(session_id: int, session, expected_part_index: int, part_ids: list) -> None:
    """Persists the resume-point and either schedules the next part or marks the session COMPLETED."""
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    next_index = expected_part_index + 1

    if next_index >= len(part_ids):
        await ScheduledSession.objects.filter(
            pk=session_id, status=SessionStatus.RUNNING, current_part_index=expected_part_index
        ).aupdate(status=SessionStatus.COMPLETED, current_part_index=next_index)
        logger.info("Session %d: all parts completed", session_id)
        return

    logger.info(
        "Session %d: part %d done, scheduling part %d in %ds",
        session_id, expected_part_index, next_index, _INTER_PART_PAUSE,
    )
    task = continue_scheduled_session.apply_async(
        kwargs={"session_id": session_id, "part_index": next_index},
        countdown=_INTER_PART_PAUSE,
    )
    # Persist the resume-point *and* the new task id together, only after the
    # continuation is durably queued in the broker — this ordering is what
    # makes the resume-point trustworthy for the redelivery guard above.
    updated_ids = list(session.celery_task_ids) + [task.id]
    await ScheduledSession.objects.filter(
        pk=session_id, current_part_index=expected_part_index
    ).aupdate(current_part_index=next_index, celery_task_ids=updated_ids)


async def _launch_one_part(session, part_index: int, part_id: int, bot):
    """
    Prepares and starts one quiz part inside the running event loop.

    Returns one of:
      - a ready (STARTED) GroupQuiz — proceed to start_group_testing;
      - `_PART_ALREADY_DONE` — nothing to launch, but the caller must still
        advance past this part (it already completed in an earlier attempt);
      - `None` — stop; nothing more should be scheduled (session cancelled,
        part not found, or a duplicate run bailing out).
    """
    from django.utils import timezone
    from quiz.models import GroupQuiz as GQ, QuizPart
    from quiz.choices import QuizStatus
    from bot.utils import redis_group

    def _is_genuinely_live(group_quiz_obj, is_active_in_redis: bool, stale_after: float) -> bool:
        # `group_quiz:{pk}:active` is set once at start with an 86400s TTL and
        # is only ever *deleted* by the loop's own natural-finish/stop path —
        # nothing refreshes it, and nothing clears it on a hard crash. So on
        # its own it cannot tell "still running" apart from "the process that
        # was running this died hours ago" — it would read as active for up
        # to 24h either way. `updated_at` is a real heartbeat instead: every
        # question sent calls `group_quiz.asave(update_fields=["poll_id", "index"])`
        # (see send_question in bot/handlers/groups/testing.py), so a process
        # that's actually alive keeps bumping it every `timer` seconds.
        if not is_active_in_redis:
            return False
        age = (timezone.now() - group_quiz_obj.updated_at).total_seconds()
        return age <= stale_after

    quiz_part = await (
        QuizPart.objects
        .prefetch_related('questions', 'questions__options')
        .select_related('quiz')
        .filter(pk=part_id)
        .afirst()
    )
    if not quiz_part:
        logger.error(
            "Session %d part_index=%d: QuizPart pk=%s not found — cancelling session",
            session.pk, part_index, part_id,
        )
        await _cancel_session_blocked(session.pk, session.group_id)
        return None

    # Our own record for this exact (session, part_index) — set if a previous
    # (possibly crashed/redelivered) attempt at this same part already got as
    # far as creating a GroupQuiz. Distinguishes "retry my own part" from
    # "a foreign quiz is blocking this group" below.
    own_record = await (
        GQ.objects
        .filter(scheduled_session_id=session.pk, session_part_index=part_index)
        .order_by('-id')
        .afirst()
    )

    if own_record:
        if own_record.status == QuizStatus.FINISHED:
            # This part already ran to completion in an earlier attempt whose
            # progress-save just didn't make it before the worker died. The
            # caller must still advance current_part_index — signal that with
            # the sentinel rather than plain None (see its definition).
            logger.info(
                "Session %d part %d: already FINISHED (GroupQuiz pk=%d) — skipping re-launch",
                session.pk, part_index, own_record.pk,
            )
            return _PART_ALREADY_DONE
        if own_record.status == QuizStatus.STARTED:
            is_active = await redis_group.get_redis_client().exists(f"group_quiz:{own_record.pk}:active") == 1
            # Precise threshold: we know this part's own timer.
            still_live = _is_genuinely_live(own_record, is_active, stale_after=quiz_part.quiz.timer + 60)
            if still_live:
                # Genuinely still running elsewhere (a concurrent redelivery
                # while the original run is still healthy) — a plain None
                # here is correct: don't schedule a duplicate continuation
                # while the other run is still in flight.
                logger.warning(
                    "Session %d part %d: own GroupQuiz pk=%d still live — skipping duplicate run",
                    session.pk, part_index, own_record.pk,
                )
                return None
            logger.warning(
                "Session %d part %d: own GroupQuiz pk=%d STARTED but stale (worker likely crashed) — retrying part",
                session.pk, part_index, own_record.pk,
            )
            await _cleanup_stale_group_quiz(own_record.pk)
        # else CANCELED — fall through and relaunch fresh below.

    # Conflict check: a *foreign* quiz (manual /start, or a different session)
    # already active in this group blocks us from starting.
    existing = await GQ.objects.filter(
        group_id=session.group_id
    ).exclude(status__in=[QuizStatus.FINISHED, QuizStatus.CANCELED]).afirst()

    if existing:
        if existing.status == QuizStatus.STARTED:
            is_active = await redis_group.get_redis_client().exists(f"group_quiz:{existing.pk}:active") == 1
            # We don't know the foreign quiz's own timer without another
            # query; 5 min of silence is a safe "definitely dead" bar for any
            # quiz configuration (max timer is 2 min).
            still_live = _is_genuinely_live(existing, is_active, stale_after=300)
            if not still_live:
                logger.warning(
                    "Session %d part %d: foreign GroupQuiz pk=%d STARTED but stale — cleaning up",
                    session.pk, part_index, existing.pk,
                )
                await _cleanup_stale_group_quiz(existing.pk)
                # Fall through to start normally
            else:
                logger.warning(
                    "Session %d part %d: active GroupQuiz pk=%d exists — cancelling session",
                    session.pk, part_index, existing.pk,
                )
                await _cancel_session_blocked(session.pk, session.group_id)
                return None
        else:
            logger.warning(
                "Session %d part %d: GroupQuiz pk=%d status=%s exists — cancelling session",
                session.pk, part_index, existing.pk, existing.status,
            )
            await _cancel_session_blocked(session.pk, session.group_id)
            return None

    # Send "part ready" info to the group
    text = get_text_sync('testing_group_quiz_part_ready_info', {
        "from_i": str(quiz_part.from_i),
        "to_i": str(quiz_part.to_i),
        "quantity": str(quiz_part.quantity),
        "timer": str(quiz_part.quiz.timer),
        "title": str(quiz_part.title or quiz_part.quiz.title),
    })
    response = send_text(chat_id=int(session.group_id), text=text)
    if response.status_code != 200:
        logger.error(
            "Session %d part %d: sendMessage failed: %s %s",
            session.pk, part_index, response.status_code, response.text,
        )
        return None

    message_id = str(response.json()['result']['message_id'])
    group_quiz = await GQ.objects.acreate(
        part=quiz_part,
        user=session.created_by,
        group_id=session.group_id,
        message_id=message_id,
        title=session.group_title or '',
        invite_link='',
        poll_id='',
        scheduled_session=session,
        session_part_index=part_index,
    )

    starts_text = get_text_sync('group_quiz_starts_in_10_sec')
    send_text(chat_id=int(session.group_id), text=starts_text)

    # Transition INIT → STARTED
    updated = await GQ.objects.filter(
        pk=group_quiz.pk, status=QuizStatus.INIT
    ).aupdate(status=QuizStatus.STARTED)
    if not updated:
        logger.error(
            "Session %d part %d: failed to transition GroupQuiz pk=%d to STARTED",
            session.pk, part_index, group_quiz.pk,
        )
        return None

    # Return fully prefetched STARTED record for start_group_testing
    return await (
        GQ.objects
        .prefetch_related('part__questions', 'part__questions__options')
        .select_related('part', 'part__quiz', 'user')
        .filter(pk=group_quiz.pk, status=QuizStatus.STARTED)
        .afirst()
    )


async def _cleanup_stale_group_quiz(pk: int) -> None:
    """Cancels a stale (STARTED-in-DB but not active-in-Redis) GroupQuiz and wipes its Redis state."""
    from quiz.models import GroupQuiz as GQ
    from quiz.choices import QuizStatus
    from bot.utils import redis_group

    stale_pk = str(pk)
    await GQ.objects.filter(pk=pk).aupdate(status=QuizStatus.CANCELED)
    await redis_group.get_redis_client().delete(
        f"group_quiz:{stale_pk}:players",
        f"group_quiz:{stale_pk}:scores",
        f"group_quiz:{stale_pk}:wrongs",
        f"group_quiz:{stale_pk}:times",
        f"group_quiz:{stale_pk}:usernames",
        f"group_quiz:{stale_pk}:current",
        f"group_quiz:{stale_pk}:questions",
        f"group_quiz:{stale_pk}:active",
        f"group_quiz:{stale_pk}:answered",
        f"group_quiz:{stale_pk}:skip_count",
    )


async def _cancel_session_blocked(session_id: int, group_id: str) -> None:
    """Marks session CANCELLED when an existing quiz blocks the start."""
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    updated = await ScheduledSession.objects.filter(
        pk=session_id,
        status__in=[SessionStatus.PENDING, SessionStatus.RUNNING],
    ).aupdate(status=SessionStatus.CANCELLED, active_group_quiz_id=None)

    if updated:
        text = get_text_sync('ss_cancelled_due_to_active_quiz')
        send_text(chat_id=int(group_id), text=text)
