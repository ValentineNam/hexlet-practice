import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

CRUD_DIR = (
    Path(__file__).resolve().parents[2]
    / 'Учебная практика 21.09.2026'
    / 'Интеграция формы с БД (CRUD-операции и обновление UI)'
)
sys.path.insert(0, str(CRUD_DIR))

backend_spec = importlib.util.spec_from_file_location(
    'audited_partner_backend',
    CRUD_DIR / 'server.py',
)
backend = importlib.util.module_from_spec(backend_spec)
sys.modules[backend_spec.name] = backend
backend_spec.loader.exec_module(backend)


class ParameterizedPartnerQueryTests(unittest.TestCase):
    def setUp(self):
        self.cursor = MagicMock()
        self.cursor.__enter__.return_value = self.cursor
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.connection.cursor.return_value = self.cursor

    @patch.object(backend, 'get_db_connection')
    def test_partner_id_is_bound_as_select_parameter(self, get_connection):
        get_connection.return_value = self.connection
        self.cursor.fetchone.return_value = None

        result = backend.get_partner(42)

        self.assertIsNone(result)
        query, parameters = self.cursor.execute.call_args.args
        self.assertIn('WHERE partner_id = %s', query)
        self.assertEqual(parameters, (42,))

    @patch.object(backend, 'get_db_connection')
    def test_insert_keeps_untrusted_company_name_out_of_sql(self, get_connection):
        get_connection.return_value = self.connection
        self.cursor.fetchone.return_value = (501,)
        injection_text = "ООО'); DROP TABLE partners; --"
        payload = {
            'company_name': injection_text,
            'partner_type': 'ООО',
            'rating': 3,
            'address': '',
            'director': '',
            'phone': '+79990000000',
            'inn': '1234567890',
            'email': 'audit@example.test',
        }

        result = backend.create_partner(payload)

        self.assertEqual(result, 501)
        query, parameters = self.cursor.execute.call_args.args
        self.assertEqual(query.count('%s'), 8)
        self.assertIn(injection_text, parameters)
        self.assertNotIn(injection_text, query)

    @patch.object(backend, 'get_db_connection')
    def test_update_values_and_id_are_bound_separately(self, get_connection):
        get_connection.return_value = self.connection
        self.cursor.fetchone.return_value = (42,)
        injection_text = "ООО' OR '1'='1"
        payload = {
            'company_name': injection_text,
            'partner_type': 'ООО',
            'rating': 2,
            'address': '',
            'director': '',
            'phone': '',
            'inn': '1234567890',
            'email': 'audit-update@example.test',
        }

        result = backend.update_partner(42, payload)

        self.assertEqual(result, 42)
        query, parameters = self.cursor.execute.call_args.args
        self.assertIn('WHERE partner_id = %s', query)
        self.assertEqual(query.count('%s'), 9)
        self.assertEqual(parameters[-1], 42)
        self.assertIn(injection_text, parameters)
        self.assertNotIn(injection_text, query)


if __name__ == '__main__':
    unittest.main()
