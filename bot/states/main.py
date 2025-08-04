from aiogram.fsm.state import State, StatesGroup


class MainState(StatesGroup):
    main_menu = State()
    choose_language = State()
    instruction = State()
    categories = State()
    share_contact = State()

    admin = State()
    admin_write = State()

class CreateQuizState(StatesGroup):
    title = State()
    category = State()
    file = State()
    timer = State()
    check = State()
    save = State()


class QuizState(StatesGroup):
    quizzes = State()
    testing = State()
    group_testing = State()
    finished = State()
    admin_test = State()
    update_timer = State()
    update_privacy = State()


class SupportState(StatesGroup):
    support = State()
    writeToAdmin = State()
    addCategoryTitle = State()


