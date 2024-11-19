import logging
from openai import OpenAI
from dotenv import load_dotenv
import os

def get_openai_client():
    logger = logging.getLogger("OpenAIConnection")
    
    # Загрузка переменных окружения из .env файла
    load_dotenv()
    
    # Получение API ключа
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("Переменная окружения OPENAI_API_KEY не установлена.")
        return None

    # Создание клиента OpenAI
    try:
        client = OpenAI(api_key=openai_api_key)
        logger.info("Клиент OpenAI успешно создан.")
        return client
    except Exception as e:
        logger.error(f"Не удалось создать клиента OpenAI: {e}")
        logger.exception("Трассировка ошибки:")
        return None
