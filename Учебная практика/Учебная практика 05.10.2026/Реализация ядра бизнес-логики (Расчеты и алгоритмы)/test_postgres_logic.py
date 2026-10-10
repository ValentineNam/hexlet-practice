"""PostgreSQL + HTTP: изменения каждого сценария откатываются."""

import importlib.util
import json
import os
import threading
import unittest
from decimal import Decimal
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import psycopg2
from psycopg2.extensions import parse_dsn

import material_calculator
import material_catalogs
from discount import calculate_partner_discount


class BorrowedConnection:
    """Backend использует настоящие SQL-запросы внутри откатываемой тестовой транзакции."""
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self, *args, **kwargs):
        return self.connection.cursor(*args, **kwargs)

    def close(self):
        pass


@unittest.skipUnless(os.environ.get('STAGE2_ALLOW_DB_WRITE') == '1' and os.environ.get('STAGE2_TEST_DSN'),
                     'Требуется явно разрешенная изолированная PostgreSQL')
class PostgresBusinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'Разработка UI, навигации и CRUD-форм' / 'server.py'
        spec = importlib.util.spec_from_file_location('stage2_backend', path)
        cls.backend = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.backend)

    def setUp(self):
        dsn = os.environ['STAGE2_TEST_DSN']
        settings = parse_dsn(dsn)
        self.assertEqual(settings.get('dbname'), 'stage1_etl_test')
        self.assertEqual(settings.get('host'), '/private/tmp/stage1-etl.bxjg75')
        self.assertEqual(settings.get('port'), '55435')
        self.connection = psycopg2.connect(dsn)
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        self.cursor = self.connection.cursor()
        self.cursor.execute("SELECT current_database(), current_setting('data_directory'), current_setting('listen_addresses')")
        self.assertEqual(self.cursor.fetchone(), ('stage1_etl_test', settings['host'] + '/data', ''))
        self.cursor.execute('SET LOCAL search_path TO practice_2026_10_05')
        self.before = self.snapshot()
        borrowed = BorrowedConnection(self.connection)
        for module in (material_catalogs, self.backend):
            patcher = patch.object(module, 'get_db_connection', return_value=borrowed)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), self.backend.AppHandler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.http.server_close)
        self.addCleanup(self.thread.join)
        self.addCleanup(self.http.shutdown)

    def snapshot(self):
        result = []
        for table, key in (('partners', 'partner_id'), ('products', 'product_id'), ('sales_history', 'sale_id'),
                           ('product_types', 'product_type_id'), ('material_types', 'material_type_id')):
            from psycopg2 import sql
            self.cursor.execute(sql.SQL('SELECT * FROM practice_2026_10_05.{} ORDER BY {}').format(sql.Identifier(table), sql.Identifier(key)))
            result.append(self.cursor.fetchall())
        return result

    def tearDown(self):
        self.connection.rollback()
        self.assertEqual(self.snapshot(), self.before, 'Тест изменил сохраненные данные')

    def request(self, path, payload=None):
        client = HTTPConnection(*self.http.server_address, timeout=5)
        try:
            client.request('GET' if payload is None else 'POST', path,
                           body=None if payload is None else json.dumps(payload),
                           headers={'Content-Type': 'application/json'})
            response = client.getresponse()
            return response.status, json.loads(response.read())
        finally:
            client.close()

    def payload(self, **changes):
        result = dict(product_type_id=1, material_type_id=2, quantity=100, param_1=1, param_2=1)
        result.update(changes)
        return result

    def test_production_connection_configuration(self):
        from database import get_db_connection
        with patch.dict(os.environ, {
            'DB_HOST': '/private/tmp/stage1-etl.bxjg75', 'DB_PORT': '55435',
            'DB_NAME': 'stage1_etl_test', 'DB_USER': 'v.nam', 'DB_PASSWORD': '',
            'DB_SCHEMA': 'practice_2026_10_05',
        }), patch.object(material_catalogs, 'get_db_connection', side_effect=get_db_connection):
            self.assertEqual(material_calculator.calculate_material_requirement(1, 2, 100, 1, 1), 126)
            self.assertEqual(self.request('/api/material/calculate', self.payload()), (200, {'material_requirement': 126}))
            self.assertEqual(self.request('/api/material/catalogs')[0], 200)

    def test_database_coefficients_change_core_and_http_result(self):
        self.cursor.execute('UPDATE product_types SET coefficient=%s WHERE product_type_id=%s', (Decimal('2'), 1))
        self.cursor.execute('UPDATE material_types SET scrap_percentage=%s WHERE material_type_id=%s', (Decimal('10'), 2))
        self.assertEqual(material_calculator.calculate_material_requirement(1, 2, 100, 1, 1), 220)
        self.assertIs(self.backend.material_module, material_calculator)
        status, body = self.request('/api/material/calculate', self.payload())
        self.assertEqual((status, body['material_requirement']), (200, 220))
        status, body = self.request('/api/material/catalogs')
        self.assertEqual(status, 200)
        self.assertEqual(Decimal(body['product_types'][0]['coefficient']), Decimal('2'))
        self.assertEqual(Decimal(body['material_types'][1]['scrap_percentage']), Decimal('10'))

    def test_unknown_and_deleted_catalog_records(self):
        self.cursor.execute('DELETE FROM material_types WHERE material_type_id=%s', (2,))
        for payload in (self.payload(), self.payload(product_type_id=999), self.payload(param_1=-1)):
            self.assertEqual(self.request('/api/material/calculate', payload), (200, {'material_requirement': -1}))

    def test_empty_catalogs_and_missing_table_have_predictable_errors(self):
        self.cursor.execute('DELETE FROM product_types')
        self.assertEqual(self.request('/api/material/catalogs')[0], 503)
        self.assertEqual(self.request('/api/material/calculate', self.payload())[1]['material_requirement'], -1)
        self.cursor.execute('ALTER TABLE material_types RENAME TO temporarily_missing_material_types')
        self.assertEqual(self.request('/api/material/catalogs')[0], 503)
        self.connection.rollback()
        self.cursor.execute('SET LOCAL search_path TO practice_2026_10_05')
        self.cursor.execute('ALTER TABLE material_types RENAME TO temporarily_missing_material_types')
        self.assertEqual(self.request('/api/material/calculate', self.payload())[0], 503)

    def test_actual_connection_failure_has_no_dictionary_fallback(self):
        with patch.object(material_catalogs, 'get_db_connection', side_effect=lambda: psycopg2.connect(
            host='/private/tmp/stage1-etl.bxjg75/no-such-socket', port=55435,
            dbname='stage1_etl_test', user='v.nam', connect_timeout=1,
        )):
            self.assertEqual(self.request('/api/material/catalogs')[0], 503)
            self.assertEqual(self.request('/api/material/calculate', self.payload())[0], 503)

    def test_decimal_rounding_http_and_bad_payload(self):
        self.cursor.execute('UPDATE product_types SET coefficient=%s WHERE product_type_id=%s', (1, 1))
        self.cursor.execute('UPDATE material_types SET scrap_percentage=%s WHERE material_type_id=%s', (0, 2))
        payload = self.payload(quantity=1, param_1='1.00000000000000000000000000001')
        self.assertEqual(self.request('/api/material/calculate', payload), (200, {'material_requirement': 2}))
        self.assertEqual(self.request('/api/material/calculate', {} )[0], 400)
        self.assertEqual(self.request('/api/material/calculate', self.payload(param_1='bad'))[1]['material_requirement'], -1)

    def test_sale_aggregation_thresholds_and_partner_without_sales(self):
        for index, total in enumerate((0, 9999, 10000, 49999, 50000, 299999, 300000)):
            partner_id = 2000 + index
            self.cursor.execute('INSERT INTO partners (partner_id,company_name,partner_type,inn,contact_email) VALUES (%s,%s,%s,%s,%s)',
                                (partner_id, 'Порог ' + str(total), 'ООО', str(9000000000 + index), f'boundary{index}@example.test'))
            if total:
                # Две строки доказывают SUM, а не использование одного значения.
                for offset, quantity in enumerate((1, total - 1)):
                    self.cursor.execute('INSERT INTO sales_history (sale_id,partner_id,product_id,sale_date,quantity,sale_amount) VALUES (%s,%s,%s,%s,%s,%s)',
                                        (20000 + index * 2 + offset, partner_id, 101, '2026-10-05', quantity, 1))
        status, partners = self.request('/api/partners')
        self.assertEqual(status, 200)
        by_id = {partner['id']: partner for partner in partners}
        for index, total in enumerate((0, 9999, 10000, 49999, 50000, 299999, 300000)):
            self.assertEqual(by_id[2000 + index]['discount'], calculate_partner_discount(total))
        self.assertEqual(self.request('/api/partners/2000/history')[1]['rows'], [])
