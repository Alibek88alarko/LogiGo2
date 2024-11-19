# email_client/email_body_splitter.py

import re  # Для работы с регулярными выражениями
import logging  # Для логирования
import win32com.client  # Для работы с Outlook (необходима библиотека pywin32)

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
            r"(?i)^((from|sent|date|subject|发件人|日期|主题|प्रेषक|दिनांक|विषय|de|enviado|fecha|asunto|"
            r"envoyé|objet|من|التاريخ|موضوع|প্রেরক|তারিখ|বিষয়|от|отправлено|дата|тема|data|"
            r"assunto|dari|dikirim|tanggal|subjek|سے|تاریخ|موضوع|送信者|日付|件名|von|gesendet|"
            r"datum|betreff|kutoka|tarehe|mada|ప్రేలగించు|తేదీ|విషయం|प्रेषक|तारीख|"
            r"विषय|kimden|tarih|konu|அனுப்புனர்|தேதி|பொருள்|inviato|oggetto|فرستنده|"
            r"تاریخ|موضوع):\s+.*)|"
            r"(\n-{2,}\n)"  # Линия из дефисов как разделитель
        ) # Учитывает различные языки и форматы
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

    @staticmethod
    def test_with_last_outlook_email():
        # Настройка логирования
        logging.basicConfig(
            level=logging.ERROR,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logger = logging.getLogger("EmailBodySplitterTest")

        # Инициализация Outlook и получение последнего сообщения
        try:
            outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            inbox = outlook.GetDefaultFolder(6)  # Папка "Входящие"
            messages = inbox.Items
            messages.Sort("[ReceivedTime]", True)  # Сортируем по дате получения, начиная с последнего
            latest_message = messages.GetFirst()  # Получаем последнее письмо
            
            # Получаем содержимое тела письма
            full_body = latest_message.Body
            logger.debug("Тестируем с последним письмом из Outlook.")

            # Разделяем тело письма
            splitter = EmailBodySplitter(logger=logger)
            main_body, history_body = splitter.split_body(full_body)

            # Выводим результаты
            print("Основное письмо:")
            print(main_body)
            print("\nИстория переписки:")
            print(history_body if history_body else "Истории переписки нет.")

        except Exception as e:
            logger.error(f"Ошибка при получении письма из Outlook: {e}")

# Запускаем тест, если файл исполняется как основной
if __name__ == "__main__":
    EmailBodySplitter.test_with_last_outlook_email()
