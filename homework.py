import logging
import os
import sys
import time

from dotenv import load_dotenv
from telebot import TeleBot
from telebot.apihelper import ApiException

import requests
from requests.exceptions import RequestException
from http import HTTPStatus

from contextlib import suppress

load_dotenv()

logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

CURRENT_DATE = 'current_date'
STATUS = 'status'
HOMEWORKS = 'homeworks'
HOMEWORK_NAME = 'homework_name'


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    logger.debug('Проверка токенов.')
    ENV_VARS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    missing_tokens = []
    globals_values = globals()
    for env in ENV_VARS:
        token_value = globals_values[env]
        if token_value == '' or token_value is None:
            missing_tokens.append(env)

    if len(missing_tokens) > 0:
        token_values = ' '.join(missing_tokens)
        message = f'Отсутствуют переменные окружения: {token_values}.'
        logger.critical(message)
        raise ValueError(message)


def send_message(bot, message):
    """Oтправляет сообщение в Telegram-чат."""
    logger.info(f'Сообщение: "{message}" отправляется.')
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logger.debug(f'Сообщение: "{message}" отправлено.')


def get_api_answer(timestamp):
    """Функция делает запрос к эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    logger.info(f'Запрос: "{payload}" отправляется.')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise RequestException(response.text)
    except RequestException:
        raise ConnectionError(f'Ошибка запроса:{response.text}.')

    logger.info('Запрос отправлен успешно.')
    return response.json()


def check_response(response):
    """Функция проверяет ответ API на соответствие документации из урока."""
    logger.info('Начало проверки ответа API')
    if not isinstance(response, dict):
        raise TypeError(f'{response} не является словарем')

    if HOMEWORKS not in response:
        raise KeyError(f'{HOMEWORKS} отсутствует в словаре')

    if not isinstance(response[HOMEWORKS], list):
        raise TypeError(f'неверный формат {HOMEWORKS}')

    logger.info('Пройдена проверка ответа API')


def parse_status(homework):
    """Функция извлекает из информации o конкретной домашней работе статус."""
    logger.info('Начало проверки статуса работы')
    if HOMEWORK_NAME not in homework:
        raise KeyError(f'Нет ключа {HOMEWORK_NAME}!')

    if STATUS not in homework:
        raise KeyError(f'Нет ключа {STATUS}!')

    homework_name = homework[HOMEWORK_NAME]
    status = homework[STATUS]

    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Статуса: {status} не существует!')

    logger.info('Конец проверки статуса работы')
    return (f'Изменился статус проверки работы "{homework_name}". '
            f'{HOMEWORK_VERDICTS[status]}')


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    old_message = ''

    while True:
        try:
            all_homeworks = get_api_answer(timestamp)
            timestamp = all_homeworks.get(CURRENT_DATE, int(time.time()))
            check_response(all_homeworks)
            if len(all_homeworks[HOMEWORKS]) == 0:
                logger.info('Список домашних работ пуст!')
                continue

            last_homework = all_homeworks[HOMEWORKS][0]
            new_message = parse_status(last_homework)
            if old_message != new_message:
                send_message(bot, new_message)
                old_message = new_message
        except RequestException or ApiException as error:
            logger.exception(f'Сбой в работе программы: {error}. '
                             'Бот временно недоступен')

        except Exception as error:
            new_message = f'Сбой в работе программы: {error}'
            logger.exception(new_message)
            with suppress(Exception):
                if old_message != new_message:
                    send_message(bot, new_message)
                    old_message = new_message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s'
        ))
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[stream_handler]
    )
    main()
