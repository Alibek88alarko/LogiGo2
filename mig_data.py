import sqlite3
import logging
from openai_connection import get_openai_client

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmailProcessor")

# Стоимость токенов для модели gpt-3.5-turbo
COST_PER_1000_INPUT_TOKENS = 0.002  # в долларах США
COST_PER_1000_OUTPUT_TOKENS = 0.002  # в долларах США

def extract_transportation_info(client, combined_data):
    """
    Функция для анализа текста письма с использованием OpenAI API.

    Параметры:
        combined_data (str): Текст письма для анализа.

    Возвращает:
        dict: Словарь с извлечённой информацией.
    """
    try:
        prompt = f"""
Вы помощник, который извлекает информацию из писем, связанных с перевозками и ценовыми предложениями.
Пожалуйста, прочитайте следующее письмо и извлеките информацию о перевозке, сосредоточившись на следующих ключевых деталях:

- Место отправления
- Место назначения
- Детали груза
- Тип письма (запрос на перевозку или ответ на запрос или другое)
- Тип запроса
- Тип транспортировки
- Даты
- Цена
- Дополнительная информация

Письмо:
\"\"\"
{combined_data}
\"\"\"

Пожалуйста, предоставьте извлечённую информацию в следующем формате:

Тип письма:
Место отправления:
Место назначения:
Детали груза:
Тип запроса: 
Тип транспортировки:
Даты:
Цена:
Дополнительная информация:

Если письмо не связано с перевозкой, ответьте "Нет информации о перевозке".
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Вы полезный помощник."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )

        answer = response.choices[0].message.content.strip()

        # Извлечение информации об использовании токенов
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens

        # Расчёт стоимости
        input_cost = (prompt_tokens / 1000) * COST_PER_1000_INPUT_TOKENS
        output_cost = (completion_tokens / 1000) * COST_PER_1000_OUTPUT_TOKENS
        total_cost = input_cost + output_cost

        # Логирование информации о токенах и стоимости
        logger.info(f"Использовано токенов: Входные - {prompt_tokens}, Выходные - {completion_tokens}, Всего - {total_tokens}")
        logger.info(f"Стоимость запроса: Входные - ${input_cost:.6f}, Выходные - ${output_cost:.6f}, Общая - ${total_cost:.6f}")

        if "Нет информации о перевозке" in answer or "нет информации о перевозке" in answer.lower():
            return None

        # Обработка ответа и преобразование в словарь
        lines = answer.split('\n')
        data = {}
        current_field = ''

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip().lower()] = value.strip()
                current_field = key.strip().lower()
            elif current_field:
                data[current_field] += ' ' + line.strip()

        return data

    except Exception as e:
        logger.error(f"Ошибка при обращении к OpenAI API: {e}")
        logger.exception("Трассировка ошибки:")
        return None

def analyze_and_migrate():
    # Подключение к базе данных
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    # Извлечение всех необработанных данных из таблицы
    cursor.execute("""
        SELECT id, request_type, origin, destination, cargo_details, price, additional_info, transport_type 
        FROM emails
        WHERE migration_processed = 0 OR migration_processed IS NULL
    """)
    emails = cursor.fetchall()

    if not emails:
        logger.info("Нет необработанных писем для обработки.")
        conn.close()
        print("Данные успешно структурированы и перенесены.")
        return

    # Подсчёт для логирования
    total_emails = len(emails)
    processed_emails = 0
    skipped_emails = 0

    logger.info(f"Найдено писем для обработки: {total_emails}")

    # Обработка каждой записи
    for email in emails:
        email_id, request_type, origin, destination, cargo_details, price, additional_info, transport_type = email

        logger.info(f"Обрабатывается письмо с id {email_id}.")

        client = get_openai_client()  # Получаем клиент OpenAI

        # === Подготовка данных для анализа ИИ ===
        combined_data = f"""
