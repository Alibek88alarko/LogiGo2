import sqlite3

def monitor_database(db_path):
    """
    Функция для мониторинга структуры базы данных SQLite.
    :param db_path: Путь к файлу базы данных.
    """
    # Подключение к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Получение списка всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print("Существующие таблицы в базе данных:", tables)
        
        # Сбор информации о столбцах для каждой таблицы
        table_structure = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [row[1] for row in cursor.fetchall()]
            table_structure[table] = columns
            print(f"Таблица '{table}' содержит столбцы: {columns}")
        
        # Предложение добавить таблицы или столбцы
        while True:
            action = input("\nВы хотите добавить (1) таблицу или (2) столбец в таблицу? Введите 1, 2 или 'exit' для выхода: ").strip()
            
            if action.lower() == 'exit':
                break
            elif action == '1':
                new_table = input("Введите название новой таблицы: ").strip()
                if new_table in tables:
                    print(f"Таблица '{new_table}' уже существует.")
                else:
                    columns = input("Введите названия столбцов для новой таблицы (через запятую): ").strip().split(',')
                    create_table_query = f"CREATE TABLE {new_table} ({', '.join([col.strip() + ' TEXT' for col in columns])});"
                    cursor.execute(create_table_query)
                    conn.commit()
                    print(f"Таблица '{new_table}' создана с колонками: {columns}")
            
            elif action == '2':
                table_name = input("Введите название существующей таблицы: ").strip()
                if table_name not in tables:
                    print(f"Таблица '{table_name}' не найдена.")
                else:
                    new_column = input("Введите название нового столбца: ").strip()
                    if new_column in table_structure[table_name]:
                        print(f"Столбец '{new_column}' уже существует в таблице '{table_name}'.")
                    else:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {new_column} TEXT;")
                        conn.commit()
                        print(f"Столбец '{new_column}' добавлен в таблицу '{table_name}'.")
            else:
                print("Некорректный выбор. Пожалуйста, введите 1, 2 или 'exit'.")
    
    except sqlite3.Error as e:
        print("Ошибка работы с базой данных:", e)
    finally:
        # Закрытие соединения с базой данных
        conn.close()

# Пример использования
monitor_database("emails.db")
