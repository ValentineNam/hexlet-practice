"""Единое подключение финального backend и справочников калькулятора."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = 'practice_2026_10_05'


def get_db_connection():
    load_dotenv(ROOT / 'Разработка UI, навигации и CRUD-форм' / '.env', override=False)
    load_dotenv(ROOT / 'Инфраструктура данных и ETL (База данных в 3NF)' / '.env', override=False)
    if os.environ.get('DB_SCHEMA', SCHEMA) != SCHEMA:
        raise ValueError(f'DB_SCHEMA должен быть {SCHEMA}.')
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'practice_2026_autumn'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        connect_timeout=5,
        options=f'-c search_path={SCHEMA}',
    )
