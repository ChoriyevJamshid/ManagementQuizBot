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
    from quiz.models import GroupQuiz as GQ
    from quiz.choices import QuizStatus

    candidates = list(
        GQ.objects.filter(
            status__in=[QuizStatus.STARTED, QuizStatus.INIT]
        ).values_list('pk', flat=True)
    )
    if not candidates:
        return

    _r = _sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        stale_pks = [
            pk for pk in candidates
            if not _r.exists(f"group_quiz:{pk}:active")
        ]
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


# ── Daily statistics task ─────────────────────────────────────────────────────

@shared_task
def send_daily_group_stats():
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    since = now - timedelta(hours=24)

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

    date_str = now.strftime('%d.%m.%Y')
    header = get_text_sync('daily_stats_header', {'date': date_str})

    for group_id, players in groups.items():
        # if len(players) < 5:
        #     continue

        sorted_players = sorted(
            players.items(),
            key=lambda item: (
                -(item[1]['corrects'] + item[1]['wrongs']),
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
        score = (stats['corrects'] ** 2) / total if total else 0.0
        mins = int(stats['spent_time'] // 60)
        secs = int(stats['spent_time'] % 60)
        prefix = medals.get(rank, f"{rank}.")
        rows.append(
            f"{prefix} {stats['username']} — {score:.1f} ball"
            f" ({stats['corrects']}/{total}) | ⏱ {mins}:{secs:02d}"
        )
    return "\n".join(rows)


# ── Scheduled Session tasks ───────────────────────────────────────────────────

@shared_task
def notify_scheduled_session(session_id: int, label: str):
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

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


@shared_task
def start_scheduled_session(session_id: int):
    """
    Single long-running Celery task for the entire ScheduledSession.
    Runs all quiz parts sequentially inside one asyncio.run() call,
    which keeps a single event loop (and Redis client) alive for the
    whole session — no "Future attached to a different loop" errors.

    Note: soft_time_limit/time_limit are not used because --pool=threads
    ignores SIGALRM-based limits. Timeout is enforced via asyncio.wait_for
    inside _run_session instead.
    """
    _run_session(session_id)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _run_session(session_id: int) -> None:
    """Sync entry point: creates one event loop for the entire session."""
    import redis.asyncio as aioredis
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from bot.utils import redis_group
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    async def _run():
        # Fresh Redis client for this event loop — module-level client may be
        # tied to a different (bot process) loop.
        redis_group.redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        bot = Bot(
            token=settings.API_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            # 3-hour hard cap via asyncio — works with any Celery pool type.
            await asyncio.wait_for(_run_all_parts(session_id, bot), timeout=10800)
        except asyncio.TimeoutError:
            logger.error("Session %d: timed out after 3 hours — cancelling", session_id)
            ScheduledSession.objects.filter(
                pk=session_id,
                status__in=[SessionStatus.PENDING, SessionStatus.RUNNING],
            ).update(status=SessionStatus.CANCELLED)
        finally:
            await bot.session.close()
            await redis_group.redis_client.aclose()

    try:
        asyncio.run(_run())
    except Exception:
        logger.exception("Session %d: unhandled exception", session_id)
        ScheduledSession.objects.filter(
            pk=session_id,
            status__in=[SessionStatus.PENDING, SessionStatus.RUNNING],
        ).update(status=SessionStatus.CANCELLED)


async def _run_all_parts(session_id: int, bot) -> None:
    """
    Async main loop: iterates over all quiz parts of a session.
    Runs entirely inside a single asyncio.run() — no new loops created.
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
        logger.info("Session %d already cancelled before start", session_id)
        return

    part_ids = session.part_ids
    if not part_ids:
        await ScheduledSession.objects.filter(pk=session_id).aupdate(status=SessionStatus.COMPLETED)
        return

    await ScheduledSession.objects.filter(
        pk=session_id, status=SessionStatus.PENDING
    ).aupdate(status=SessionStatus.RUNNING)
    # Re-fetch so session.status is current for the rest of the function
    session = await ScheduledSession.objects.select_related('created_by').filter(pk=session_id).afirst()

    for part_index, part_id in enumerate(part_ids):
        # Cancellation guard before every part
        current_status = await (
            ScheduledSession.objects
            .filter(pk=session_id)
            .values_list('status', flat=True)
            .afirst()
        )
        if current_status == SessionStatus.CANCELLED:
            logger.info("Session %d: cancelled before part %d", session_id, part_index)
            return

        group_quiz = await _launch_one_part(session, part_index, part_id, bot)
        if group_quiz is None:
            # _launch_one_part already set status to CANCELLED
            return

        from bot.handlers.groups.testing import start_group_testing
        completed_normally = await start_group_testing(group_quiz=group_quiz, bot=bot)

        if not completed_normally:
            logger.info("Session %d part %d: stopped via /stop", session_id, part_index)
            await ScheduledSession.objects.filter(
                pk=session_id, status=SessionStatus.RUNNING
            ).aupdate(status=SessionStatus.CANCELLED)
            return

        # Pause 120 s between parts; skip after last part
        if part_index < len(part_ids) - 1:
            logger.info(
                "Session %d: part %d done, waiting 120 s before part %d",
                session_id, part_index, part_index + 1,
            )
            still_active = await _sleep_interruptible(session_id, 120)
            if not still_active:
                logger.info("Session %d: cancelled during inter-part pause", session_id)
                return

    await ScheduledSession.objects.filter(
        pk=session_id, status=SessionStatus.RUNNING
    ).aupdate(status=SessionStatus.COMPLETED)
    logger.info("Session %d: all parts completed", session_id)


async def _sleep_interruptible(session_id: int, total_seconds: int) -> bool:
    """
    Sleep for total_seconds, polling DB status every 5 s.
    Returns True if sleep finished normally, False if session was cancelled.
    """
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    elapsed = 0
    chunk = 5
    while elapsed < total_seconds:
        await asyncio.sleep(min(chunk, total_seconds - elapsed))
        elapsed += chunk
        status = await (
            ScheduledSession.objects
            .filter(pk=session_id)
            .values_list('status', flat=True)
            .afirst()
        )
        if status != SessionStatus.RUNNING:
            return False
    return True


async def _launch_one_part(session, part_index: int, part_id: int, bot) -> 'GroupQuiz | None':
    """
    Prepares and starts one quiz part inside the running event loop.
    Returns a ready (STARTED) GroupQuiz, or None on failure.
    """
    from quiz.models import GroupQuiz as GQ, QuizPart
    from quiz.choices import QuizStatus
    from bot.utils import redis_group

    quiz_part = await (
        QuizPart.objects
        .prefetch_related('questions', 'questions__options')
        .select_related('quiz')
        .filter(pk=part_id)
        .afirst()
    )
    if not quiz_part:
        logger.error(
            "Session %d part_index=%d: QuizPart pk=%s not found",
            session.pk, part_index, part_id,
        )
        return None

    # Check for any active GroupQuiz in this group
    existing = await GQ.objects.filter(
        group_id=session.group_id
    ).exclude(status__in=[QuizStatus.FINISHED, QuizStatus.CANCELED]).afirst()

    if existing:
        if existing.status == QuizStatus.STARTED:
            is_active = await redis_group.redis_client.exists(f"group_quiz:{existing.pk}:active") == 1
            if not is_active:
                # Stale STARTED record — clean up and proceed
                logger.warning(
                    "Session %d part %d: GroupQuiz pk=%d STARTED but stale — cleaning up",
                    session.pk, part_index, existing.pk,
                )
                stale_pk = str(existing.pk)
                await GQ.objects.filter(pk=existing.pk).aupdate(status=QuizStatus.CANCELED)
                await redis_group.redis_client.delete(
                    f"group_quiz:{stale_pk}:players",
                    f"group_quiz:{stale_pk}:scores",
                    f"group_quiz:{stale_pk}:wrongs",
                    f"group_quiz:{stale_pk}:times",
                    f"group_quiz:{stale_pk}:usernames",
                    f"group_quiz:{stale_pk}:current",
                    f"group_quiz:{stale_pk}:questions",
                    f"group_quiz:{stale_pk}:active",
                )
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


async def _cancel_session_blocked(session_id: int, group_id: str) -> None:
    """Marks session CANCELLED when an existing quiz blocks the start."""
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    updated = await ScheduledSession.objects.filter(
        pk=session_id,
        status__in=[SessionStatus.PENDING, SessionStatus.RUNNING],
    ).aupdate(status=SessionStatus.CANCELLED)

    if updated:
        text = get_text_sync('ss_cancelled_due_to_active_quiz')
        send_text(chat_id=int(group_id), text=text)
