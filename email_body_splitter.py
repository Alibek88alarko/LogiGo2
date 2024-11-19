import re  # Для работы с регулярными выражениями
import logging  # Для логирования

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
            r"(?i)^((from|sent|date|subject|"
            r"от|отправлено|дата|тема|"
            r"de|envoyé|date|sujet|"
            r"von|gesendet|datum|betreff|"
            r"da|inviato|data|oggetto|"
            r"de|enviado|fecha|asunto|"
            r"由|发送时间|日期|主题|"
            r"发件人|寄件日期|信件主题|"
            r"van|verzonden|datum|onderwerp|"
            r"fra|sendt|dato|emne|"
            r"від|надіслано|дата|тема|"
            r"من|مرسل|تاريخ|موضوع|"
            r"fra|sendt|dato|emne|"
            r"mới|gửi|ngày|chủ đề|"
            r"od|poslano|datum|naslov|"
            r"od|zaslano|datum|predmet|"
            r"отправитель|отправлено|дата|тема|"
            r"发件者|发送日期|日期|主题):\s+.*)|"
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
