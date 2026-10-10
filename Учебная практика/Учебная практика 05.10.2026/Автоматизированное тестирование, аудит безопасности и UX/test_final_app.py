import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

FINAL_APP_DIR = (
    Path(__file__).resolve().parents[1]
    / 'Разработка UI, навигации и CRUD-форм'
)
sys.path.insert(0, str(FINAL_APP_DIR))
import server

ETL_DIR = (
    Path(__file__).resolve().parents[1]
    / 'Инфраструктура данных и ETL (База данных в 3NF)'
)
sys.path.insert(0, str(ETL_DIR))
from etl import transform_sources


class FinalBusinessLogicTests(unittest.TestCase):
    def test_discount_thresholds(self):
        cases = ((9999, 0), (10000, 5), (49999, 5), (50000, 10), (300000, 15))
        for quantity, expected in cases:
            with self.subTest(quantity=quantity):
                self.assertEqual(server.discount_module.calculate_partner_discount(quantity), expected)

    def test_material_calculation_and_invalid_ids(self):
        self.assertEqual(server.material_module.calculate_material_requirement(1, 2, 100, 1.0, 1.0), 126)
        self.assertEqual(server.material_module.calculate_material_requirement(999, 2, 100, 1.0, 1.0), -1)


class FinalDataPipelineTests(unittest.TestCase):
    def test_dev_sources_clean_and_reject_broken_foreign_key(self):
        partners, products, sales, rejected = transform_sources(ETL_DIR / 'raw')
        self.assertEqual((len(partners), len(products), len(sales), len(rejected)), (5, 3, 5, 1))
        self.assertIn('partner_id=999', rejected[0][2])


class FinalBackendSecurityTests(unittest.TestCase):
    def setUp(self):
        self.cursor = MagicMock()
        self.cursor.__enter__.return_value = self.cursor
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.connection.cursor.return_value = self.cursor

    @patch.object(server, 'get_db_connection')
    def test_sql_injection_payload_is_bound_not_interpolated(self, get_connection):
        get_connection.return_value = self.connection
        self.cursor.fetchone.return_value = (810,)
        injection = "X'); DROP TABLE partners; --"
        partner = {
            'company_name': injection,
            'partner_type': 'ООО',
            'inn': '1234567890',
            'rating': 4,
            'address': '',
            'director': '',
            'phone': '',
            'email': 'safe@example.test',
        }

        partner_id = server.save_partner(None, partner)

        query, parameters = self.cursor.execute.call_args.args
        self.assertEqual(partner_id, 810)
        self.assertNotIn(injection, query)
        self.assertIn(injection, parameters)
        self.assertEqual(query.count('%s'), len(parameters))

    def test_partner_input_validation_rejects_negative_rating(self):
        partner = {
            'company_name': 'Тест',
            'partner_type': 'ООО',
            'inn': '1234567890',
            'rating': -1,
            'address': '',
            'director': '',
            'phone': '',
            'email': 'safe@example.test',
        }
        with self.assertRaisesRegex(ValueError, 'Рейтинг'):
            server.validate_partner(partner)


class FinalLoggingTests(unittest.TestCase):
    def test_application_log_file_is_configured(self):
        log_path = FINAL_APP_DIR / 'app.log'
        file_handlers = [
            handler
            for handler in logging.getLogger().handlers
            if isinstance(handler, logging.FileHandler)
        ]
        self.assertTrue(any(Path(handler.baseFilename) == log_path for handler in file_handlers))


if __name__ == '__main__':
    unittest.main()
