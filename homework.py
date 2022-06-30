import logging
import os
import sys
import time

import requests
from telegram import Bot
from dotenv import load_dotenv

from exceptions import EmptyListError, EndPointError, MessageError, TokenError


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    filename='main.log',
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в telegramm."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except MessageError as error:
        logging.error(f'Сбой при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Запрос к API Яндекс практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code == 200:
        return (requests.get(ENDPOINT, headers=HEADERS, params=params)).json()
    else:
        raise EndPointError(
            f'Ошибка сети API: {homework_statuses.status_code}'
        )


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Неверный тип данных. Not dict')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('Неверный тип данных. Not list')
    if len(homework) == 0:
        raise EmptyListError('Список домашних заданий пустой!')
    return homework


def parse_status(homework):
    """Определение статуса ревью."""
    if not isinstance(homework, dict):
        raise TypeError('Ошибка! Неверный тип данных.')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if not homework_status and homework_name:
        raise KeyError(
            'Ошибка ключа! Не найдены данные: '
            'название спринта или статус спринта'
        )
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        raise KeyError(f'Ошибка ключа! Нет такого статуса ДЗ: {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия необходимых токенов."""
    TOKENS = {
        PRACTICUM_TOKEN: 'PRACTICUM_TOKEN',
        TELEGRAM_TOKEN: 'TELEGRAM_TOKEN',
        TELEGRAM_CHAT_ID: 'TELEGRAM_CHAT_ID',
    }
    for token, name_token in TOKENS.items():
        if not token:
            logging.critical(
                f'Нет обязательных переменных окружения: {name_token}')
            return False
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        raise TokenError('Ошибка токенов')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    cash_message_error = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                send_message(bot, parse_status(homework))
            logging.info('Успешная отправка сообщения')
            current_timestamp = int(time.time()) - RETRY_TIME
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if not cash_message_error:
                send_message(bot, message)
                cash_message_error = error
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
