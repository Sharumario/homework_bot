import logging
import os
import time
import sys

import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

from exceptions import ServerError, MessageError

load_dotenv()

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TOKENS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
RETRY_TIME = 600
VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
SEND_MESSAGE = '"{message}": cообщение отправлено в чат!'
ERROR_SEND = ('Сбой при отправке сообщения: {error}. '
              'Сообщение: "{message}" не доставлено!')
CONNECTION_ERROR = ('Не удалось получить доступ к API: {error} '
                    'Параметры запроса: {endpoint}, {headers}, {params}')
API_RESPONSE_ERROR = ('Неожиданный статус ответа API: {status_code}. '
                      'Параметры запроса: {endpoint}, {headers}, {params}.')
RESPONSE_ERROR = ('Неверный тип данных: {type_response}. '
                  'Ожидался словарь.')
HOMEWORKS_ERROR = ('Неверный тип данных: {type_homeworks}. '
                   'Ожидался список.')
KEYS_ERROR = 'В словаре нет ключа: homeworks'
VERDICT_ERROR = 'Неожиданное принятое значение, отсутствует статус: {status}}'
TOKEN_ERROR = 'Нет обязательной переменной окружения: {name}'
TOKENS_ERROR = 'Ошибка токенов'
SERVER_ERROR = ('Отказ обслуживания сети: "{field}: {error}" '
                'Параметры запроса: {endpoint}, {headers}, {params}')
VERDICT = 'Изменился статус проверки работы "{name}". {verdict}'
MAIN_ERROR = 'Сбой в работе программы: {error}'
EMPTY_RESPONSE = 'Список ДЗ пустой.'


def send_message(bot, message):
    """Отправка сообщения в telegramm."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(SEND_MESSAGE.format(message=message))
    except TelegramError as error:
        raise MessageError(ERROR_SEND.format(error=error, message=message))


def get_api_answer(current_timestamp):
    """Запрос к API Яндекс практикума."""
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.ConnectionError as error:
        raise ConnectionError(
            CONNECTION_ERROR.format(
                error=error,
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params
            )
        )
    if homework_statuses.status_code != 200:
        raise ServerError(
            API_RESPONSE_ERROR.format(
                status_code=homework_statuses.status_code,
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params
            )
        )
    response = homework_statuses.json()
    for field in ['error', 'code']:
        if field in response:
            raise RuntimeError(
                SERVER_ERROR.format(
                    field=field,
                    error=response[field],
                    endpoint=ENDPOINT,
                    headers=HEADERS,
                    params=params
                )
            )
    return response


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            RESPONSE_ERROR.format(type_response=type(response))
        )
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(KEYS_ERROR)
    if not isinstance(homeworks, list):
        raise TypeError(
            HOMEWORKS_ERROR.format(type_homeworks=type(homeworks))
        )
    return homeworks


def parse_status(homework):
    """Определение статуса ревью."""
    name = homework['homework_name']
    status = homework['status']
    verdict = VERDICTS.get(status)
    if not verdict:
        raise ValueError(VERDICT_ERROR.format(status=status))
    return VERDICT.format(name=name, verdict=verdict)


def check_tokens():
    """Проверка наличия необходимых токенов."""
    empty_tokens = [name for name in TOKENS if globals()[name] is None]
    if empty_tokens:
        logger.critical(TOKEN_ERROR.format(name=empty_tokens))
    return not empty_tokens


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError(TOKENS_ERROR)
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    cash_message_error = None
    cash_message = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                message = EMPTY_RESPONSE
            else:
                message = parse_status(homeworks[0])
            if cash_message != message:
                send_message(bot, message)
                cash_message = message
            current_timestamp = (response.get('current_date',
                                 current_timestamp))
            cash_message_error = None

        except Exception as error:
            if cash_message_error != str(error):
                try:
                    logger.error(MAIN_ERROR.format(error=error))
                    send_message(bot, MAIN_ERROR.format(error=error))
                    cash_message_error = str(error)
                except TelegramError as error:
                    logger.exception(
                        ERROR_SEND.format(error=error, message=message)
                    )
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