Тип запроса: {request_type}
Место отправления: {origin}
Место назначения: {destination}
Детали груза: {cargo_details}
Цена: {price}
Дополнительная информация: {additional_info}
Тип транспорта: {transport_type}
"""

        try:
            # Начало транзакции
            conn.execute('BEGIN')

            # Вызов ИИ для анализа данных
            analyzed_data = extract_transportation_info(client, combined_data)

            if not analyzed_data:
                logger.info(f"Пропущено письмо с email_id {email_id}: информация о перевозке отсутствует.")
                logger.debug(f"Содержимое письма: {combined_data}")
                logger.debug(f"Ответ модели: {analyzed_data}")
                # Отмечаем письмо как обработанное для миграции
                cursor.execute("UPDATE emails SET migration_processed = 1 WHERE id = ?", (email_id,))
                conn.commit()
                skipped_emails += 1
                continue

            # Извлечение структурированных данных из анализа
            structured_route = {
                "origin": analyzed_data.get("место отправления", origin),
                "destination": analyzed_data.get("место назначения", destination)
            }
            structured_price = analyzed_data.get("цена", price)
            transport_subtype = analyzed_data.get("тип транспортировки", transport_type)
            transport_size = analyzed_data.get("детали груза", cargo_details)

            logger.debug(f"Структурированные данные: {structured_route}, {structured_price}, {transport_subtype}, {transport_size}")

            # === Маршруты (routes) ===
            origin = structured_route["origin"]
            destination = structured_route["destination"]
            cursor.execute("SELECT id FROM routes WHERE loading_location = ? AND unloading_location = ?", (origin, destination))
            route = cursor.fetchone()

            if route:
                route_id = route[0]
                logger.debug(f"Найден существующий маршрут с id {route_id}.")
            else:
                cursor.execute("INSERT INTO routes (loading_location, unloading_location) VALUES (?, ?)", (origin, destination))
                route_id = cursor.lastrowid
                logger.debug(f"Добавлен новый маршрут с id {route_id}.")

            # === Типы транспорта (transport_types) ===
            if transport_type:
                cursor.execute("SELECT id FROM transport_types WHERE type = ?", (transport_type,))
                transport_type_record = cursor.fetchone()

                if transport_type_record:
                    transport_type_id = transport_type_record[0]
                    logger.debug(f"Найден существующий тип транспорта с id {transport_type_id}.")
                else:
                    cursor.execute("INSERT INTO transport_types (type) VALUES (?)", (transport_type,))
                    transport_type_id = cursor.lastrowid
                    logger.debug(f"Добавлен новый тип транспорта с id {transport_type_id}.")

                # === Детали транспорта (transport_details) ===
                cursor.execute("SELECT id FROM transport_details WHERE transport_type_id = ? AND subtype = ? AND size = ?", 
                               (transport_type_id, transport_subtype, transport_size))
                transport_detail = cursor.fetchone()

                if transport_detail:
                    transport_id = transport_detail[0]
                    logger.debug(f"Найден существующий деталь транспорта с id {transport_id}.")
                else:
                    cursor.execute("""
                        INSERT INTO transport_details (transport_type_id, subtype, size) 
                        VALUES (?, ?, ?)
                    """, (transport_type_id, transport_subtype, transport_size))
                    transport_id = cursor.lastrowid
                    logger.debug(f"Добавлена новая деталь транспорта с id {transport_id}.")

                # === Цены (prices) ===
                cursor.execute("INSERT INTO prices (transport_id, route_id, price, email_id) VALUES (?, ?, ?, ?)", 
                               (transport_id, route_id, structured_price, email_id))
                logger.debug(f"Добавлена новая запись в таблицу 'prices' для email_id {email_id}.")

            # Отмечаем письмо как обработанное для миграции
            cursor.execute("UPDATE emails SET migration_processed = 1 WHERE id = ?", (email_id,))
            # Коммит всех изменений для текущего письма
            conn.commit()
            processed_emails += 1
            logger.info(f"Письмо с id {email_id} успешно обработано.")

        except Exception as e:
            # Откат транзакции в случае ошибки
            conn.rollback()
            logger.error(f"Ошибка при обработке письма с id {email_id}: {e}")
            logger.exception("Трассировка ошибки:")
            skipped_emails += 1
            continue

    # Логирование итогов
    logger.info(f"Всего писем: {total_emails}, Обработано: {processed_emails}, Пропущено: {skipped_emails}")

    # Закрытие соединения
    conn.close()
    print("Данные успешно структурированы и перенесены.")

if __name__ == "__main__":
    analyze_and_migrate()
