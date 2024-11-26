import sqlite3

def list_tables_and_fields():
    """
    Функция перечисляет все таблицы и их поля в базе данных.
    """
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    # Список всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print("Список таблиц и их полей:")
    table_structure = {}
    for table in tables:
        table_name = table[0]
        print(f"\nТаблица: {table_name}")

        # Получение информации о столбцах таблицы
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        for column in columns:
            print(f"  - {column[1]} ({column[2]})")
        table_structure[table_name] = [column[1] for column in columns]

    conn.close()
    return table_structure


def delete_table():
    """
    Функция запрашивает, какую таблицу удалить, и удаляет её после подтверждения.
    """
    tables_and_fields = list_tables_and_fields()

    # Запрос имени таблицы для удаления
    table_to_delete = input("\nВведите имя таблицы, которую хотите удалить (или нажмите Enter для отмены): ").strip()

    if not table_to_delete:
        print("Удаление отменено.")
        return

    if table_to_delete not in tables_and_fields:
        print(f"Таблица '{table_to_delete}' не найдена.")
        return

    # Подтверждение удаления
    confirm = input(f"Вы уверены, что хотите удалить таблицу '{table_to_delete}'? (да/нет): ").strip().lower()
    if confirm != "да":
        print("Удаление отменено.")
        return

    # Удаление таблицы
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table_to_delete};")
        conn.commit()
        print(f"Таблица '{table_to_delete}' успешно удалена.")
    except Exception as e:
        print(f"Ошибка при удалении таблицы '{table_to_delete}': {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    print("Добро пожаловать в утилиту управления таблицами SQLite!")
    delete_table()
