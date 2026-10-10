"""Только явно разрешенная одноразовая БД, без подключения по рабочему .env."""

import importlib.util
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import psycopg2
from psycopg2.extensions import parse_dsn

import etl


@unittest.skipUnless(
    os.environ.get('STAGE1_ALLOW_DB_WRITE') == '1' and os.environ.get('STAGE1_TEST_DSN'),
    'Нужны отдельное разрешение и STAGE1_ALLOW_DB_WRITE=1 / STAGE1_TEST_DSN',
)
class IsolatedPostgresTests(unittest.TestCase):
    def test_migration_import_crud_repeat_conflict_and_audit(self):
        dsn = os.environ['STAGE1_TEST_DSN']
        settings = parse_dsn(dsn)
        self.assertEqual(settings.get('dbname'), 'stage1_etl_test')
        self.assertTrue(settings.get('host', '').startswith('/private/tmp/'))
        self.assertEqual(settings.get('port'), '55435')
        expected_data_dir = str(Path(settings['host']) / 'data')
        connect = lambda: psycopg2.connect(dsn)
        connection = connect()
        self.addCleanup(connection.close)
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_setting('data_directory'), current_setting('listen_addresses')")
            self.assertEqual(cursor.fetchone(), ('stage1_etl_test', expected_data_dir, ''))
            cursor.execute('SELECT 1 FROM pg_namespace WHERE nspname = %s', (etl.SCHEMA_NAME,))
            self.assertIsNone(cursor.fetchone(), 'Нужна пустая одноразовая БД: существующую схему тест не удаляет.')
            cursor.execute((etl.ROOT_DIR / 'schema.sql').read_text(encoding='utf-8'))
            cursor.execute('INSERT INTO partners (company_name,partner_type,inn,contact_email,rating) VALUES (%s,%s,%s,%s,%s) RETURNING partner_id',
                           ('Проба', 'ООО', '9999999999', 'fresh@example.test', 6))
            self.assertEqual(cursor.fetchone()[0], 1)
        connection.rollback()
        with connection:
            with connection.cursor() as cursor:
                # Минимальная исходная версия для проверки перехода без потери данных.
                cursor.execute('''
                    CREATE SCHEMA practice_2026_10_05;
                    SET search_path TO practice_2026_10_05;
                    CREATE TABLE partners (
                        partner_id INTEGER PRIMARY KEY, company_name VARCHAR(255) NOT NULL,
                        partner_type VARCHAR(30) NOT NULL, inn VARCHAR(12) NOT NULL UNIQUE,
                        contact_email VARCHAR(255) NOT NULL UNIQUE, phone VARCHAR(20),
                        rating DECIMAL(3,2) NOT NULL DEFAULT 0 CHECK (rating >= 0 AND rating <= 5),
                        address VARCHAR(500), director VARCHAR(255)
                    );
                    CREATE TABLE products (
                        product_id INTEGER PRIMARY KEY, product_name VARCHAR(255) NOT NULL UNIQUE,
                        list_price DECIMAL(12,2) NOT NULL
                    );
                    CREATE TABLE sales_history (
                        sale_id INTEGER PRIMARY KEY,
                        partner_id INTEGER NOT NULL REFERENCES partners(partner_id),
                        product_id INTEGER NOT NULL REFERENCES products(product_id),
                        sale_date DATE NOT NULL, quantity INTEGER NOT NULL,
                        unit_price_at_sale DECIMAL(12,2) NOT NULL
                    );
                ''')
                cursor.execute('INSERT INTO partners (partner_id,company_name,partner_type,inn,contact_email,rating) VALUES (%s,%s,%s,%s,%s,%s)',
                               (50, 'Пользователь', 'ООО', '1234567890', 'user@example.test', 3))
                cursor.execute('INSERT INTO products VALUES (%s,%s,%s)', (500, 'Старый товар', Decimal('99.99')))
                cursor.execute('INSERT INTO sales_history VALUES (%s,%s,%s,%s,%s,%s)',
                               (5000, 50, 500, '2020-01-01', 3, Decimal('1.25')))
        with tempfile.TemporaryDirectory() as directory, patch.object(etl, 'get_connection', side_effect=connect):
            report = Path(directory) / 'rejections.csv'
            first = etl.run_etl(output_path=report)
            self.assertEqual(first['partners']['inserted'], 5)
            second = etl.run_etl(output_path=report)
            self.assertTrue(all(value['inserted'] == 0 for value in second.values()))
            backend_path = etl.ROOT_DIR.parent / 'Разработка UI, навигации и CRUD-форм' / 'server.py'
            spec = importlib.util.spec_from_file_location('stage1_backend', backend_path)
            backend = importlib.util.module_from_spec(spec)
            # Соединение не мокируется: вызывается настоящий get_db_connection приложения.
            with patch.dict(os.environ, {
                'DB_HOST': settings['host'], 'DB_PORT': settings['port'],
                'DB_NAME': settings['dbname'], 'DB_USER': settings['user'],
                'DB_PASSWORD': '', 'DB_SCHEMA': etl.SCHEMA_NAME,
            }):
                spec.loader.exec_module(backend)
                partner_id = backend.save_partner(None, {
                    'company_name': 'Новый', 'partner_type': 'ИП', 'inn': '123456789012',
                    'email': 'new@example.test', 'rating': 6,
                })
                self.assertGreater(partner_id, 50)
                self.assertEqual(backend.get_partner(partner_id)['rating'], 6)
                self.assertEqual(backend.get_partner_history(partner_id)['rows'], [])
                self.assertEqual(len(backend.list_partners()), 7)
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT sale_amount FROM sales_history WHERE sale_id=%s', (5000,))
                    self.assertEqual(cursor.fetchone()[0], Decimal('3.75'))
                    for inn, rating in [('12345678901', 0), ('9999999999', -1)]:
                        cursor.execute('SAVEPOINT invalid_input')
                        with self.assertRaises(psycopg2.IntegrityError):
                            cursor.execute('INSERT INTO partners (company_name,partner_type,inn,contact_email,rating) VALUES (%s,%s,%s,%s,%s)',
                                           ('Ошибка', 'ООО', inn, 'invalid@example.test', rating))
                        cursor.execute('ROLLBACK TO SAVEPOINT invalid_input')
                    cursor.execute('SELECT * FROM data_quality_checks WHERE invalid_count <> 0')
                    self.assertEqual(cursor.fetchall(), [])
                    cursor.execute('SELECT count(*) FROM partners')
                    self.assertEqual(cursor.fetchone()[0], 7)
            third = etl.run_etl(output_path=report)
            self.assertTrue(all(value['inserted'] == 0 for value in third.values()))
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute('UPDATE partners SET company_name=%s WHERE partner_id=%s', ('Изменено вручную', 1))
            partners, products, sales, rejected = etl.transform_sources()
            partners.insert(0, (90, 'До конфликта', 'ООО', '9876543210', 'rollback@example.test'))
            with patch.object(etl, 'transform_sources', return_value=(partners, products, sales, rejected)):
                with self.assertRaisesRegex(ValueError, 'Конфликт'):
                    etl.run_etl(output_path=report)
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT company_name FROM partners WHERE partner_id=%s', (1,))
                    self.assertEqual(cursor.fetchone()[0], 'Изменено вручную')
                    cursor.execute('SELECT count(*) FROM partners WHERE partner_id=%s', (90,))
                    self.assertEqual(cursor.fetchone()[0], 0)
                    cursor.execute('SELECT count(*) FROM partners')
                    self.assertEqual(cursor.fetchone()[0], 7)
        # Весь read-only скрипт должен исполняться, даже если эталон уже изменен пользователем.
        with connection.cursor() as cursor:
            cursor.execute((etl.ROOT_DIR / 'select_count.sql').read_text(encoding='utf-8'))
