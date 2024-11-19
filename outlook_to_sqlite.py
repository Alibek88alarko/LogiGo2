import logging
import os
import re
import sqlite3
import win32com.client
from dotenv import load_dotenv
import openai

class EmailBodySplitter:
    def __init__(self, logger=None):
        # Если логгер не передан, создаем его
        self.logger = logger or logging.getLogger(__name__)

    def split_body(self, full_body):
        """
        Разделяет основное письмо и историю переписки на основе шаблонов, характерных для начала переписки.
        Возвращает кортеж (основное письмо, письмо с историей переписки).
        """
        self.logger.debug("Начинаем разделение тела письма.")

        # Ищем место начала истории переписки по характерным признакам
        split_pattern = (
            r"(?i)^((from|sent|date|subject|от|отправлено|дата|тема):\s+.*)|"
            r"(\n-{2,}\n)"  # Линия из дефисов как разделитель
        )  # Учитывает различные языки и форматы
        split_match = re.search(split_pattern, full_body, re.MULTILINE)

        if split_match:
            main_body = full_body[:split_match.start()].strip()  # Основное письмо без истории переписки
            history_body = full_body[split_match.start():].strip()  # История переписки
            self.logger.debug("История переписки обнаружена и разделена.")
        else:
            main_body = full_body.strip()
            history_body = None  # Если нет истории, устанавливаем None
            self.logger.debug("История переписки не обнаружена. Используем основное письмо полностью.")

        return main_body, history_body

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,  # Измените на DEBUG для более подробного логирования
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("email_processing.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def setup_openai_api():
    # Загрузка переменных окружения из файла .env
    load_dotenv()

    # Получение API ключа
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logging.error("Переменная окружения OPENAI_API_KEY не установлена.")
        return False

    openai.api_key = openai_api_key
    return True

def setup_database():
    # Подключаемся к базе данных SQLite (или создаем новую)
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()

    # Создаем таблицу для хранения писем, если она еще не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            sender TEXT,
            received_time TEXT,
            body TEXT,
            origin TEXT,
            destination TEXT,
            cargo_details TEXT,
            dates TEXT,
            price TEXT,
            additional_info TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

def refers_to_thread(main_body):
    # Простая эвристика для определения ссылок на историю переписки
    thread_keywords = [
        'см. ниже', 'смотрите ниже', 'см. переписку', 'как обсуждалось', 'как договорились',
        'see below', 'as per our conversation', 'please find below', 'как обсуждали ранее'
    ]
    for keyword in thread_keywords:
        if keyword.lower() in main_body.lower():
            return True
    return False

def extract_transportation_info(body):
    logger = logging.getLogger("EmailProcessor")
    try:
        # Формируем запрос для ИИ
        prompt = f"""
Вы помощник, который извлекает информацию о запросах на перевозку или ценовых предложениях из писем для дальнейшего анализа.
Пожалуйста, прочитайте следующее письмо и извлеките информацию о перевозке, сосредоточившись на ключевых деталях, таких как место отправления, место назначения, детали груза, даты и любая ценовая информация.

Письмо:
\"\"\"
{body}
\"\"\"

Пожалуйста, предоставьте извлеченную информацию в следующем формате:

Место отправления:
Место назначения:
Детали груза:
Даты:
Цена:
Дополнительная информация:

Если письмо не содержит информации о перевозке или ценового предложения, или если вы не можете извлечь достаточную информацию, ответьте "Нет информации о перевозке".
"""

        # Используем OpenAI API для получения ответа
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Вы можете выбрать другую модель при необходимости
            messages=[
                {"role": "system", "content": "Вы полезный помощник."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500,
        )
        # Извлекаем ответ ассистента
        answer = response.choices[0].message.content.strip()

        if "Нет информации о перевозке" in answer:
            return None
        else:
            # Парсим ответ и извлекаем данные
            lines = answer.split('\n')
            data = {}
            current_field = ''
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    data[key.strip().lower()] = value.strip()
                    current_field = key.strip().lower()
                elif current_field:
                    data[current_field] += ' ' + line.strip()

            return data
    except Exception as e:
        logger.error(f"Ошибка при обращении к OpenAI API: {e}")
        return None

def process_emails():
    logger = logging.getLogger("EmailProcessor")

    # Подключаемся к Outlook
    try:
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.GetDefaultFolder(6)  # 6 соответствует папке "Входящие"
    except Exception as e:
        logger.error(f"Не удалось подключиться к Outlook: {e}")
        return

    # Подключаемся к базе данных
    conn, cursor = setup_database()

    # Инициализируем EmailBodySplitter
    splitter = EmailBodySplitter(logger=logger)

    # Получаем письма из "Входящих"
    messages = inbox.Items
    message = messages.GetFirst()
    while message:
        try:
            # Проверяем, является ли элемент почтовым сообщением (MailItem)
            if message.Class == 43:  # 43 соответствует MailItem
                subject = message.Subject
                sender = message.SenderName
                received_time = message.ReceivedTime.strftime("%Y-%m-%d %H:%M:%S")
                full_body = message.Body

                # Разделяем тело письма
                main_body, history_body = splitter.split_body(full_body)

                # Решаем, какое тело использовать для анализа
                body_to_analyze = main_body
                if len(main_body) < 50 or refers_to_thread(main_body):
                    # Если мало информации или есть ссылки на историю, включаем историю
                    body_to_analyze = main_body + "\n" + (history_body or "")
                    logger.debug("Используем основное письмо вместе с историей для анализа.")

                # Используем OpenAI API для извлечения информации
                transportation_info = extract_transportation_info(body_to_analyze)

                if transportation_info:
                    # Сохраняем письмо и извлеченную информацию в базу данных
                    cursor.execute('''
                        INSERT INTO emails (
                            subject, sender, received_time, body,
                            origin, destination, cargo_details, dates, price, additional_info
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        subject,
                        sender,
                        received_time,
                        full_body,
                        transportation_info.get('место отправления', ''),
                        transportation_info.get('место назначения', ''),
                        transportation_info.get('детали груза', ''),
                        transportation_info.get('даты', ''),
                        transportation_info.get('цена', ''),
                        transportation_info.get('дополнительная информация', '')
                    ))
                    conn.commit()
                    logger.info(f"Письмо от {sender} от {received_time} обработано и сохранено.")
                else:
                    logger.info(f"Письмо от {sender} от {received_time} не содержит информации о перевозке.")
            else:
                logger.debug("Пропущен элемент, который не является почтовым сообщением.")
        except Exception as e:
            logger.error(f"Ошибка при обработке письма: {e}")
        message = messages.GetNext()

    # Закрываем соединение с базой данных
    conn.close()

if __name__ == "__main__":
    setup_logging()
    if setup_openai_api():
        process_emails()
    else:
        logging.error("Настройка OpenAI API не удалась.")
