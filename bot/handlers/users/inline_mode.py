from aiogram import types
from aiogram.fsm.context import FSMContext

from bot import utils
from bot.keyboards import inline_kb
from bot.utils.functions import get_text, get_texts



# async def share_inline_query(query: types.InlineQuery):
#     user = await get_user(query.from_user)
#     language = user.language if user.language else 'en'
#
#     result = types.InlineQueryResultArticle(
#         id=query.id,
#         title="Share to friend",
#         description="Share to friend to get more quotas.",
#         input_message_content=types.InputTextMessageContent(
#             message_text=text,
#             disable_web_page_preview=False
#         ),
#         reply_markup=await inline.invite_markup({
#             "text": f"⭐️ {settings.bot_username} ⭐️",
#             'username': settings.bot_username,
#             'chat_id': user.chat_id
#         })
#     )
#
#     await query.answer(results=[result], cache_time=0)
#     user.quota += 1
#     user.save(update_fields=['quota'])


async def testing_inline_query(query: types.InlineQuery):
    user = await utils.get_user(query.from_user)
    language = user.language if user.language else 'en'

    parameter = query.query.split('_')[-1]
    if parameter.isdigit():
        quiz_part = await utils.get_quiz_part_by_id(int(parameter))
    else:
        quiz_part = await utils.get_quiz_part(parameter)

    data_solo = await utils.get_data_solo()

    title = quiz_part.quiz.title
    quantity = quiz_part.quantity
    timer = quiz_part.quiz.timer

    text = await get_text("inline_mode_share_quiz", language, {
        "title": title,
        "quantity": str(quantity),
        "timer": str(timer),
    })

    markup = await inline_kb.inline_mode_share_quiz_markup(
        start_url=f"https://t.me/{data_solo.username}?start={quiz_part.link}",
        start_in_group_url=f"https://t.me/{data_solo.username}?startgroup={quiz_part.link}",
        parameter=parameter,
        language=language,
    )

    result = types.InlineQueryResultArticle(
        id=query.id,
        title="Share to friend",
        description="Share to friend the quiz test.",
        input_message_content=types.InputTextMessageContent(
            message_text=text,
            disable_web_page_preview=True
        ),
        reply_markup=markup
    )

    await query.answer(results=[result], cache_time=0)