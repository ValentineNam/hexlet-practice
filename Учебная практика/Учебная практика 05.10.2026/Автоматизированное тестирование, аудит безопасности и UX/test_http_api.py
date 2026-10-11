"""Real HTTP transport; all PostgreSQL connections are blocked in this suite."""
import json
import sys
import threading
import unittest
from decimal import Decimal
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Разработка UI, навигации и CRUD-форм'))
import server


class HttpApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_guard = patch.object(server.psycopg2, 'connect', side_effect=AssertionError('Database forbidden in unit tests'))
        cls.database_guard.start()
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.AppHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)
        cls.database_guard.stop()

    def request(self, path, method='GET', payload=None, raw=None):
        body = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        request = Request(self.base + path, data=body, method=method, headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_list_empty_and_missing_partner(self):
        with patch.object(server, 'list_partners', return_value=[]):
            self.assertEqual(self.request('/api/partners'), (200, []))
        for path, method in [('/api/partners/999', 'get_partner'), ('/api/partners/999/history', 'get_partner_history')]:
            with self.subTest(path=path), patch.object(server, method, return_value=None):
                self.assertEqual(self.request(path)[0], 404)

    def test_history_empty(self):
        result = {'partner': {'id': 1, 'company_name': 'Тест'}, 'rows': []}
        with patch.object(server, 'get_partner_history', return_value=result) as operation:
            self.assertEqual(self.request('/api/partners/1/history'), (200, result))
            operation.assert_called_once_with(1)

    def test_create_update_and_missing_update(self):
        for method, path, partner_id, status in [('POST', '/api/partners', None, 201), ('PUT', '/api/partners/12', 12, 200)]:
            with self.subTest(method=method), patch.object(server, 'save_partner', return_value=12) as save:
                self.assertEqual(self.request(path, method, {'rating': 0}), (status, {'id': 12}))
                save.assert_called_once_with(partner_id, {'rating': 0})
        with patch.object(server, 'save_partner', return_value=None):
            self.assertEqual(self.request('/api/partners/999', 'PUT', {})[0], 404)

    def test_invalid_json_and_partner_data(self):
        for method, path in [('POST', '/api/partners'), ('PUT', '/api/partners/1'), ('POST', '/api/material/calculate')]:
            for raw in [b'{', b'[]', b'null', b'{}']:
                with self.subTest(method=method, path=path, raw=raw):
                    self.assertEqual(self.request(path, method, raw=raw)[0], 400)

    def test_database_failure_is_safe(self):
        secret = 'INTERNAL_TRACE_PASSWORD_SENTINEL'
        for path, operation in [('/api/partners', 'list_partners'), ('/api/partners/1', 'get_partner'), ('/api/partners/1/history', 'get_partner_history')]:
            with self.subTest(path=path), patch.object(server, operation, side_effect=RuntimeError(secret)):
                status, payload = self.request(path)
                self.assertEqual(status, 500)
                self.assertNotIn(secret, json.dumps(payload))
        with patch.object(server, 'save_partner', side_effect=RuntimeError(secret)):
            for method, path in [('POST', '/api/partners'), ('PUT', '/api/partners/1')]:
                status, payload = self.request(path, method, {})
                self.assertEqual(status, 500)
                self.assertNotIn(secret, json.dumps(payload))

    def test_catalog_failure_is_service_unavailable(self):
        with patch.object(server.material_catalogs, 'get_db_connection', side_effect=server.psycopg2.OperationalError('internal connection detail')):
            status, payload = self.request('/api/material/catalogs')
            self.assertEqual(status, 503)
            self.assertNotIn('internal connection detail', json.dumps(payload))
            status, payload = self.request('/api/material/calculate', 'POST', self.parameters())
            self.assertEqual(status, 503)
            self.assertNotIn('internal connection detail', json.dumps(payload))

    @staticmethod
    def parameters():
        return dict(product_type_id=1, material_type_id=2, quantity=100, param_1='1', param_2='1')

    def test_calculation_and_decimal_transport(self):
        with patch.object(server.material_module, 'get_coefficients', return_value=(Decimal('1.2'), Decimal('5'))):
            self.assertEqual(self.request('/api/material/calculate', 'POST', self.parameters()), (200, {'material_requirement': 126}))
        payload = self.parameters() | dict(quantity=1, param_1='1.00000000000000000000000000001')
        with patch.object(server.material_module, 'get_coefficients', return_value=(Decimal('1'), Decimal('0'))):
            self.assertEqual(self.request('/api/material/calculate', 'POST', payload), (200, {'material_requirement': 2}))

    def test_invalid_calculator_values(self):
        for change in [dict(quantity=-1), dict(product_type_id=0), dict(param_1='wrong'), dict(param_2='-1')]:
            with self.subTest(change=change):
                self.assertEqual(self.request('/api/material/calculate', 'POST', self.parameters() | change), (200, {'material_requirement': -1}))
        with patch.object(server.material_module, 'get_coefficients', return_value=None):
            self.assertEqual(self.request('/api/material/calculate', 'POST', self.parameters()), (200, {'material_requirement': -1}))


if __name__ == '__main__':
    unittest.main()
