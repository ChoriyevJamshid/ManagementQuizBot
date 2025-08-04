# import json
# import orjson
# import os
# import time
# import psycopg2 as sql
# from bs4 import BeautifulSoup

# my_dict = {}
# for i in range(10000):
#     my_dict[f"my_code_{i}"] = {
#         'uz': f'uz {"text" * 100} {i}',
#         'ru': f'ru {"text" * 100} {i}',
#         'en': f'en {"text" * 100} {i}',
#     }
#
# with open(f"../trush/langs.json", 'wb') as f:
#     f.write(orjson.dumps(my_dict, option=4))

# st = time.perf_counter()
# with open("../trush/langs.json", "rb") as f:  # Открываем в бинарном режиме
#     data = orjson.loads(f.read())
#
# en = time.perf_counter()
# # print(f"Text: {text1}")
# print(f"Time: {round(en - st, 3)}")


# with open("t.json", mode='w', encoding='utf-8') as f:
#     json.dump()


m_d = {
    'a': 'a',
    'b': 'b',
}

print(len(m_d))
