import sqlite3

def list_and_clear_tables(db_path):
    """
    Функция для отображения списка таблиц в базе данных и удаления всех значений в выбранных таблицах.
    :param db_path: Путь к файлу базы данных.
    """
    # Подключение к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Получение списка всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("В базе данных нет таблиц.")
            return
        
        # Вывод таблиц с номерами
        print("Список таблиц в базе данных:")
        for i, table in enumerate(tables, start=1):
            print(f"{i}. {table}")
        
        while True:
            # Предложение выбрать таблицы для очистки
            choice = input("\nВведите номера таблиц, в которых нужно удалить значения (через запятую), или 'exit' для выхода: ").strip()
            
            if choice.lower() == 'exit':
                break

            try:
                # Преобразование ввода в список номеров
                selected_indices = [int(num.strip()) for num in choice.split(',')]
                
                # Проверка корректности номеров
                if any(index < 1 or index > len(tables) for index in selected_indices):
                    print("Некорректный выбор. Убедитесь, что номера таблиц указаны правильно.")
                    continue
                
                # Удаление значений во всех полях выбранных таблиц
                for index in selected_indices:
                    table_name = tables[index - 1]
                    print(f"Очищаю таблицу '{table_name}'...")
                    cursor.execute(f"DELETE FROM {table_name};")
                    conn.commit()
                    print(f"Все значения в таблице '{table_name}' удалены.")
            except ValueError:
                print("Некорректный ввод. Убедитесь, что вы вводите номера таблиц через запятую.")
    
    except sqlite3.Error as e:
        print("Ошибка работы с базой данных:", e)
    finally:
        # Закрытие соединения с базой данных
        conn.close()

# Пример использования
list_and_clear_tables("emails.db")
