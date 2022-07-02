import logging
import os
import time
import sys

import requests
from dotenv import load_dotenv
from telegram import Bot

from exceptions import EndPointError, MessageError


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
ERROR_SEND_MESSAGE = 'Сбой при отправке корректного сообщения: {error}'
MESSAGE_ERROR_API_RESPONSE = ('Неожиданный статус ответа API: {status_code}. '
                              'Параметры запроса: {params}.')
MESSAGE_ERROR_RESPONSE = ('Неверный тип данных: {type_response}. '
                          'Ожидался словарь.')
MESSAGE_ERROR_HOMEWORKS = ('Неверный тип данных: {type_homeworks}. '
                           'Ожидался список.')
MESSAGE_ERROR_KEYS = 'Отсутствует ключ: {error}'
MESSAGE_ERROR_VERDICT = ('Вердикт не соответствует '
                         'ожидаемым значениям: {verdict}')
MESSAGE_ERROR_TOKEN = 'Нет обязательных переменных окружения: {name}'
VERDICT = 'Изменился статус проверки работы "{name}". {verdict}'


def send_message(bot, message):
    """Отправка сообщения в telegramm."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено в чат!')
    except MessageError as error:
        logger.exception(error)
        raise MessageError(ERROR_SEND_MESSAGE.format(error=error))


def get_api_answer(current_timestamp):
    """Запрос к API Яндекс практикума."""
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        logger.exception(error)
        raise EndPointError('Не удалось получить доступ к API')
    if homework_statuses.status_code != 200:
        raise EndPointError(
            MESSAGE_ERROR_API_RESPONSE.format(
                status_code=homework_statuses.status_code,
                params=params
            )
        )
    return homework_statuses.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            MESSAGE_ERROR_RESPONSE.format(type_response=type(response))
        )
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        logger.exception(error)
        raise KeyError('В словаре нет ключа: homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            MESSAGE_ERROR_HOMEWORKS.format(type_homeworks=type(homeworks))
        )
    return homeworks


def parse_status(homework):
    """Определение статуса ревью."""
    try:
        name = homework['homework_name']
        status = homework['status']
    except KeyError as error:
        raise KeyError(MESSAGE_ERROR_KEYS.format(error=error))
    verdict = VERDICTS.get(status)
    if not verdict:
        logger.exception(MESSAGE_ERROR_VERDICT.format(verdict=verdict))
        raise ValueError('Неожиданное принятое значение: None')
    return VERDICT.format(name=name, verdict=verdict)


def check_tokens():
    """Проверка наличия необходимых токенов."""
    cash_chek = []
    for name in ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']:
        if globals()[name] is None:
            logging.critical(
                MESSAGE_ERROR_TOKEN.format(name=name)
            )
            cash_chek.append(1)
    if len(cash_chek) != 0:
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise SyntaxError('Ошибка токенов')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    cash_message_error = None
    cash_message = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                raise IndexError('Нет домашних заданий(')
            message = parse_status(homeworks[0])
            if cash_message != message:
                send_message(bot, message)
                cash_message = message
            else:
                logger.debug('Обновлении статуса ДЗ нет.')
            current_timestamp = response['current_date']
            cash_message_error = None

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if cash_message_error != str(error):
                try:
                    send_message(bot, message)
                    cash_message_error = str(error)
                except Exception:
                    logger.error('Не удаётся отправить сообщение в телеграмм')
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
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    main()
