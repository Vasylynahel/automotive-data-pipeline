"""
Тестовий скрипт для перевірки upsert-логіки.

Що робить:
  1. Створює таблицю raw_companies (якщо ще нема).
  2. Раунд 1: вставляє 3 тестові записи.
  3. Раунд 2: заново "завантажує" ТІ САМІ дані (нічого не змінилось) —
     scraped_at має оновитись, updated_at — НІ.
  4. Раунд 3: змінює телефон в одному записі і завантажує знову —
     тепер updated_at має змінитись ТІЛЬКИ для цього одного запису.

Підключення до Postgres бере з тих самих параметрів, що й у твоєму
docker-compose (стандартний airflow/astro сетап зазвичай піднімає
Postgres на localhost:5432 з користувачем postgres/postgres).
Якщо в тебе інакше — просто поправ DB_CONFIG нижче.
"""

import hashlib
import time
from datetime import datetime, timezone

import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "postgres",
    "user": "postgres",
    "password": "postgres",
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS raw_companies (
    record_id     TEXT PRIMARY KEY,
    name          TEXT,
    city          TEXT,
    street        TEXT,
    phone_number  TEXT,
    content_hash  TEXT NOT NULL,
    scraped_at    TIMESTAMPTZ NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL
);
"""

UPSERT_SQL = """
INSERT INTO raw_companies (record_id, name, city, street, phone_number, content_hash, scraped_at, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (record_id) DO UPDATE SET
    scraped_at = EXCLUDED.scraped_at,
    name = EXCLUDED.name,
    street = EXCLUDED.street,
    phone_number = EXCLUDED.phone_number,
    content_hash = EXCLUDED.content_hash,
    updated_at = CASE
        WHEN raw_companies.content_hash != EXCLUDED.content_hash
        THEN EXCLUDED.updated_at
        ELSE raw_companies.updated_at
    END;
"""

def mark_deleted(cursor, fresh_record_ids):
    # fresh_record_ids — список record_id, які щойно прийшли з парсера
    cursor.execute(
        "UPDATE raw_companies SET is_active = false, deleted_at = %s WHERE record_id != ALL(%s) AND is_active = true",
        (datetime.now(timezone.utc), fresh_record_ids)
    )

def make_record_id(city, name, street):
    raw = f"{city}|{name}|{street}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def upsert_record(cursor, record):
    content = f"{record['name']}|{record['street']}|{record['phoneNumber']}"
    content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    is_active = False

    cursor.execute(
        UPSERT_SQL,
        (
            record["record_id"],
            record["name"],
            record["city"],
            record["street"],
            record["phoneNumber"],
            content_hash,
            record["scraped_at"],
            record["is_active"]
            now,

        ),
    )


def make_test_records():
    """3 тестові записи, схожі на реальний вивід парсера top20.ua."""
    raw = [
        {"name": "СТО Іванова", "city": "Львів", "street": "вул. Городоцька, 1", "phoneNumber": "+380671111111"},
        {"name": "АвтоМайстер", "city": "Київ", "street": "вул. Хрещатик, 5", "phoneNumber": "+380672222222"},
        {"name": "Шиномонтаж Плюс", "city": "Одеса", "street": "вул. Дерибасівська, 10", "phoneNumber": "+380673333333"},
    ]
    for r in raw:
        r["scraped_at"] = datetime.now(timezone.utc).isoformat()
        r["record_id"] = make_record_id(r["city"], r["name"], r["street"])
    return raw


def print_table(cursor, title):
    cursor.execute(
        "SELECT name, phone_number, scraped_at, updated_at FROM raw_companies ORDER BY name;"
    )
    rows = cursor.fetchall()
    print(f"\n--- {title} ---")
    for name, phone, scraped_at, updated_at in rows:
        print(f"{name:20s} | {phone:15s} | scraped_at={scraped_at} | updated_at={updated_at}")


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute(CREATE_TABLE_SQL)

    # --- Раунд 1: перше завантаження ---
    records = make_test_records()
    for r in records:
        upsert_record(cursor, r)
    print_table(cursor, "Раунд 1: перше завантаження (все нове)")

    time.sleep(1.5)  # щоб scraped_at у раунді 2 точно відрізнявся від раунду 1

    # --- Раунд 2: ті самі дані, нічого не змінилось ---
    records = make_test_records()  # новий scraped_at, але зміст той самий
    for r in records:
        upsert_record(cursor, r)
    print_table(cursor, "Раунд 2: ті самі дані (очікуємо: scraped_at змінився, updated_at — НІ)")

    time.sleep(1.5)

    # --- Раунд 3: змінюємо телефон у ОДНОГО запису ---
    records = make_test_records()
    records[0]["phoneNumber"] = "+380679999999"  # "СТО Іванова" змінили номер
    for r in records:
        upsert_record(cursor, r)
    print_table(cursor, "Раунд 3: змінили телефон у 'СТО Іванова' (очікуємо: updated_at змінився ТІЛЬКИ в неї)")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
