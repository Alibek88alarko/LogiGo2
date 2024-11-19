import logging
import win32com.client

def get_outlook_messages():
    logger = logging.getLogger("OutlookConnection")
    try:
        # Подключаемся к Outlook
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.GetDefaultFolder(6)  # 6 соответствует папке "Входящие"
        messages = inbox.Items
        logger.info("Успешно подключились к Outlook и получили сообщения.")
        return messages
    except Exception as e:
        logger.error(f"Не удалось подключиться к Outlook: {e}")
        return None
