import logging
from openai_connection import get_openai_client
from outlook_connection import get_outlook_messages
from email_body_splitter import EmailBodySplitter
from database_connection import setup_database, insert_email, email_exists_in_db, get_emails_from_db

# Импортируем модуль logging для ведения журнала событий
# Импортируем функции для подключения к OpenAI и Outlook
# Импортируем класс для разделения тела письма на основное и историю переписки
# Импортируем функции для работы с базой данных: настройка, вставка, проверка существования и получение писем

def setup_logging():
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,  # Уровень логирования - информационный
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщений
        handlers=[
            logging.FileHandler("email_processing.log", encoding='utf-8'),  # Запись в файл с указанием кодировки
            logging.StreamHandler()  # Вывод в консоль
        ]
    )

def refers_to_thread(main_body):
    # Функция для проверки, ссылается ли основное тело письма на историю переписки
    thread_keywords = [
        'см. ниже', 'смотрите ниже', 'см. переписку', 'как обсуждалось', 'как договорились',
        'see below', 'as per our conversation', 'please find below', 'как обсуждали ранее'
    ]
    for keyword in thread_keywords:
        # Перебираем ключевые фразы
        if keyword.lower() in main_body.lower():
            # Если ключевая фраза найдена в тексте, возвращаем True
            return True
    return False  # Иначе возвращаем False

