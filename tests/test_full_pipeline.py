"""
Повний тестовий сценарій: усе, що ми зібрали докупи.

Логіка одного "прогону" (це те, що робитиме Airflow-задача щодня):
  1. Парсер повертає СПИСОК записів, які реально є на сайті ЗАРАЗ.
  2. Для кожного з них викликаємо upsert_record — це покриває
     "додалося" і "оновилося" (і "нічого не змінилось").
  3. Викликаємо mark_deleted зі списком record_id з кроку 1 —
     це покриває "видалилося".

Раунди нижче симулюють 4 різні дні роботи скрапера.
"""

import time
from datetime import datetime, timezone

import psycopg2

from pipeline.db import DB_CONFIG, CREATE_TABLE_SQL, make_record_id, run_pipeline_once


def fake_parser_output(include_shynomontazh=True, changed_phone=False):
    """Імітує те, що повертає реальний парсер: список словників."""
    raw = [
        {"name": "СТО Іванова", "city": "Львів", "street": "вул. Городоцька, 1",
         "phoneNumber": "+380679999999" if changed_phone else "+380671111111"},
        {"name": "АвтоМайстер", "city": "Київ", "street": "вул. Хрещатик, 5",
         "phoneNumber": "+380672222222"},
    ]
    if include_shynomontazh:
        raw.append({"name": "Шиномонтаж Плюс", "city": "Одеса",
                     "street": "вул. Дерибасівська, 10", "phoneNumber": "+380673333333"})

    for r in raw:
        r["scraped_at"] = datetime.now(timezone.utc).isoformat()
        r["record_id"] = make_record_id(r["city"], r["name"], r["street"])
    return raw


def print_table(cursor, title):
    cursor.execute(
        "SELECT name, phone_number, is_active, scraped_at, updated_at, deleted_at "
        "FROM raw_companies ORDER BY name;"
    )
    rows = cursor.fetchall()
    print(f"\n--- {title} ---")
    for name, phone, is_active, scraped_at, updated_at, deleted_at in rows:
        print(f"{name:20s} | active={str(is_active):5s} | phone={phone:15s} | "
              f"updated_at={updated_at} | deleted_at={deleted_at}")


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)

    run_pipeline_once(cursor, fake_parser_output())
    print_table(cursor, "Раунд 1: усі 3 записи нові")
    time.sleep(1.2)

    run_pipeline_once(cursor, fake_parser_output())
    print_table(cursor, "Раунд 2: без змін (очікуємо: updated_at той самий)")
    time.sleep(1.2)

    run_pipeline_once(cursor, fake_parser_output(changed_phone=True))
    print_table(cursor, "Раунд 3: змінився телефон (очікуємо: updated_at змінився тільки в СТО Іванова)")
    time.sleep(1.2)

    run_pipeline_once(cursor, fake_parser_output(include_shynomontazh=False, changed_phone=True))
    print_table(cursor, "Раунд 4: Шиномонтаж Плюс зник (очікуємо: active=False, deleted_at заповнений)")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()