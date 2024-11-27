import sqlite3

def monitor_and_delete_values(db_path):
    """
    Функция для мониторинга структуры базы данных и удаления значений полей.
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

        if not tables:
            print("В базе данных нет таблиц.")
            return

        # Сбор информации о столбцах для каждой таблицы
        table_structure = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [row[1] for row in cursor.fetchall()]
            table_structure[table] = columns
            print(f"Таблица '{table}' содержит столбцы: {columns}")

        while True:
            action = input("\nВы хотите удалить значения из поля? Введите 'yes' для продолжения или 'exit' для выхода: ").strip()
            
            if action.lower() == 'exit':
                break
            elif action.lower() == 'yes':
                # Пользователь выбирает таблицу
                table_name = input("Введите название таблицы, из которой вы хотите удалить значения: ").strip()
                if table_name not in tables:
                    print(f"Таблица '{table_name}' не найдена.")
                    continue

                # Пользователь выбирает поле
                field_name = input(f"Введите название столбца в таблице '{table_name}': ").strip()
                if field_name not in table_structure[table_name]:
                    print(f"Столбец '{field_name}' не найден в таблице '{table_name}'.")
                    continue

                # Подтверждение удаления
                confirmation = input(f"Вы уверены, что хотите удалить все значения в поле '{field_name}' таблицы '{table_name}'? (yes/no): ").strip()
                if confirmation.lower() == 'yes':
                    # Удаление значений в указанном поле
                    cursor.execute(f"UPDATE {table_name} SET {field_name} = NULL;")
                    conn.commit()
                    print(f"Значения в поле '{field_name}' таблицы '{table_name}' успешно удалены.")
                else:
                    print("Удаление отменено.")
            else:
                print("Некорректный выбор. Введите 'yes' для удаления значений или 'exit' для выхода.")

    except sqlite3.Error as e:
        print("Ошибка работы с базой данных:", e)
    finally:
        # Закрытие соединения с базой данных
        conn.close()

# Пример использования
monitor_and_delete_values("emails.db")
