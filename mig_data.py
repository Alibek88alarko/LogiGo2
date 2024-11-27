import sqlite3
import logging
from openai_connection import get_openai_client

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Уровень DEBUG для подробного логирования
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.FileHandler("email_processor.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EmailProcessor")

# Отключение логирования для системных библиотек
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("openai").setLevel(logging.CRITICAL)

# Стоимость токенов для модели gpt-3.5-turbo
COST_PER_1000_INPUT_TOKENS = 0.002  # в долларах США
COST_PER_1000_OUTPUT_TOKENS = 0.002  # в долларах США

def extract_transportation_info(client, combined_data, email_id):
    """
    Функция для анализа текста письма с использованием OpenAI API.

    Параметры:
        combined_data (str): Текст письма для анализа.
        email_id (int): Идентификатор письма для логирования.

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

        logger.debug(f"Письмо ID {email_id}: Отправка запроса к OpenAI API.")
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
        logger.debug(f"Письмо ID {email_id}: Полный ответ ИИ: {answer}")

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
        logger.info(f"Письмо ID {email_id}: Использовано токенов - Входные: {prompt_tokens}, Выходные: {completion_tokens}, Всего: {total_tokens}")
        logger.info(f"Письмо ID {email_id}: Стоимость запроса - Входные: ${input_cost:.6f}, Выходные: ${output_cost:.6f}, Общая: ${total_cost:.6f}")

        if "Нет информации о перевозке" in answer or "нет информации о перевозке" in answer.lower():
            logger.info(f"Письмо ID {email_id}: ИИ ответил - Нет информации о перевозке.")
            return None

        # Обработка ответа и преобразование в словарь
        lines = answer.split('\n')
        data = {}
        current_field = ''

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                data[key] = value
                current_field = key
            elif current_field:
                data[current_field] += ' ' + line.strip()

        logger.debug(f"Письмо ID {email_id}: Извлечённые данные: {data}")

        # Проверка обязательных полей
        required_fields = [
            "тип письма",
            "место отправления",
            "место назначения",
            "детали груза",
            "тип запроса",
            "тип транспортировки",
            "даты",
            "цена",
            "дополнительная информация"
        ]
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            logger.warning(f"Письмо ID {email_id}: Отсутствуют обязательные поля: {missing_fields}")

        return data

    except Exception as e:
        logger.error(f"Письмо ID {email_id}: Ошибка при обращении к OpenAI API: {e}")
        logger.exception("Трассировка ошибки:")
        return None

def create_tables_if_not_exists(cursor):
    """
    Функция для создания необходимых таблиц, если они не существуют.
    """
    try:
        # Включаем поддержку внешних ключей
        cursor.execute("PRAGMA foreign_keys = ON;")
        logger.debug("Включена поддержка внешних ключей.")

        # Создание таблицы routes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loading_location TEXT NOT NULL,
                unloading_location TEXT NOT NULL,
                UNIQUE(loading_location, unloading_location)
            );
        """)
        logger.debug("Таблица 'routes' создана или уже существует.")

        # Создание таблицы transport_types
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transport_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL UNIQUE
            );
        """)
        logger.debug("Таблица 'transport_types' создана или уже существует.")

        # Создание таблицы transport_details
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transport_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transport_type_id INTEGER NOT NULL,
                subtype TEXT,
                size TEXT,
                FOREIGN KEY (transport_type_id) REFERENCES transport_types(id),
                UNIQUE(transport_type_id, subtype, size)
            );
        """)
        logger.debug("Таблица 'transport_details' создана или уже существует.")

        # Создание таблицы prices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transport_id INTEGER NOT NULL,
                route_id INTEGER NOT NULL,
                price REAL NOT NULL,
                email_id INTEGER NOT NULL,
                FOREIGN KEY (transport_id) REFERENCES transport_details(id),
                FOREIGN KEY (route_id) REFERENCES routes(id),
                FOREIGN KEY (email_id) REFERENCES emails(id)
            );
        """)
        logger.debug("Таблица 'prices' создана или уже существует.")

        logger.info("Все необходимые таблицы успешно созданы или уже существуют.")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise  # Поднять исключение для дальнейшей обработки

def analyze_and_migrate():
    # Подключение к базе данных
    try:
        conn = sqlite3.connect("emails.db")
        cursor = conn.cursor()
        logger.debug("Подключение к базе данных 'emails.db' установлено.")
    except Exception as e:
        logger.error(f"Не удалось подключиться к базе данных: {e}")
        return

    try:
        # Создание необходимых таблиц, если они не существуют
        create_tables_if_not_exists(cursor)
        conn.commit()
        logger.debug("Транзакция по созданию таблиц зафиксирована.")
    except Exception as e:
        logger.error("Не удалось создать необходимые таблицы. Завершение работы.")
        conn.close()
        return

    # Извлечение всех необработанных данных из таблицы
    try:
        cursor.execute("""
            SELECT id, request_type, origin, destination, cargo_details, price, additional_info, transport_type 
            FROM emails
            WHERE migration_processed = 0 OR migration_processed IS NULL
        """)
        emails = cursor.fetchall()
        logger.debug(f"Запрос на выборку необработанных писем выполнен. Найдено {len(emails)} писем.")
    except Exception as e:
        logger.error(f"Ошибка при извлечении писем из базы данных: {e}")
        conn.close()
        return

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
        logger.debug(f"Клиент OpenAI для письма с id {email_id} успешно создан.")

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

        logger.debug(f"Письмо ID {email_id}: Подготовленные данные для ИИ:\n{combined_data}")

        try:
            # Начало транзакции
            conn.execute('BEGIN')
            logger.debug(f"Письмо ID {email_id}: Начата транзакция.")

            # Вызов ИИ для анализа данных
            analyzed_data = extract_transportation_info(client, combined_data, email_id)

            if not analyzed_data:
                logger.info(f"Письмо ID {email_id}: Пропущено - информация о перевозке отсутствует.")
                logger.debug(f"Письмо ID {email_id}: Содержимое письма:\n{combined_data}")
                logger.debug(f"Письмо ID {email_id}: Ответ модели:\n{analyzed_data}")
                # Отмечаем письмо как обработанное для миграции
                cursor.execute("UPDATE emails SET migration_processed = 1 WHERE id = ?", (email_id,))
                conn.commit()
                logger.debug(f"Письмо ID {email_id}: Флаг 'migration_processed' обновлён.")
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
            transport_type_extracted = analyzed_data.get("тип транспортировки", transport_type)

            logger.debug(f"Письмо ID {email_id}: Структурированные данные:")
            logger.debug(f"Письмо ID {email_id}: Маршрут - Отправление: {structured_route['origin']}, Назначение: {structured_route['destination']}")
            logger.debug(f"Письмо ID {email_id}: Цена: {structured_price}")
            logger.debug(f"Письмо ID {email_id}: Тип транспортировки: {transport_type_extracted}")
            logger.debug(f"Письмо ID {email_id}: Детали груза: {transport_size}")

            # Проверка наличия transport_type
            if not transport_type_extracted:
                logger.warning(f"Письмо ID {email_id}: Поле 'тип транспортировки' отсутствует или пусто. Пропуск вставки в связанные таблицы.")

            # === Маршруты (routes) ===
            origin = structured_route["origin"]
            destination = structured_route["destination"]
            logger.debug(f"Письмо ID {email_id}: Поиск маршрута - От: {origin} -> До: {destination}")
            cursor.execute("SELECT id FROM routes WHERE loading_location = ? AND unloading_location = ?", (origin, destination))
            route = cursor.fetchone()

            if route:
                route_id = route[0]
                logger.debug(f"Письмо ID {email_id}: Найден существующий маршрут с id {route_id}.")
            else:
                cursor.execute("INSERT INTO routes (loading_location, unloading_location) VALUES (?, ?)", (origin, destination))
                route_id = cursor.lastrowid
                logger.debug(f"Письмо ID {email_id}: Добавлен новый маршрут с id {route_id}.")

            # === Типы транспорта (transport_types) ===
            if transport_type_extracted:
                logger.debug(f"Письмо ID {email_id}: Обработка типа транспорта - {transport_type_extracted}")
                cursor.execute("SELECT id FROM transport_types WHERE type = ?", (transport_type_extracted,))
                transport_type_record = cursor.fetchone()

                if transport_type_record:
                    transport_type_id = transport_type_record[0]
                    logger.debug(f"Письмо ID {email_id}: Найден существующий тип транспорта с id {transport_type_id}.")
                else:
                    cursor.execute("INSERT INTO transport_types (type) VALUES (?)", (transport_type_extracted,))
                    transport_type_id = cursor.lastrowid
                    logger.debug(f"Письмо ID {email_id}: Добавлен новый тип транспорта с id {transport_type_id}.")

                # === Детали транспорта (transport_details) ===
                logger.debug(f"Письмо ID {email_id}: Обработка деталей транспорта - Подтип: {transport_subtype}, Размер: {transport_size}")
                cursor.execute("SELECT id FROM transport_details WHERE transport_type_id = ? AND subtype = ? AND size = ?", 
                               (transport_type_id, transport_subtype, transport_size))
                transport_detail = cursor.fetchone()

                if transport_detail:
                    transport_id = transport_detail[0]
                    logger.debug(f"Письмо ID {email_id}: Найден существующий деталь транспорта с id {transport_id}.")
                else:
                    cursor.execute("""
                        INSERT INTO transport_details (transport_type_id, subtype, size) 
                        VALUES (?, ?, ?)
                    """, (transport_type_id, transport_subtype, transport_size))
                    transport_id = cursor.lastrowid
                    logger.debug(f"Письмо ID {email_id}: Добавлена новая деталь транспорта с id {transport_id}.")

                # === Цены (prices) ===
                logger.debug(f"Письмо ID {email_id}: Добавление цены - transport_id: {transport_id}, route_id: {route_id}, цена: {structured_price}")
                cursor.execute("INSERT INTO prices (transport_id, route_id, price, email_id) VALUES (?, ?, ?, ?)", 
                               (transport_id, route_id, structured_price, email_id))
                logger.debug(f"Письмо ID {email_id}: Добавлена новая запись в таблицу 'prices'.")
            else:
                logger.warning(f"Письмо ID {email_id}: Тип транспорта отсутствует. Цены не будут добавлены.")

            # Отмечаем письмо как обработанное для миграции
            cursor.execute("UPDATE emails SET migration_processed = 1 WHERE id = ?", (email_id,))
            logger.debug(f"Письмо ID {email_id}: Флаг 'migration_processed' обновлён.")

            # Коммит всех изменений для текущего письма
            conn.commit()
            logger.debug(f"Письмо ID {email_id}: Транзакция зафиксирована.")
            processed_emails += 1
            logger.info(f"Письмо ID {email_id}: Успешно обработано.")

        except Exception as e:
            # Откат транзакции в случае ошибки
            conn.rollback()
            logger.error(f"Письмо ID {email_id}: Ошибка при обработке: {e}")
            logger.exception("Трассировка ошибки:")
            skipped_emails += 1
            continue

    # Логирование итогов
    logger.info(f"Итоги обработки: Всего писем: {total_emails}, Обработано: {processed_emails}, Пропущено: {skipped_emails}")

    # Закрытие соединения
    try:
        conn.close()
        logger.debug("Соединение с базой данных закрыто.")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с базой данных: {e}")

    print("Данные успешно структурированы и перенесены.")

if __name__ == "__main__":
    analyze_and_migrate()
