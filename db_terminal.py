import sqlite3

def execute_sql(database_path, sql_command):
    """
    Выполняет SQL-команду в указанной базе данных SQLite.

    Аргументы:
        database_path (str): Путь к файлу базы данных SQLite.
        sql_command (str): SQL-команда для выполнения.

    Возвращает:
        list: Результат выполнения SQL-команды (если есть).
    """
    try:
        # Подключение к базе данных
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        print(f"Подключено к базе данных: {database_path}")
        
        # Выполнение SQL-команды
        cursor.execute(sql_command)
        
        # Если команда возвращает данные, выводим их
        if sql_command.strip().lower().startswith("select"):
            results = cursor.fetchall()
            for row in results:
                print(row)
        else:
            # Сохранение изменений, если команда изменила базу данных
            conn.commit()
            print("Команда выполнена успешно.")
        
        cursor.close()
    except sqlite3.Error as e:
        print(f"Ошибка SQLite: {e}")
    finally:
        # Закрытие подключения
        if conn:
            conn.close()

if __name__ == "__main__":
    # Запрос пути к базе данных и команды
    database = input("Введите путь к базе данных SQLite (например, emails.db): ").strip()
    while True:
        print("\nВведите SQL-команду (или 'exit' для выхода):")
        command = input("> ").strip()
        if command.lower() == "exit":
            print("Выход из программы.")
            break
        execute_sql(database, command)
