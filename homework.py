import logging
import os
import sys
import time
from contextlib import suppress
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException
from telebot import TeleBot
from telebot.apihelper import ApiException

load_dotenv()


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
    logging.debug('Проверка токенов.')
    ENV_VARS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    missing_tokens = [token for token in ENV_VARS if not globals()[token]]

    if missing_tokens:
        token_values = ' '.join(missing_tokens)
        message = f'Отсутствуют переменные окружения: {token_values}.'
        logging.critical(message)
        raise ValueError(message)


def send_message(bot, message):
    """Oтправляет сообщение в Telegram-чат."""
    logging.info(f'Сообщение: "{message}" отправляется.')
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.debug(f'Сообщение: "{message}" отправлено.')


def get_api_answer(timestamp):
    """Функция делает запрос к эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    logging.info(f'Запрос отправляется к {ENDPOINT} с параметрами:"{payload}"')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except RequestException as error:
        raise ConnectionError(f'Ошибка запроса к {ENDPOINT} с параметрами: '
                              f'"{payload}". Ошибка:{error}.')

    if response.status_code != HTTPStatus.OK:
        raise RequestException(f'Получен неожиданный статус ответа: '
                               f'{response.status_code}')
    logging.info('Запрос отправлен успешно.')
    return response.json()


def check_response(response):
    """Функция проверяет ответ API на соответствие документации из урока."""
    logging.info('Начало проверки ответа API')
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API не является словарем, '
                        f'тип данных: {type(response)}')

    if HOMEWORKS not in response:
        raise KeyError(f'Ключ {HOMEWORKS} отсутствует в ответе API')

    if not isinstance(response[HOMEWORKS], list):
        raise TypeError(f'Ключ {HOMEWORKS} в ответе API не является списком, '
                        f'тип данных: {type(response[HOMEWORKS])}')

    logging.info('Пройдена проверка ответа API')


def parse_status(homework):
    """Функция извлекает из информации o конкретной домашней работе статус."""
    logging.info('Начало проверки статуса работы')
    if HOMEWORK_NAME not in homework:
        raise KeyError(f'Нет ключа {HOMEWORK_NAME} '
                       f'в данных о домашней работе {homework}!')

    if STATUS not in homework:
        raise KeyError(f'Нет ключа {STATUS} '
                       f'в данных о домашней работе {homework}!')

    homework_name = homework[HOMEWORK_NAME]
    status = homework[STATUS]

    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неожиданный статус: {status}!')

    logging.info('Конец проверки статуса работы')
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
            homeworks = all_homeworks[HOMEWORKS]
            if not homeworks:
                logging.info('Список домашних работ пуст!')
                continue

            last_homework = homeworks[0]
            new_message = parse_status(last_homework)
            if old_message != new_message:
                send_message(bot, new_message)
                old_message = new_message
        except (RequestException, ApiException) as error:
            logging.exception(f'Сбой в работе программы: {error}. '
                              'Бот временно недоступен')

        except Exception as error:
            new_message = f'Сбой в работе программы: {error}'
            logging.exception(new_message)
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
