# import pandas as pd
#
# def reform_spent_time(spent_time: float | int):
#     """
#     spent_time: float | int - this argument get time on types: int, float
#     """
#
#     formatted_text = str()
#     minutes = spent_time // 60
#     seconds = round(spent_time % 60, 2)
#
#     if minutes > 0:
#         formatted_text += f"{minutes} min "
#     formatted_text += f"{seconds} sec"
#     return formatted_text
#
# data = {
#     "players": {"263578897": {"wrongs": 10, "corrects": 10, "username": "Урмонов Шермухаммад", "spent_time": 581.6},
#                 "308071638": {"wrongs": 7, "corrects": 8, "username": "22-maktab direktori: X. Otaliqov",
#                               "spent_time": 488.5},
#                 "496131446": {"wrongs": 4, "corrects": 13, "username": "Анвар Кенжебаевич",
#                               "spent_time": 623.0999999999999},
#                 "627742561": {"wrongs": 5, "corrects": 12, "username": "Asilbek Jumabayev", "spent_time": 591.7},
#                 "700648099": {"wrongs": 11, "corrects": 7, "username": "Олтиной", "spent_time": 543.5999999999999},
#                 "730979653": {"wrongs": 2, "corrects": 16, "username": "Hurliman Embergenova",
#                               "spent_time": 471.9000000000001},
#                 "781117438": {"wrongs": 7, "corrects": 12, "username": "Махсетбай", "spent_time": 606.1},
#                 "914558318": {"wrongs": 3, "corrects": 13, "username": "Nargiza", "spent_time": 496.49999999999994},
#                 "923173161": {"wrongs": 8, "corrects": 9, "username": "Усманова", "spent_time": 637.1999999999999},
#                 "5686251936": {"wrongs": 2, "corrects": 16, "username": "@ALBAA2218", "spent_time": 474.5},
#                 "6020535055": {"wrongs": 4, "corrects": 15, "username": "Yunus", "spent_time": 655.0},
#                 "6037368260": {"wrongs": 4, "corrects": 12, "username": "@Azamat_Ataxanovich",
#                                "spent_time": 515.0000000000001},
#                 "6677810273": {"wrongs": 5, "corrects": 7, "username": "Xurshidaxon", "spent_time": 397.90000000000003},
#                 "7837432893": {"wrongs": 0, "corrects": 0, "username": "Teacher", "spent_time": 0},
#                 "7965896578": {"wrongs": 7, "corrects": 7, "username": "Барнохон", "spent_time": 436.99999999999994}},
#     "start_time": 3208622.305057992, "correct_option_id": 2}
#
# players = data.get("players")

# cols_name = {
#         'name': {
#             'en': "Full Name",
#             'uz': "FIO",
#             'ru': "ФИО"
#         },
#         'corrects': {
#             'en': "Corrects",
#             'uz': "To‘g‘ri javoblar",
#             'ru': "Правильные ответы"
#         },
#         'wrongs': {
#             'en': "Wrongs",
#             'uz': "Noto‘g‘ri javoblar",
#             'ru': "Неправильные ответы"
#         },
#         'spent_time': {
#             'en': "Spend Time",
#             'uz': "Sarf qilingan vaqt",
#             'ru': "Затраченное время"
#         },
#         'percent': {
#             'en': "Percent",
#             'uz': "Foiz",
#             'ru': "Процент"
#         }
#
#     }

import os

base_dir = "/home/jamshid/PyDir/Bots/FileToQuizBotV3/media"
files = os.listdir(base_dir)

for file in files:
    extension = file.split(".")[-1]
    if extension in ("xlsx", "xls", "doc", "docx", "txt"):
        if os.path.exists(f"{base_dir}/{file}"):
            os.remove(f"{base_dir}/{file}")
            print(f"File {file} deleted")





