import sqlite3
import logging

def setup_database():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()

    # Создание таблицы, если она не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT UNIQUE,
            subject TEXT,
            sender TEXT,
            received_time TEXT,
            body TEXT,
            request_type TEXT,
            origin TEXT,
            destination TEXT,
            cargo_details TEXT,
            dates TEXT,
            price TEXT,
            additional_info TEXT,
            processed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

    # Список ожидаемых столбцов (включая новые)
    expected_columns = {
        "query_type": "TEXT",  # Новый столбец
        "transport_type": "TEXT",
        "weight": "TEXT",
        "volume": "TEXT"
    }

    # Проверка существующих столбцов в таблице
    cursor.execute("PRAGMA table_info(emails)")
    existing_columns = [column[1] for column in cursor.fetchall()]  # Список имен столбцов

    # Добавление недостающих столбцов
    for column_name, column_type in expected_columns.items():
        if column_name not in existing_columns:
            try:
                cursor.execute(f'ALTER TABLE emails ADD COLUMN {column_name} {column_type}')
                logging.info(f"Столбец {column_name} ({column_type}) добавлен в таблицу emails.")
            except sqlite3.Error as e:
                logging.error(f"Ошибка при добавлении столбца {column_name}: {e}")

    conn.commit()
    return conn, cursor

def insert_email(cursor, email_data):
    try:
        logging.debug(f"Данные для вставки: {email_data}")
        cursor.execute('''
            INSERT OR IGNORE INTO emails (
                entry_id, subject, sender, received_time, body, request_type, query_type,
                origin, destination, cargo_details, transport_type, dates, price, additional_info, processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            email_data['entry_id'],
            email_data['subject'],
            email_data['sender'],
            email_data['received_time'],
            email_data['body'],
            email_data.get('request_type', ''),
            email_data.get('query_type', ''),
            email_data.get('origin', ''),
            email_data.get('destination', ''),
            email_data.get('cargo_details', ''),
            email_data.get('transport_type', ''),
            email_data.get('dates', ''),
            email_data.get('price', ''),
            email_data.get('additional_info', ''),
            email_data.get('processed', 0)
        ))
        cursor.connection.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка при вставке данных в базу: {e}")

def email_exists_in_db(cursor, entry_id):
    try:
        cursor.execute('SELECT 1 FROM emails WHERE entry_id = ?', (entry_id,))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logging.error(f"Ошибка при проверке существования письма в базе данных: {e}")
        return False

def get_emails_from_db(cursor):
    try:
        cursor.execute("SELECT * FROM emails WHERE processed = 0")
        return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Ошибка при выборке данных из базы: {e}")
        return []

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
