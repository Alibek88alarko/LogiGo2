# email_client/email_message_processor.py

import traceback  # Для трассировки ошибок
from email_client.email_body_splitter import EmailBodySplitter  # Импортируем новый класс

class EmailMessageProcessor:
    def __init__(self, logger):
        self.logger = logger  # Логгер для записи ошибок
        self.body_splitter = EmailBodySplitter()  # Экземпляр класса для разделения тела письма

    def process(self, message):
        try:
            subject = getattr(message, 'Subject', "Нет темы")  # Получаем тему письма
            full_body = getattr(message, 'Body', "Нет содержимого") or "Нет содержимого"  # Получаем текстовое содержимое письма
            html_body = getattr(message, 'HTMLBody', "") or ""  # Получаем HTML-версию письма (если доступно)
            received_time = getattr(message, 'ReceivedTime', None)  # Время получения письма
            sender_email = self._get_sender_email(message)  # Получаем адрес отправителя
            attachments = self._get_attachments(message)  # Получаем список вложений
            
            # Используем EmailBodySplitter для разделения основного письма и истории переписки
            main_body, history_body = self.body_splitter.split_body(full_body)

            # Формируем словарь с данными письма
            email_data = {
                'subject': subject,
                'body': main_body,  # Основное письмо без истории переписки
                'history_body': history_body,  # Полное письмо с историей переписки
                'html_body': html_body,
                'sender': sender_email,
                'received_time': str(received_time),  # Преобразуем время в строку для сериализации
                'attachments': attachments
            }
            return email_data  # Возвращаем данные письма
        except Exception as e:
            # Логируем ошибки и трассировку
            self.logger.error(f"Ошибка при обработке сообщения: {e}")
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            self.logger.debug(f"Трассировка ошибки:\n{traceback_str}")
            return None

    def _get_sender_email(self, message):
        # Метод для получения адреса отправителя
        try:
            if hasattr(message, 'SenderEmailAddress') and message.SenderEmailAddress:
                return message.SenderEmailAddress
            elif hasattr(message, 'Sender') and message.Sender is not None:
                sender = message.Sender
                if hasattr(sender, 'EmailAddress') and sender.EmailAddress:
                    return sender.EmailAddress
                elif hasattr(sender, 'Address') and sender.Address:
                    return sender.Address
                elif hasattr(sender, 'Name') and sender.Name:
                    return sender.Name
                else:
                    return 'Unknown'
            elif hasattr(message, 'SentOnBehalfOfName') and message.SentOnBehalfOfName:
                return message.SentOnBehalfOfName
            else:
                return 'Unknown'
        except Exception as e:
            self.logger.error(f"Ошибка при получении адреса отправителя: {e}")
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            self.logger.debug(f"Трассировка ошибки:\n{traceback_str}")
            return 'Unknown'

    def _get_attachments(self, message):
    # Метод для получения вложений письма
         attachments = []
         try:
            if hasattr(message, 'Attachments'):
               for attachment in message.Attachments:
                if attachment.FileName:
                    attachments.append(attachment.FileName)
         except Exception as e:
          self.logger.error(f"Ошибка при получении вложений: {e}")
          traceback_str = ''.join(traceback.format_tb(e.__traceback__))
          self.logger.debug(f"Трассировка ошибки:\n{traceback_str}")
         return attachments
