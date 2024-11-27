import sqlite3
import logging
import pandas as pd

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Уровень DEBUG для подробного логирования
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.FileHandler("data_extraction.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DataExtractor")

def extract_price_and_route(db_path):
    """
    Функция для извлечения цены и маршрута из базы данных.
    
    Параметры:
        db_path (str): Путь к файлу базы данных SQLite.
    
    Возвращает:
        pandas.DataFrame: Таблица с ценой, местом отправления и местом назначения.
    """
    try:
        # Подключение к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logger.debug(f"Подключение к базе данных '{db_path}' установлено.")
    except Exception as e:
        logger.error(f"Не удалось подключиться к базе данных: {e}")
        return pd.DataFrame()
    
    try:
        # Определение SQL-запроса
        query = """
            SELECT prices.price, routes.loading_location, routes.unloading_location
            FROM prices
            JOIN routes ON prices.route_id = routes.id;
        """
        logger.debug("Выполнение SQL-запроса для извлечения цены и маршрута.")
        cursor.execute(query)
        results = cursor.fetchall()
        logger.info(f"Извлечено {len(results)} записей из базы данных.")
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        conn.close()
        return pd.DataFrame()
    
    # Закрытие соединения с базой данных
    try:
        conn.close()
        logger.debug("Соединение с базой данных закрыто.")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения: {e}")
    
    # Создание DataFrame из результатов
    df = pd.DataFrame(results, columns=['Цена (USD)', 'Место Отправления', 'Место Назначения'])
    logger.debug("Создан DataFrame из извлечённых данных.")
    
    return df

def export_to_excel(df, excel_path):
    """
    Функция для экспорта данных в Excel.
    
    Параметры:
        df (pandas.DataFrame): Таблица с данными.
        excel_path (str): Путь к создаваемому Excel-файлу.
    """
    if df.empty:
        logger.info("Нет данных для экспорта в Excel.")
        return
    
    try:
        # Экспорт DataFrame в Excel
        df.to_excel(excel_path, index=False, engine='openpyxl')
        logger.info(f"Данные успешно экспортированы в Excel-файл '{excel_path}'.")
    except Exception as e:
        logger.error(f"Ошибка при экспорте данных в Excel: {e}")
        logger.exception("Трассировка ошибки:")

def display_extracted_data(df):
    """
    Функция для отображения извлечённых данных в консоли.
    
    Параметры:
        df (pandas.DataFrame): Таблица с данными.
    """
    if df.empty:
        logger.info("Нет данных для отображения.")
        return
    
    logger.info("Вывод извлечённых данных:")
    for idx, row in df.iterrows():
        print(f"{idx + 1}. Маршрут: {row['Место Отправления']} -> {row['Место Назначения']}, Цена: {row['Цена (USD)']} USD")
        logger.debug(f"Маршрут {idx + 1}: Отправление - {row['Место Отправления']}, Назначение - {row['Место Назначения']}, Цена - {row['Цена (USD)']} USD")

if __name__ == "__main__":
    db_path = "emails.db"  # Укажите путь к вашей базе данных
    excel_path = "extracted_data.xlsx"  # Укажите путь для сохранения Excel-файла
    
    # Извлечение данных
    extracted_data = extract_price_and_route(db_path)
    
    # Отображение данных в консоли
    display_extracted_data(extracted_data)
    
    # Экспорт данных в Excel
    export_to_excel(extracted_data, excel_path)
