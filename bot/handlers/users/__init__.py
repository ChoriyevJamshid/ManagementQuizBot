from aiogram import Router, F
from aiogram.filters import Command, CommandStart, or_f

from bot.filters import *

from bot.handlers.users.main import *
from bot.handlers.users.create_quizzes import *
from bot.handlers.users.instruction import *
from bot.handlers.users.quizzes import *
from bot.handlers.users.testing import *
from bot.handlers.users.inline_mode import *
from bot.handlers.users.categories import *
from bot.handlers.users.support import *


def prepare_router() -> Router:
    router = Router()
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    # message handlers
    router.message.register(cancel_handler, Command('cancel'))

    # support.py
    """
        Handlers from support.py
    """


    router.callback_query.register(
        support_appeal_to_admin_menu_handler,
        F.data == 'support-appeal-to-admin-menu'
    )

    router.callback_query.register(
        support_handler,
        F.data == "support-back-to-support-menu"
    )

    router.callback_query.register(
        support_appeal_to_admin_handler,
        F.data.startswith('support-appeal-to-admin'),
    )

    router.callback_query.register(
        support_mark_message_as_read_handler,
        F.data.startswith('support-mark-message-as-read'),
    )

    router.message.register(
        support_get_new_message_handler,
        SupportState.writeToAdmin
    )


    router.callback_query.register(
        support_add_category_handler,
        F.data == 'support-add-new-category'
    )

    router.message.register(
        support_add_category_title_handler,
        SupportState.addCategoryTitle
    )

    router.callback_query.register(
        support_testing_questions_file_handler,
        F.data == 'support-testing-questions-file'
    )



    # main.py
    """
        Handler from main.py 
    """

    router.callback_query.register(
        choose_language_handler,
        MainState.choose_language,
        F.data.startswith("choose-language")
    )

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
        create_quiz_get_category_handler,
        CreateQuizState.category,
    )

    router.message.register(
        create_quiz_get_file_handler,
        F.content_type.in_({types.ContentType.TEXT, types.ContentType.DOCUMENT}),
        CreateQuizState.file
    )

    router.message.register(
        create_quiz_get_timer_handler,
        CreateQuizState.timer,
    )

    router.message.register(
        create_quiz_save_handler,
        CreateQuizState.save,
    )

    # quizzes.py
    """
        Handler from quizzes.py 
    """

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
        or_f(Command('stopQuiz'), Command('stop')),
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

    # categories
    """
        Handler from categories.py 
    """

    router.callback_query.register(
        categories_handler,
        F.data == "categories-back-to-categories"
    )

    router.callback_query.register(
        categories_detail_handler,
        F.data.startswith("categories-list"),
    )

    router.callback_query.register(
        categories_paginate_handler,
        F.data.startswith("categories-quizzes-paginate")
    )

    router.callback_query.register(
        categories_detail_quiz_handler,
        F.data.startswith("categories-quizzes-detail")
    )

    router.callback_query.register(
        categories_back_to_quizzes_handler,
        F.data.startswith("categories-back-to-quizzes")
    )

    router.callback_query.register(
        categories_detail_quiz_part_handler,
        F.data.startswith("categories-quizzes-parts")
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
