import json
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils import timezone


# ── helpers ──────────────────────────────────────────────────────────────────

def _last_n_days(n):
    today = timezone.now().date()
    return [today - timedelta(days=i) for i in range(n - 1, -1, -1)]


def _day_label(d):
    return d.strftime("%d %b")


def _build_user_chart(days=14):
    from common.models import TelegramProfile

    since = timezone.now() - timedelta(days=days)
    qs = (
        TelegramProfile.objects
        .filter(created_at__gte=since)
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    counts = {row["day"].date(): row["count"] for row in qs}
    dates = _last_n_days(days)
    return json.dumps({
        "labels": [_day_label(d) for d in dates],
        "datasets": [{
            "label": "New Users",
            "data": [counts.get(d, 0) for d in dates],
            "borderColor": "rgb(99, 102, 241)",
            "backgroundColor": "rgba(99, 102, 241, 0.08)",
            "tension": 0.4,
            "fill": True,
            "pointRadius": 3,
        }],
    })


def _build_quiz_activity_chart(days=14):
    from quiz.models import UserQuiz

    since = timezone.now() - timedelta(days=days)
    qs = (
        UserQuiz.objects
        .filter(created_at__gte=since)
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    counts = {row["day"].date(): row["count"] for row in qs}
    dates = _last_n_days(days)
    return json.dumps({
        "labels": [_day_label(d) for d in dates],
        "datasets": [{
            "label": "Quiz Sessions",
            "data": [counts.get(d, 0) for d in dates],
            "backgroundColor": "rgba(16, 185, 129, 0.7)",
            "borderColor": "rgb(16, 185, 129)",
            "borderRadius": 4,
        }],
    })


def _build_userquiz_status_chart():
    from quiz.models import UserQuiz
    from quiz.choices import QuizStatus

    labels = []
    data = []
    colors = ["#6366F1", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
    for i, (value, label) in enumerate(QuizStatus.choices):
        labels.append(label)
        data.append(UserQuiz.objects.filter(status=value).count())
    return json.dumps({
        "labels": labels,
        "datasets": [{
            "data": data,
            "backgroundColor": colors[: len(labels)],
            "borderWidth": 0,
        }],
    })


def _build_support_status_chart():
    from support.models import SupportMessage
    from support.choices import SupportMessageStatus

    labels = []
    data = []
    colors = ["#F59E0B", "#10B981", "#EF4444"]
    for i, (value, label) in enumerate(SupportMessageStatus.choices):
        labels.append(label)
        data.append(SupportMessage.objects.filter(status=value).count())
    return json.dumps({
        "labels": labels,
        "datasets": [{
            "data": data,
            "backgroundColor": colors[: len(labels)],
            "borderWidth": 0,
        }],
    })


def _build_recent_users(limit=5):
    from common.models import TelegramProfile
    from django.urls import reverse

    qs = TelegramProfile.objects.order_by("-created_at")[:limit]
    return [
        {
            "name": p.first_name + (f" {p.last_name}" if p.last_name else ""),
            "username": f"@{p.username}" if p.username else "—",
            "role": p.role,
            "registered": p.is_registered,
            "url": reverse("admin:common_telegramprofile_change", args=[p.pk]),
        }
        for p in qs
    ]


def _build_recent_support(limit=5):
    from support.models import SupportMessage
    from support.choices import SupportMessageStatus
    from django.urls import reverse

    qs = SupportMessage.objects.filter(
        status=SupportMessageStatus.PENDING
    ).select_related("owner").order_by("-created_at")[:limit]
    return [
        {
            "question": m.question[:60] + ("…" if len(m.question) > 60 else ""),
            "owner": str(m.owner),
            "date": m.created_at.strftime("%d %b, %H:%M"),
            "url": reverse("admin:support_supportmessage_change", args=[m.pk]),
        }
        for m in qs
    ]


def _build_upcoming_sessions(limit=5):
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus
    from django.urls import reverse

    now = timezone.now()
    qs = ScheduledSession.objects.filter(
        status__in=[SessionStatus.PENDING, SessionStatus.RUNNING],
        scheduled_at__gte=now,
    ).order_by("scheduled_at")[:limit]
    return [
        {
            "group_title": s.group_title or s.group_id,
            "scheduled_at": s.scheduled_at.strftime("%d %b %Y, %H:%M"),
            "status": s.status,
            "url": reverse("admin:quiz_scheduledsession_change", args=[s.pk]),
        }
        for s in qs
    ]


# ── main callback ─────────────────────────────────────────────────────────────

def dashboard_callback(request, context):
    from common.models import TelegramProfile, TelegramGroup
    from quiz.models import UserQuiz, GroupQuiz, Quiz, Question, ScheduledSession
    from support.models import SupportMessage
    from quiz.choices import QuizStatus, SessionStatus
    from support.choices import SupportMessageStatus

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    total_users = TelegramProfile.objects.count()
    new_today = TelegramProfile.objects.filter(created_at__date=today).count()
    new_this_week = TelegramProfile.objects.filter(created_at__date__gte=week_ago).count()
    registered_users = TelegramProfile.objects.filter(is_registered=True).count()

    active_quizzes = UserQuiz.objects.filter(status=QuizStatus.STARTED).count()
    finished_quizzes = UserQuiz.objects.filter(status=QuizStatus.FINISHED).count()
    total_quizzes = Quiz.objects.count()
    total_questions = Question.objects.count()

    group_sessions = GroupQuiz.objects.count()
    active_groups = TelegramGroup.objects.filter(is_active=True).count()

    pending_support = SupportMessage.objects.filter(status=SupportMessageStatus.PENDING).count()
    resolved_support = SupportMessage.objects.filter(status=SupportMessageStatus.RESOLVED).count()

    upcoming_sessions = ScheduledSession.objects.filter(
        status__in=[SessionStatus.PENDING, SessionStatus.RUNNING],
        scheduled_at__gte=timezone.now(),
    ).count()

    context["kpi"] = [
        {
            "title": "Total Users",
            "metric": total_users,
            "footer": f"+{new_today} today · +{new_this_week} this week",
            "icon": "person",
        },
        {
            "title": "Registered Users",
            "metric": registered_users,
            "footer": f"{total_users - registered_users} not registered",
            "icon": "how_to_reg",
        },
        {
            "title": "Active Quizzes",
            "metric": active_quizzes,
            "footer": f"{finished_quizzes} finished total",
            "icon": "history_edu",
        },
        {
            "title": "Total Quizzes",
            "metric": total_quizzes,
            "footer": f"{total_questions} questions",
            "icon": "quiz",
        },
        {
            "title": "Group Sessions",
            "metric": group_sessions,
            "footer": f"{active_groups} active groups",
            "icon": "groups",
        },
        {
            "title": "Pending Support",
            "metric": pending_support,
            "footer": f"{resolved_support} resolved total",
            "icon": "support_agent",
        },
        {
            "title": "Scheduled Sessions",
            "metric": upcoming_sessions,
            "footer": "upcoming (pending/running)",
            "icon": "schedule",
        },
    ]

    context["user_chart_data"] = _build_user_chart(14)
    context["quiz_chart_data"] = _build_quiz_activity_chart(14)
    context["userquiz_status_chart"] = _build_userquiz_status_chart()
    context["support_status_chart"] = _build_support_status_chart()

    context["recent_users"] = _build_recent_users(5)
    context["recent_support"] = _build_recent_support(5)
    context["upcoming_sessions"] = _build_upcoming_sessions(5)

    return context


# ── navigation badges ─────────────────────────────────────────────────────────

def badge_new_users(request):
    from common.models import TelegramProfile

    today = timezone.now().date()
    count = TelegramProfile.objects.filter(created_at__date=today).count()
    return str(count) if count else None


def badge_pending_support(request):
    from support.models import SupportMessage
    from support.choices import SupportMessageStatus

    count = SupportMessage.objects.filter(status=SupportMessageStatus.PENDING).count()
    return str(count) if count else None
