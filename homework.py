import logging
import os
import time
import sys

import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

from exceptions import ServerError

load_dotenv()

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
SEND_MESSAGE = '"{message}": cообщение отправлено в чат!'
ERROR_SEND = 'Сбой при отправке сообщения: {error}'
CONNECTION_ERROR = ('Не удалось получить доступ к API. '
                    'Параметры запроса: {endpoint}, {headers}, {params}')
ERROR_API_RESPONSE = ('Неожиданный статус ответа API: {status_code}. '
                      'Параметры запроса: {endpoint}, {headers}, {params}.')
ERROR_RESPONSE = ('Неверный тип данных: {type_response}. '
                  'Ожидался словарь.')
ERROR_HOMEWORKS = ('Неверный тип данных: {type_homeworks}. '
                   'Ожидался список.')
ERROR_KEYS = 'В словаре нет ключа: homeworks'
ERROR_VERDICT = 'Неожиданное принятое значение вердикта: {verdict}}'
ERROR_TOKEN = 'Нет обязательной переменной окружения: {name}'
ERROR_TOKENS = 'Ошибка токенов'
ERROR_SERVER = 'Отказ обслуживания сети: {error}'
VERDICT = 'Изменился статус проверки работы "{name}". {verdict}'
ERROR_MAIN = 'Сбой в работе программы: {error}'


def send_message(bot, message):
    """Отправка сообщения в telegramm."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(SEND_MESSAGE.format(message=message))
    except TelegramError as error:
        raise TelegramError(ERROR_SEND.format(error=error))


def get_api_answer(current_timestamp):
    """Запрос к API Яндекс практикума."""
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.ConnectionError:
        raise requests.ConnectionError(
            CONNECTION_ERROR.format(
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params
            )
        )
    if homework_statuses.status_code != 200:
        raise ServerError(
            ERROR_API_RESPONSE.format(
                status_code=homework_statuses.status_code,
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params
            )
        )
    for field in ['error', 'code']:
        if field in homework_statuses.json():
            raise RuntimeError(
                ERROR_SERVER.format(error=homework_statuses.json()[field])
            )
    return homework_statuses.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            ERROR_RESPONSE.format(type_response=type(response))
        )
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(ERROR_KEYS)
    if not isinstance(homeworks, list):
        raise TypeError(
            ERROR_HOMEWORKS.format(type_homeworks=type(homeworks))
        )
    return homeworks


def parse_status(homework):
    """Определение статуса ревью."""
    name = homework['homework_name']
    status = homework['status']
    verdict = VERDICTS.get(status)
    if not verdict:
        raise ValueError(ERROR_VERDICT.format(verdict=verdict))
    return VERDICT.format(name=name, verdict=verdict)


def check_tokens():
    """Проверка наличия необходимых токенов."""
    empty_tokens = []
    for name in TOKENS:
        if globals()[name] is None:
            empty_tokens.append(name)
            logger.critical(ERROR_TOKEN.format(name=name))
    return len(empty_tokens) == 0


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise NameError(ERROR_TOKENS)
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    cash_message_error = None
    cash_message = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            message = parse_status(homeworks[0])
            if cash_message != message:
                send_message(bot, message)
                cash_message = message
            current_timestamp = (response.get('current_date')
                                 or current_timestamp)
            cash_message_error = None

        except Exception as error:
            if cash_message_error != str(error):
                try:
                    logger.error(ERROR_MAIN.format(error=error))
                    send_message(bot, ERROR_MAIN.format(error=error))
                    cash_message_error = str(error)
                except TelegramError as error:
                    logger.exception(ERROR_SEND.format(error=error))
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    path = os.path.expanduser('~')
    logging.basicConfig(
        filename=os.path.join(path, 'main.log'),
        filemode='w',
        format=('%(asctime)s - %(funcName)s - '
                '%(name)s - %(levelname)s - %(message)s'),
        level=logging.DEBUG
    )
    main()
