"""
DAG: top20_pipeline

Щоденний запуск скрапінгу top20.ua + інкрементальне завантаження в Postgres.

mark_missing=False навмисно — поточна реалізація mark_deleted ще не має
захисту від ротації видачі сайту (missed_count). Вмикати тільки після
того, як цей захист буде доданий (див. README, "Відоме обмеження").
"""

from datetime import datetime, timedelta

import psycopg2
from airflow.sdk import dag, task

from parsers.parser_top_20 import run as scrape_top20
from pipeline.db import DB_CONFIG, CREATE_TABLE_SQL, run_pipeline_once


default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


@dag(
    dag_id="top20_pipeline",
    description="Scrape top20.ua and load into raw_companies with CDC-style upsert",
    schedule=None,  # запускаємо вручну, поки не перевіримо кілька разів
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["scraping", "cdc", "portfolio"],
)
def top20_pipeline():

    @task
    def extract():
        """Витягує список закладів з top20.ua. Повертає список dict — піде в XCom."""
        records = scrape_top20()
        return records

    @task
    def load(records: list):
        """Upsert усіх записів у Postgres. mark_missing=False — поки без soft delete."""
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(CREATE_TABLE_SQL)

        run_pipeline_once(cursor, records, mark_missing=False)

        cursor.close()
        conn.close()
        return len(records)

    load(extract())


top20_pipeline()
