# email_client/email_reader.py

# Общий комментарий к файлу:
# Данный файл представляет собой класс EmailReader, который отвечает за чтение писем из почтового сервиса, обработку и сохранение писем в базу данных,
# а также работу с метками, присваивая письмам соответствующие теги. Класс интегрируется с другими компонентами системы, такими как база данных и клиент OpenAI.

import json  # Библиотека для работы с форматом JSON
import os  # Библиотека для работы с операционной системой (например, для работы с путями файлов)
import traceback  # Библиотека для получения трассировки исключений (ошибок)
from email_client.email_client_base import EmailClientBase  # Импортируем базовый класс для клиента почты
import logging  # Библиотека для логирования
from database_manager import DatabaseManager  # Импортируем менеджер базы данных
from email_client.email_message_processor import EmailMessageProcessor  # Импортируем EmailMessageProcessor

# Определение класса EmailReader
class EmailReader:
    def __init__(self, email_client: EmailClientBase, db_manager, tags_manager, tag_processor):
        # Инициализация класса EmailReader с необходимыми зависимостями
        self.email_client = email_client  # Клиент для работы с электронной почтой (например, Outlook)
        self.db_manager = db_manager  # Менеджер базы данных для сохранения данных писем
        self.tags_manager = tags_manager  # Менеджер для работы с метками писем
        self.logger = logging.getLogger(self.__class__.__name__)  # Создаем логгер для этого класса
        self.tag_processor = tag_processor  # Обработчик меток для автоматического присвоения меток письмам
        self.message_processor = EmailMessageProcessor(self.logger)  # Создаем экземпляр для обработки сообщений

    def fetch_emails(self, existing_entryids=set(), limit=None):
        emails = []
        try:
            messages = self.email_client.get_messages()
            if messages is not None:
                messages.Sort("[ReceivedTime]", True)
                for message in messages:
                    if message.Class == 43:  # MailItem
                        # Получаем стабильный уникальный идентификатор письма
                        entryid = self._get_unique_id(message)

                        if entryid is None:
                            self.logger.warning("Письмо без Internet Message ID пропущено.")
                            continue

                        self.logger.debug(f"Обработка сообщения с entryid: {entryid}")

                        if entryid in existing_entryids:
                            self.logger.debug(f"Письмо с entryid {entryid} уже существует в базе данных.")
                            continue

                        email_data = self._process_message(message)
                        if email_data:
                            email_data['entryid'] = entryid
                            emails.append(email_data)

                    if limit and len(emails) >= limit:
                        break
            else:
                self.logger.warning("Не удалось получить письма.")
        except Exception as e:
            self.logger.error(f"Ошибка при чтении писем: {e}")
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            self.logger.debug(f"Трассировка ошибки:\n{traceback_str}")
        return emails

    def _get_unique_id(self, message):
        try:
            # Получаем PR_INTERNET_MESSAGE_ID
            internet_message_id = message.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x1035001E")
            if internet_message_id:
                return internet_message_id
            else:
                self.logger.warning("Письмо не содержит PR_INTERNET_MESSAGE_ID.")
                print("Письмо не содержит PR_INTERNET_MESSAGE_ID.")
                return None
        except Exception as e:
            self.logger.error(f"Ошибка при получении Internet Message ID: {e}")
            print(f"Ошибка при получении Internet Message ID: {e}")
            return None

    def _process_message(self, message):
        # Обертка для вызова метода process из EmailMessageProcessor
        return self.message_processor.process(message)

    def _get_sender_email(self, message):
        # Метод для получения адреса отправителя
        try:
            # Проверяем наличие разных атрибутов отправителя
            if hasattr(message, 'SenderEmailAddress') and message.SenderEmailAddress:
                return message.SenderEmailAddress  # Возвращаем email, если он доступен
            elif hasattr(message, 'Sender') and message.Sender is not None:
                sender = message.Sender
                # Проверяем разные возможные атрибуты отправителя, чтобы получить email
                if hasattr(sender, 'EmailAddress') and sender.EmailAddress:
                    return sender.EmailAddress
                elif hasattr(sender, 'Address') and sender.Address:
                    return sender.Address
                elif hasattr(sender, 'Name') and sender.Name:
                    return sender.Name
                else:
                    return 'Unknown'  # Если ничего не найдено, возвращаем "Unknown"
            elif hasattr(message, 'SentOnBehalfOfName') and message.SentOnBehalfOfName:
                return message.SentOnBehalfOfName
            else:
                return 'Unknown'  # Если email не найден, возвращаем "Unknown"
        except Exception as e:
            # Обрабатываем ошибки при получении адреса отправителя
            self.logger.error(f"Ошибка при получении адреса отправителя: {e}")
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            self.logger.debug(f"Трассировка ошибки:\n{traceback_str}")
            return 'Unknown'

    def _get_attachments(self, message):
        # Метод для получения вложений письма
        attachments = []  # Создаем пустой список для вложений
        try:
            if hasattr(message, 'Attachments'):
                for attachment in message.Attachments:  # Перебираем все вложения письма
                    attachments.append(attachment.FileName)  # Добавляем имя файла вложения в список
        except Exception as e:
            # Обрабатываем ошибки при получении вложений
            self.logger.error(f"Ошибка при получении вложений: {e}")
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            self.logger.debug(f"Трассировка ошибки:\n{traceback_str}")
        return attachments  # Возвращаем список вложений

    def load_existing_emails(self):
        # Метод для получения существующих идентификаторов писем из базы данных
        existing_entryids = self.db_manager.get_existing_entryids()  # Получаем существующие идентификаторы писем из базы данных
        return existing_entryids

    def save_emails(self, emails):
        # Метод для сохранения писем в базу данных
        for email_data in emails:  # Перебираем каждое письмо
            email_id = self.db_manager.save_email(email_data)  # Сохраняем письмо и получаем его идентификатор
            if 'tags' in email_data:
                self.db_manager.save_tags(email_id, email_data['tags'])  # Сохраняем метки письма, если они есть

    def assign_tags(self, email_data):
        # Метод для присвоения меток письму
        try:
            categories_and_tags = self.tags_manager.get_categories_and_tags()  # Получаем текущие категории и метки
            tags = self.tag_processor.assign_tags(email_data, categories_and_tags)  # Присваиваем метки письму на основе данных
            email_data['tags'] = tags  # Сохраняем присвоенные метки в данные письма
            return email_data
        except Exception as e:
            # Обрабатываем ошибки при присвоении меток
            self.logger.error(f"Ошибка при присвоении меток письму: {e}")
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            self.logger.debug(f"Трассировка ошибки:\n{traceback_str}")
            email_data['tags'] = {}
            return email_data
