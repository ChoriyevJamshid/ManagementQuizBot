from django.utils import timezone


def dashboard_callback(request, context):
    from common.models import TelegramProfile
    from quiz.models import UserQuiz, GroupQuiz, Quiz, Question
    from support.models import SupportMessage
    from quiz.choices import QuizStatus
    from support.choices import SupportMessageStatus

    today = timezone.now().date()

    total_users = TelegramProfile.objects.count()
    new_today = TelegramProfile.objects.filter(created_at__date=today).count()
    active_quizzes = UserQuiz.objects.filter(status=QuizStatus.STARTED).count()
    finished_quizzes = UserQuiz.objects.filter(status=QuizStatus.FINISHED).count()
    total_quizzes = Quiz.objects.count()
    total_questions = Question.objects.count()
    group_sessions = GroupQuiz.objects.count()
    pending_support = SupportMessage.objects.filter(status=SupportMessageStatus.PENDING).count()

    context["kpi"] = [
        {
            "title": "Total Users",
            "metric": total_users,
            "footer": f"+{new_today} new today",
        },
        {
            "title": "Active Quizzes",
            "metric": active_quizzes,
            "footer": f"{finished_quizzes} finished total",
        },
        {
            "title": "Total Quizzes",
            "metric": total_quizzes,
            "footer": f"{total_questions} questions",
        },
        {
            "title": "Group Sessions",
            "metric": group_sessions,
            "footer": "all time",
        },
        {
            "title": "Pending Support",
            "metric": pending_support,
            "footer": "awaiting reply",
        },
    ]

    return context


def badge_new_users(request):
    from common.models import TelegramProfile
    from django.utils import timezone

    today = timezone.now().date()
    count = TelegramProfile.objects.filter(created_at__date=today).count()
    return str(count) if count else None


def badge_pending_support(request):
    from support.models import SupportMessage
    from support.choices import SupportMessageStatus

    count = SupportMessage.objects.filter(status=SupportMessageStatus.PENDING).count()
    return str(count) if count else None
