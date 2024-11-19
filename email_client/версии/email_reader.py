# email_client/email_reader.py
import json

from email_client.email_client_base import EmailClientBase

class EmailReader:
    def __init__(self, email_client: EmailClientBase):
        self.email_client = email_client

    def fetch_emails(self):
        try:
            messages = self.email_client.get_messages()
            if messages is not None:
                emails = []
                for message in messages:
                    email_data = {
                        'subject': message.Subject,
                        'body': message.Body,
                        'sender': message.SenderEmailAddress,
                        'received_time': message.ReceivedTime,
                        'attachments': self._get_attachments(message)
                    }
                    emails.append(email_data)
                return emails
            else:
                print("Не удалось получить письма.")
                return []
        except Exception as e:
            print(f"Ошибка при чтении писем: {e}")
            return []

    def _get_attachments(self, message):
        attachments = []
        try:
            for attachment in message.Attachments:
                attachments.append(attachment.FileName)
            return attachments
        except Exception as e:
            print(f"Ошибка при получении вложений: {e}")
            return []

def save_emails_to_json(self, emails, filename='emails.json'):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(emails, f, ensure_ascii=False, indent=4, default=str)
            print(f"Письма сохранены в файл {filename}")
        except Exception as e:
            print(f"Ошибка при сохранении писем в файл: {e}")
