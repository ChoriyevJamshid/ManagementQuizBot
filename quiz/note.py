import os
import time
from docx import Document
import pandas as pd
from string import ascii_letters, digits


def docx_operate(file_path: str):
    data = []
    document = Document(file_path)
    table = document.tables[0]
    for row in table.rows:
        question = row.cells[0].text
        correct_answer = row.cells[1].text
        options = (
            row.cells[1].text,
            row.cells[2].text,
            row.cells[3].text,
            row.cells[4].text,
        )
        data.append({
            'question': question,
            'correct_answer': correct_answer,
            'options': options,
        })
    return data


# docx_operate("C:\\Users\\qpq77\\OneDrive\\Desktop\\test_quiz.docx")

def xlsx_operate(file_path: str):
    data = []

    # Загружаем Excel-файл
    df = pd.read_excel(file_path, engine="openpyxl", usecols=[0, 1, 2, 3, 4], header=None)

    for _, row in df.iterrows():
        # Проверяем, есть ли пустые значения и заменяем их на пустую строку
        row = row.fillna("")

        question = row.iloc[0]  # Вопрос
        correct_answer = row.iloc[1]  # Правильный ответ
        options = (
            row.iloc[1],  # Правильный ответ в списке вариантов
            row.iloc[2],
            row.iloc[3],
            row.iloc[4],
        )

        data.append({
            'question': question,
            'correct_answer': correct_answer,
            'options': options,
        })
    print(data)
    return data


def txt_operate(file_path: str):
    data = []
    current_question = {"options": []}
    with open(file_path, "r", encoding="utf-8") as f:
        for index, row in enumerate(f.readlines(), start=1):
            text = row.strip()

            if text == '':
                continue

            question = current_question.get('question', None)
            if question is None:
                current_question['question'] = text
                continue

            correct_answer = current_question.get('correct_answer', None)
            if correct_answer is None:
                current_question['correct_answer'] = text

            current_question['options'].append(text)

            if len(current_question.get('options', [])) == 4:
                data.append(current_question)
                current_question = {"options": []}

# file_path = "C:\\Users\\qpq77\\OneDrive\\Desktop\\test_quiz.docx"
# st = time.perf_counter()
# data = docx_operate(file_path)
# en = time.perf_counter()
# print(len(data))
# print(f"File size: {os.path.getsize(file_path) / 1024 ** 2}")
# print(f"Time: {en - st}")


if __name__ == "__main__":
    # players = {
    #     1: {"corrects": 7, "username": "player_1", "spent_time": 23.5},
    #     2: {"corrects": 3, "username": "player_2", "spent_time": 42.8},
    #     3: {"corrects": 9, "username": "player_3", "spent_time": 15.4},
    #     4: {"corrects": 6, "username": "player_4", "spent_time": 33.2},
    #     5: {"corrects": 8, "username": "player_5", "spent_time": 12.1},
    #     6: {"corrects": 4, "username": "player_6", "spent_time": 28.9},
    #     7: {"corrects": 10, "username": "player_7", "spent_time": 7.8},
    #     8: {"corrects": 5, "username": "player_8", "spent_time": 36.7},
    #     9: {"corrects": 2, "username": "player_9", "spent_time": 49.3},
    #     10: {"corrects": 7, "username": "player_10", "spent_time": 19.6},
    #     11: {"corrects": 9, "username": "player_11", "spent_time": 21.0},
    #     12: {"corrects": 1, "username": "player_12", "spent_time": 55.9},
    #     13: {"corrects": 6, "username": "player_13", "spent_time": 25.4},
    #     14: {"corrects": 3, "username": "player_14", "spent_time": 41.1},
    #     15: {"corrects": 5, "username": "player_15", "spent_time": 37.5},
    #     16: {"corrects": 8, "username": "player_16", "spent_time": 10.9},
    #     17: {"corrects": 10, "username": "player_17", "spent_time": 6.5},
    #     18: {"corrects": 7, "username": "player_18", "spent_time": 24.3},
    #     19: {"corrects": 4, "username": "player_19", "spent_time": 31.7},
    #     20: {"corrects": 6, "username": "player_20", "spent_time": 29.4},
    #     21: {"corrects": 8, "username": "player_21", "spent_time": 13.3},
    #     22: {"corrects": 2, "username": "player_22", "spent_time": 50.0},
    #     23: {"corrects": 9, "username": "player_23", "spent_time": 17.9},
    #     24: {"corrects": 5, "username": "player_24", "spent_time": 39.8},
    #     25: {"corrects": 7, "username": "player_25", "spent_time": 20.0},
    #     26: {"corrects": 10, "username": "player_26", "spent_time": 9.2},
    #     27: {"corrects": 3, "username": "player_27", "spent_time": 47.6},
    #     28: {"corrects": 4, "username": "player_28", "spent_time": 35.2},
    #     29: {"corrects": 6, "username": "player_29", "spent_time": 30.1},
    #     30: {"corrects": 8, "username": "player_30", "spent_time": 11.8},
    #     31: {"corrects": 1, "username": "player_31", "spent_time": 59.4},
    #     32: {"corrects": 9, "username": "player_32", "spent_time": 18.2},
    #     33: {"corrects": 5, "username": "player_33", "spent_time": 38.6},
    #     34: {"corrects": 6, "username": "player_34", "spent_time": 26.7},
    #     35: {"corrects": 7, "username": "player_35", "spent_time": 22.1},
    #     36: {"corrects": 4, "username": "player_36", "spent_time": 34.5},
    #     37: {"corrects": 2, "username": "player_37", "spent_time": 51.3},
    #     38: {"corrects": 3, "username": "player_38", "spent_time": 44.4},
    #     39: {"corrects": 5, "username": "player_39", "spent_time": 40.6},
    #     40: {"corrects": 9, "username": "player_40", "spent_time": 14.2},
    #     41: {"corrects": 10, "username": "player_41", "spent_time": 8.6},
    #     42: {"corrects": 7, "username": "player_42", "spent_time": 21.7},
    #     43: {"corrects": 6, "username": "player_43", "spent_time": 27.3},
    #     44: {"corrects": 4, "username": "player_44", "spent_time": 32.5},
    #     45: {"corrects": 8, "username": "player_45", "spent_time": 12.7},
    #     46: {"corrects": 5, "username": "player_46", "spent_time": 36.1},
    #     47: {"corrects": 3, "username": "player_47", "spent_time": 45.2},
    #     48: {"corrects": 2, "username": "player_48", "spent_time": 53.0},
    #     49: {"corrects": 1, "username": "player_49", "spent_time": 58.3},
    #     50: {"corrects": 10, "username": "player_50", "spent_time": 7.1},
    # }
    #
    # # Сортировка: сначала по убыванию corrects, потом по возрастанию spent_time
    # st = time.perf_counter()
    # sorted_players = sorted(players.items(), key=lambda item: (-item[1]['corrects'], item[1]['spent_time']))
    # end = time.perf_counter()
    # # Вывод результата
    #
    # print(sorted_players)
    ""

    numbers = 46.8
    print(numbers // 60)
    print(round(numbers % 60, 2))


