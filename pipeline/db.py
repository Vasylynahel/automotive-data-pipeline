"""
pipeline/db.py — уся логіка роботи з базою: схема, upsert, soft delete.
"""

import hashlib
import os
from datetime import datetime, timezone

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5433)),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
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
    updated_at    TIMESTAMPTZ NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    deleted_at    TIMESTAMPTZ
);
"""

UPSERT_SQL = """
INSERT INTO raw_companies (record_id, name, city, street, phone_number, content_hash, scraped_at, updated_at, is_active, deleted_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (record_id) DO UPDATE SET
    scraped_at = EXCLUDED.scraped_at,
    name = EXCLUDED.name,
    street = EXCLUDED.street,
    phone_number = EXCLUDED.phone_number,
    content_hash = EXCLUDED.content_hash,
    is_active = true,
    deleted_at = NULL,
    updated_at = CASE
        WHEN raw_companies.content_hash != EXCLUDED.content_hash
        THEN EXCLUDED.updated_at
        ELSE raw_companies.updated_at
    END;
"""


def make_record_id(city, name, street):
    """Стабільний ключ запису — не залежить від порядку обходу сторінок."""
    raw = f"{city}|{name}|{street}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def upsert_record(cursor, record):
    """Вставляє новий запис АБО оновлює існуючий (за record_id)."""
    content = f"{record['name']}|{record['street']}|{record['phoneNumber']}"
    content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    cursor.execute(
        UPSERT_SQL,
        (
            record["record_id"], record["name"], record["city"], record["street"],
            record["phoneNumber"], content_hash, record["scraped_at"], now,
            True, None,
        ),
    )


def mark_deleted(cursor, fresh_record_ids):
    """Позначає is_active=false для записів, яких немає у fresh_record_ids."""
    cursor.execute(
        "UPDATE raw_companies SET is_active = false, deleted_at = %s "
        "WHERE record_id != ALL(%s) AND is_active = true",
        (datetime.now(timezone.utc), fresh_record_ids),
    )


def run_pipeline_once(cursor, parsed_records):
    """Один повний прогін: upsert усіх свіжих записів + позначення видалених."""
    fresh_ids = []
    for record in parsed_records:
        upsert_record(cursor, record)
        fresh_ids.append(record["record_id"])

    mark_deleted(cursor, fresh_ids)
