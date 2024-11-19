# email_client/outlook_client.py

import win32com.client  # Библиотека для работы с COM-объектами Windows (Outlook)
from .email_client_base import EmailClientBase
from datetime import datetime, timedelta
import logging  # Импортируем модуль для логирования

# Определение класса OutlookClient, который наследуется от EmailClientBase
class OutlookClient(EmailClientBase):
    def __init__(self):
        # Инициализация атрибутов класса
        self.outlook = None  # Переменная для хранения объекта Outlook (по умолчанию None)
        self.inbox = None  # Переменная для хранения папки "Входящие" (по умолчанию None)
        self.logger = logging.getLogger(__name__)  # Создаем логгер для этого класса

    def connect(self):
        # Метод для подключения к Outlook
        try:
            # Создаем объект Outlook и получаем пространство имен "MAPI" для доступа к почтовым данным
            self.outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            # Получаем папку "Входящие" (номер 6 соответствует папке "Входящие" в Outlook)
            self.inbox = self.outlook.GetDefaultFolder(6)
            self.logger.debug("Успешное подключение к Outlook.")  # Логируем успешное подключение
        except Exception as e:
            # Обрабатываем ошибку подключения и логируем её
            self.logger.error(f"Ошибка подключения к Outlook: {e}")
            # Если произошла ошибка, устанавливаем значения атрибутов в None
            self.outlook = None
            self.inbox = None

    def get_messages(self):
        # Метод для получения писем из папки "Входящие"
        try:
            if self.inbox is not None:
                # Получаем текущую дату и время, а также дату неделю назад
                last_week = datetime.now() - timedelta(days=7)
                today = datetime.now()
                # Преобразуем дату в строку для использования в запросе к Outlook
                last_week_str = last_week.strftime('%m/%d/%Y')
                today_str = today.strftime('%m/%d/%Y %H:%M')
                self.logger.debug(f"Фильтрация сообщений с {last_week_str} по {today_str}")

                # Временно убираем фильтрацию по дате и проверяем количество всех сообщений
                all_messages = self.inbox.Items
                self.logger.info(f"Всего сообщений в папке 'Входящие': {len(all_messages)}")

                # Если хотите, чтобы фильтрация заработала снова, закомментируйте следующую строку и раскомментируйте фильтр ниже
                return all_messages  # Возвращаем все сообщения временно для проверки

                # Восстановите фильтрацию, если всё заработает:
                # messages = self.inbox.Items.Restrict(
                #     f"[ReceivedTime] >= '{last_week_str}' AND [ReceivedTime] <= '{today_str}'"
                # )
                # self.logger.info(f"Получено сообщений: {len(messages)}")
                # return messages
            else:
                # Если папка "Входящие" не найдена, логируем предупреждение и возвращаем None
                self.logger.warning("Папка 'Входящие' не найдена.")
                return None
        except Exception as e:
            # Обрабатываем ошибку при получении писем и логируем её
            self.logger.error(f"Ошибка при получении писем: {e}")
            return None