def extract_transportation_info(client, body):
    # Функция для извлечения информации о перевозке из текста письма с помощью OpenAI
    logger = logging.getLogger("EmailProcessor")  # Получаем логгер
    try:
        # Формируем запрос (prompt) для модели OpenAI
        prompt = f"""
Вы помощник, который извлекает информацию из писем, связанных с перевозками и ценовыми предложениями, для дальнейшего анализа.
Пожалуйста, прочитайте следующее письмо и извлеките информацию о перевозке, сосредоточившись на ключевых деталях, таких как:

- Тип запроса (котировка, запрос на перевозку, запрос цены)
- Место отправления
- Место назначения
- Детали груза
- Даты
- Цена
- Дополнительная информация

Письмо:
\"\"\"
{body}
\"\"\"

Пожалуйста, предоставьте извлеченную информацию в следующем формате:

Тип запроса:
Место отправления:
Место назначения:
Детали груза:
Даты:
Цена:
Дополнительная информация:

Если письмо не связано с перевозкой или вы не можете извлечь достаточную информацию, ответьте "Нет информации о перевозке".
"""

        # Отправляем запрос в OpenAI API и получаем ответ
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Указываем модель
            messages=[
                {"role": "system", "content": "Вы полезный помощник."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Температура для генерации (степень случайности)
            max_tokens=500,  # Максимальное количество токенов в ответе
        )
        answer = response.choices[0].message.content.strip()  # Извлекаем ответ из ответа API

        if "Нет информации о перевозке" in answer:
            # Если в ответе указано, что информации нет, возвращаем None
            return None
        else:
            # Иначе обрабатываем ответ и извлекаем данные
            lines = answer.split('\n')  # Разбиваем ответ на строки
            data = {}
            current_field = ''
            for line in lines:
                if ':' in line:
                    # Если в строке есть двоеточие, считаем это новым полем
                    key, value = line.split(':', 1)
                    data[key.strip().lower()] = value.strip()
                    current_field = key.strip().lower()
                elif current_field:
                    # Если продолжается предыдущее поле, добавляем информацию
                    data[current_field] += ' ' + line.strip()

            return data  # Возвращаем словарь с извлеченными данными
    except Exception as e:
        # Обрабатываем исключения, если возникли ошибки при обращении к API
        logger.error(f"Ошибка при обращении к OpenAI API: {e}")
        logger.exception("Трассировка ошибки:")
        return None  # Возвращаем None в случае ошибки

def process_emails():
    # Главная функция для обработки писем
    logger = logging.getLogger("EmailProcessor")  # Получаем логгер
    client = get_openai_client()  # Получаем клиент OpenAI
    if not client:
        # Если не удалось получить клиента, логируем ошибку и завершаем функцию
        logger.error("Не удалось получить клиент OpenAI.")
        return

    # Подключаемся к базе данных
    conn, cursor = setup_database()
    splitter = EmailBodySplitter(logger=logger)  # Создаем экземпляр класса для разделения тела письма

    # Обработка писем из Outlook
    messages = get_outlook_messages()  # Получаем сообщения из Outlook
    if not messages:
        # Если не удалось получить сообщения, логируем ошибку и завершаем функцию
        logger.error("Не удалось получить сообщения из Outlook.")
        return

    # Сортируем сообщения по дате получения, от старых к новым
    messages.Sort("[ReceivedTime]", False)

    message = messages.GetFirst()  # Получаем первое сообщение
    while message:
        try:
            if message.Class == 43:  # Проверяем, является ли элемент почтовым сообщением
                entry_id = message.EntryID  # Получаем уникальный идентификатор письма

                # Проверяем, было ли письмо уже обработано (есть ли оно в базе данных)
                if email_exists_in_db(cursor, entry_id):
                    logger.info(f"Письмо с EntryID {entry_id} уже существует в базе данных. Пропускаем.")
                    message = messages.GetNext()  # Переходим к следующему сообщению
                    continue

                # Извлекаем данные письма
                subject = message.Subject  # Тема письма
                sender = message.SenderName  # Имя отправителя
                received_time = message.ReceivedTime.strftime("%Y-%m-%d %H:%M:%S")  # Время получения
                full_body = message.Body  # Полное тело письма

                # Разделяем тело письма на основное и историю переписки
                main_body, history_body = splitter.split_body(full_body)

                # Решаем, какое тело использовать для анализа
                body_to_analyze = main_body
                if len(main_body) < 50 or refers_to_thread(main_body):
                    # Если основное тело короткое или ссылается на переписку, добавляем историю
                    body_to_analyze = main_body + "\n" + (history_body or "")
                    logger.debug("Используем основное письмо вместе с историей для анализа.")

                # Извлекаем информацию о перевозке с помощью OpenAI
                transportation_info = extract_transportation_info(client, body_to_analyze)

                if transportation_info:
                    # Если удалось извлечь информацию, проверяем наличие цены или типа запроса
                    price = transportation_info.get('цена', '').strip()
                    request_type = transportation_info.get('тип запроса', '').strip().lower()

                    if price or 'запрос' in request_type:
                        # Если есть цена или указание на запрос, формируем данные для сохранения
                        email_data = {
                            'entry_id': entry_id,
                            'subject': subject,
                            'sender': sender,
                            'received_time': received_time,
                            'body': full_body,
                            'request_type': transportation_info.get('тип запроса', ''),
                            'origin': transportation_info.get('место отправления', ''),
                            'destination': transportation_info.get('место назначения', ''),
                            'cargo_details': transportation_info.get('детали груза', ''),
                            'dates': transportation_info.get('даты', ''),
                            'price': price,
                            'additional_info': transportation_info.get('дополнительная информация', ''),
                            'processed': 1  # Помечаем как обработанное
                        }
                        insert_email(cursor, email_data)  # Вставляем данные в базу данных
                        logger.info(f"Письмо от {sender} от {received_time} обработано и сохранено.")
                    else:
                        # Если нет цены или запроса, логируем информацию
                        logger.info(f"Письмо от {sender} от {received_time} не содержит котировку или запрос на перевозку.")
                else:
                     # Добавляем письмо в базу данных как обработанное без информации о перевозке
                     email_data = {
                            'entry_id': entry_id,
                            'subject': subject,
                            'sender': sender,
                            'received_time': received_time,
                            'body': full_body,
                            'request_type': '',
                            'origin': '',
                            'destination': '',
                            'cargo_details': '',
                            'dates': '',
                            'price': '',
                            'additional_info': '',
                            'processed': 1  # Помечаем как обработанное
                         }
                insert_email(cursor, email_data)
                logger.info(f"Письмо от {sender} от {received_time} не содержит информации о перевозке и сохранено в базе данных.")
  
               
            else:
                # Если элемент не является почтовым сообщением, логируем отладочную информацию
                logger.debug("Пропущен элемент, который не является почтовым сообщением.")
        except Exception as e:
            # Обрабатываем исключения, возникшие при обработке письма
            logger.error(f"Ошибка при обработке письма: {e}")
            logger.exception("Трассировка ошибки:")
        message = messages.GetNext()  # Переходим к следующему сообщению

    # Обработка писем из базы данных (повторная обработка необработанных писем)
    emails_from_db = get_emails_from_db(cursor)
    for email_record in emails_from_db:
        try:
            # Распаковываем данные письма из записи базы данных
            (id, entry_id, subject, sender, received_time, body, request_type,
             origin, destination, cargo_details, dates, price, additional_info, processed) = email_record

            # Если письмо уже обработано, пропускаем его
            if processed:
                continue

            # Разделяем тело письма на основное и историю переписки
            main_body, history_body = splitter.split_body(body)

            # Решаем, какое тело использовать для анализа
            body_to_analyze = main_body
            if len(main_body) < 50 or refers_to_thread(main_body):
                # Если основное тело короткое или ссылается на переписку, добавляем историю
                body_to_analyze = main_body + "\n" + (history_body or "")
                logger.debug("Используем основное письмо вместе с историей для анализа.")

            # Извлекаем информацию о перевозке с помощью OpenAI
            transportation_info = extract_transportation_info(client, body_to_analyze)

            if transportation_info:
                # Если удалось извлечь информацию, проверяем наличие цены или типа запроса
                price = transportation_info.get('цена', '').strip()
                request_type = transportation_info.get('тип запроса', '').strip().lower()

                if price or 'запрос' in request_type:
                    # Если есть цена или указание на запрос, обновляем данные письма в базе данных
                    cursor.execute('''
                        UPDATE emails SET
                            request_type = ?,
                            origin = ?,
                            destination = ?,
                            cargo_details = ?,
                            dates = ?,
                            price = ?,
                            additional_info = ?,
                            processed = 1
                        WHERE id = ?
                    ''', (
                        transportation_info.get('тип запроса', ''),
                        transportation_info.get('место отправления', ''),
                        transportation_info.get('место назначения', ''),
                        transportation_info.get('детали груза', ''),
                        transportation_info.get('даты', ''),
                        price,
                        transportation_info.get('дополнительная информация', ''),
                        id
                    ))
                    conn.commit()  # Сохраняем изменения в базе данных
                    logger.info(f"Письмо из базы данных с ID {id} обработано и обновлено.")
                else:
                    # Если нет цены или запроса, логируем информацию
                    logger.info(f"Письмо из базы данных с ID {id} не содержит котировку или запрос на перевозку.")
            else:
                # Если не удалось извлечь информацию о перевозке, логируем информацию
                logger.info(f"Письмо из базы данных с ID {id} не содержит информации о перевозке.")

        except Exception as e:
            # Обрабатываем исключения, возникшие при обработке письма из базы данных
            logger.error(f"Ошибка при обработке письма из базы данных: {e}")
            logger.exception("Трассировка ошибки:")

    # Закрываем соединение с базой данных после обработки всех писем
    conn.close()

if __name__ == "__main__":
    # Если скрипт запускается напрямую, а не импортируется как модуль
    setup_logging()  # Настраиваем логирование
    process_emails()  # Запускаем процесс обработки писем
