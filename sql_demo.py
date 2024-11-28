import sqlite3

# Подключение к базе данных (если файла не существует, он будет создан)
conn = sqlite3.connect("car_parts.db")
cursor = conn.cursor()

# Создание таблицы
cursor.execute("""
CREATE TABLE IF NOT EXISTS car_parts_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- Уникальный идентификатор записи
    part_type TEXT NOT NULL,              -- Категория запчасти
    car_model TEXT NOT NULL,              -- Модель автомобиля
    price REAL NOT NULL                   -- Цена запчасти
);
""")

# Данные для вставки
data = [
    ('кузов', 'Camry', 2000.00),
    ('кузов', 'Land cruiser', 3000.00),
    ('кузов', 'Pajero', 2500.00),
    ('кузов', 'Passat', 1800.00),
    ('кузов', 'Malibu', 2200.00),
    ('двигатель', 'Camry', 5000.00),
    ('двигатель', 'Land cruiser', 7000.00),
    ('двигатель', 'Pajero', 6500.00),
    ('двигатель', 'Passat', 4800.00),
    ('двигатель', 'Malibu', 5200.00),
    ('АКПП', 'Camry', 3000.00),
    ('АКПП', 'Land cruiser', 4500.00),
    ('АКПП', 'Pajero', 4000.00),
    ('АКПП', 'Passat', 3500.00),
    ('АКПП', 'Malibu', 3700.00)
]

# Вставка данных в таблицу
cursor.executemany("""
INSERT INTO car_parts_prices (part_type, car_model, price)
VALUES (?, ?, ?);
""", data)

# Сохранение изменений и закрытие соединения
conn.commit()
conn.close()

print("Таблица создана и данные успешно добавлены.")
