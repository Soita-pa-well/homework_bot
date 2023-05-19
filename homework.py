from http import HTTPStatus
import logging
import os
import sys
import requests
import time
from telegram import Bot

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в  чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Отправка сообщения в чат')
    except Exception as error:
        logging.error(f'Не удалось отправить сообщение в telegram: {error}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        logging.debug('Запрос отправлен к эндпоинту API-сервиса')
    except ConnectionError:
        logging.error('Нет подключения к интернету')
    except Exception as error:
        error_message = f'Эндпоинт недоступен. Ошибка сервера: {error}'
        logging.error(error_message)
        send_message(error_message)
    if response.status_code != HTTPStatus.OK:
        raise ReferenceError('Статус ответа API не 200')
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    try:
        homework = response['homeworks']
    except KeyError as error:
        key_error_message = f'Ошибка доступа по ключу homeworks: {error}'
        logging.error(key_error_message)
        send_message(key_error_message)
    except Exception as error:
        error_message = f'Неверный ответ API: {error}'
        logging.error(error_message)
        send_message(error_message)
    if not isinstance(homework, list):
        list_error = 'Данные приходят не в виде списка'
        logging.error(list_error)
        raise TypeError(list_error)
    return homework


def parse_status(homework):
    """Извлечение статуса конкретной работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        api_error = f'Неверный ответ API: {error}'
        logging.error(api_error)
        send_message(api_error)
    homework_status = homework.get('status')
    if homework_status == 'approved':
        verdict = HOMEWORK_VERDICTS['approved']
    elif homework_status == 'reviewing':
        verdict = HOMEWORK_VERDICTS['reviewing']
    elif homework_status == 'rejected':
        verdict = HOMEWORK_VERDICTS['rejected']
    else:
        status_error = f'Неверный статус выполненной работы {homework_name}'
        logging.error(status_error)
        send_message(status_error)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия Токенов."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    logging.info('homework_checkBot запущен')
    if not check_tokens():
        token_error = 'Определены не все Токены для корректной работы Бота'
        logging.critical(token_error)
        sys.exit(token_error)
    bot = Bot(token=TELEGRAM_TOKEN)
    sec_in_month = 24 * 30 * 60 * 60
    timestamp = int(time.time()) - sec_in_month
    old_homework_status = ''
    while True:
        try:
            all_homeworks = get_api_answer(timestamp)
            check_response(all_homeworks)
            if all_homeworks['homeworks']:
                homework = parse_status(all_homeworks['homeworks'][0])
                if homework != old_homework_status:
                    old_homework_status = homework
                    send_message(bot, homework)
                    logging.info('Сообщение отправлено успешно')
                else:
                    logging.debug('Статус не изменился')
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='program.log',
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    main()
