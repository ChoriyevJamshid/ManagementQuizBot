from aiogram import Router, F
from aiogram.filters import Command, CommandStart, or_f

from bot.filters import *

from bot.handlers.users.main import *
from bot.handlers.users.create_quizzes import *
from bot.handlers.users.instruction import *
from bot.handlers.users.quizzes import *
from bot.handlers.users.testing import *
from bot.handlers.users.inline_mode import *


def prepare_router() -> Router:
    router = Router()
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    router.message.filter(RegisteredFilter())
    router.callback_query.filter(RegisteredFilter())

    # message handlers
    router.message.register(cancel_handler, Command('cancel'))

    # main.py
    """
    Handler from main.py 
    """

    router.callback_query.register(
        main_menu_handler,
        MainState.main_menu
    )

    # create_quiz.py
    router.message.register(
        create_quiz_get_title_handler,
        F.content_type == types.ContentType.TEXT,
        CreateQuizState.title,
    )

    router.message.register(
        create_quiz_get_file_handler,
        F.content_type.in_({types.ContentType.TEXT, types.ContentType.DOCUMENT}),
        CreateQuizState.file
    )

    router.message.register(
        create_quiz_get_quantity_handler,
        CreateQuizState.check,
    )

    router.message.register(
        create_quiz_get_timer_handler,
        CreateQuizState.timer,
    )

    router.message.register(
        create_quiz_save_handler,
        CreateQuizState.save,
    )

    router.message.register(
        get_user_contact_handler,
        MainState.share_contact
    )

    # quizzes.py
    """
        Handler from quizzes.py 
    """

    router.callback_query.register(
        quiz_list_handler,
        F.data == "menu-quizzes"

    )

    router.message.register(
        quiz_list_timer_edit_success_handler,
        QuizState.update_timer
    )

    router.callback_query.register(
        quiz_list_paginate_handler,
        F.data.startswith('quiz-list-paginate'),
        QuizState.quizzes
    )

    router.callback_query.register(
        quiz_list_detail_handler,
        F.data.startswith('quiz-list-detail'),
        QuizState.quizzes
    )

    router.callback_query.register(
        quiz_list_back_to_main_menu_handler,
        F.data == 'back-to-main-menu',
    )

    router.callback_query.register(
        quiz_list_handler,
        F.data == "quiz-list-back-user-quizzes",
        QuizState.quizzes
    )

    router.callback_query.register(
        quiz_list_edit_timer_handler,
        F.data.startswith('quiz-list-edit-timer'),
    )

    router.callback_query.register(
        quiz_list_edit_privacy_handler,
        F.data.startswith('quiz-list-edit-privacy'),
    )

    router.callback_query.register(
        quiz_list_change_privacy_handler,
        F.data.startswith('quiz-list-changed-privacy'),
    )

    # testing.py
    """
        Handler from testing.py 
    """

    router.message.register(
        testing_stop_quiz_handler,
        Command('stop'),
    )

    router.message.register(
        testing_link_handler,
        F.text.startswith("/quiz"),
    )

    router.callback_query.register(
        testing_start_pressed_handler,
        F.data.startswith('testing-start-pressed'),
    )

    router.callback_query.register(
        testing_ready_pressed_handler,
        F.data.startswith("testing-ready-pressed")
    )

    router.callback_query.register(
        testing_continue_quiz_handler,
        F.data.startswith("testing-continue-quiz"),
        QuizState.testing,
    )

    router.callback_query.register(
        testing_try_retry_handler,
        F.data.startswith("testing-try-quiz-retry"),
        QuizState.finished
    )

    router.poll_answer.register(
        testing_poll_answer_handler,
        QuizState.testing,
    )

    # instruction
    """
        Handler from instruction.py 
    """

    router.callback_query.register(
        instruction_file_type_handler,
        F.data.startswith("instruction-file-type"),
        MainState.instruction,
    )

    router.callback_query.register(
        instruction_back_to_instruction,
        F.data == "back-to-instruction",
        MainState.instruction,
    )

    # inline_mode.py
    """
        Handler from inline_mode.py 
    """

    router.inline_query.register(
        testing_inline_query,
        F.query.startswith("share-quiz")
    )

    # commands
    router.message.register(
        start_handler,
        CommandStart(),
        CancelFilter(testing_link_handler)
    )

    router.message.register(
        help_handler,
        Command('help')
    )

    #delete handler
    router.message.register(delete_message_handler)
    router.callback_query.register(delete_callback_handler)

    return router
