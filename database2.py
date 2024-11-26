import sqlite3

def create_tables():
    # Подключение к базе данных (создаёт файл, если его нет)
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    # Включение поддержки внешних ключей
    cursor.execute("PRAGMA foreign_keys = ON;")

    # SQL-запросы для создания таблиц
    create_transport_types = """
    CREATE TABLE IF NOT EXISTS transport_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL
    );
    """

    create_transport_details = """
    CREATE TABLE IF NOT EXISTS transport_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transport_type_id INTEGER NOT NULL,
        subtype TEXT NOT NULL,
        size TEXT NOT NULL,
        FOREIGN KEY (transport_type_id) REFERENCES transport_types(id)
    );
    """

    create_routes = """
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loading_location TEXT NOT NULL,
        unloading_location TEXT NOT NULL
    );
    """

    create_prices = """
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transport_id INTEGER NOT NULL,
        route_id INTEGER NOT NULL,
        price REAL NOT NULL,
        emails_id INTEGER,
        FOREIGN KEY (transport_id) REFERENCES transport_details(id),
        FOREIGN KEY (route_id) REFERENCES routes(id),
        FOREIGN KEY (emails_id) REFERENCES emails(id) 
    );
    """

    # Выполнение запросов
    cursor.execute(create_transport_types)
    cursor.execute(create_transport_details)
    cursor.execute(create_routes)
    cursor.execute(create_prices)

    # Сохранение изменений и закрытие соединения
    conn.commit()
    conn.close()
    print("Таблицы успешно созданы.")

if __name__ == "__main__":
    create_tables()
