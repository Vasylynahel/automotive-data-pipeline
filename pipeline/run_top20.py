import psycopg2

from parsers.parser_top_20 import run as scrape_top20
from pipeline.db import DB_CONFIG, CREATE_TABLE_SQL, run_pipeline_once


def main():
    records = scrape_top20()
    print(f"Зібрано записів: {len(records)}")

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)

    run_pipeline_once(cursor, records, mark_missing=True)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()