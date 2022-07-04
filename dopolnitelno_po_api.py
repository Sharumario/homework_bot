from pprint import pprint
import telegram
import logging
import requests
import os
import time

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TOKENS = ['TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN', 'PRACTICUM_TOKEN']
URL_API = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

def check_tokens():
    empty_tokens = [name for name in TOKENS if globals()[name] is None]
    if empty_tokens:
        print('Всё сломалось, всё пропало')
    return not empty_tokens

print(check_tokens())

params = {'from_date': 1652929250}
try:
    response = requests.get(URL_API, headers=HEADERS, params=params)
except requests.RequestException:
    print('Всё норм')
