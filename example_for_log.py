import logging
from logging.handlers import RotatingFileHandler


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('my_logger.log',
                              maxBytes=50000000,
                              backupCount=5)
logger.addHandler(handler)

logging.debug('Проблема в работе')
logging.info('Сообщение отправлено')
logging.warning('Большая нагрузка!')
logging.error('Бот не смог отправить сообщение')
logging.critical('Всё упало! Зовите админа!')


formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

handler.setFormatter(formatter)
