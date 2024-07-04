import time
import logging
import os
import sys
import requests

from dotenv import load_dotenv

from telebot import TeleBot
from http_exceptions import HTTPException

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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    logger.debug('Проверка токенов.')
    ENV_VARS = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for env in ENV_VARS:
        if not env:
            logger.critical(f'Отсутствует переменная окружения {env}.')
            sys.exit('Конец работы бота.')


def send_message(bot, message):
    """Oтправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Сообщение: "{message}" отправлено.')
    except Exception as error:
        logger.error(f'Сообщение не отправлено ботом. Ошибка: {error}.')


def get_api_answer(timestamp):
    """Функция делает запрос к эндпоинту API-сервиса.
    В случае успешного запроса должна вернуть ответ API."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f'Ошибка запроса: {response.text}.')
            raise HTTPException.from_status_code(
                status_code=response.status_code)(message=response.text)
    except requests.RequestException:
        logger.error(f'Ошибка запроса:{response.text}.')


def check_response(response):
    """Функция проверяет ответ API на соответствие документации из урока."""
    if isinstance(response, list):
        raise TypeError

    if HOMEWORKS not in response.keys():
        raise KeyError
    if CURRENT_DATE not in response.keys():
        raise KeyError

    if isinstance(response[HOMEWORKS], list) is False:
        raise TypeError
    if isinstance(response[CURRENT_DATE], int) is False:
        raise TypeError


def parse_status(homework):
    """Функция извлекает из информации o конкретной домашней работе статус."""
    if HOMEWORK_NAME not in homework or STATUS not in homework:
        raise KeyError(f'Нет ключа {HOMEWORK_NAME} или {STATUS}!')

    homework_name = homework[HOMEWORK_NAME]
    status = homework[STATUS]

    if status in HOMEWORK_VERDICTS.keys():
        return (f'Изменился статус проверки работы "{homework_name}". '
                f'{HOMEWORK_VERDICTS[status]}')
    else:
        raise ValueError


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    old_verdict = ''

    while True:
        try:
            all_homeworks = get_api_answer(timestamp)
            check_response(all_homeworks)

            last_homework = all_homeworks[HOMEWORKS][0]
            homework_name = last_homework[HOMEWORK_NAME]
            verdict = parse_status(last_homework)
            if old_verdict != verdict:
                message = f'Cтатус проверки "{homework_name}". {verdict}'
                send_message(bot, message)
                old_verdict = verdict
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
            break


if __name__ == '__main__':
    main()
