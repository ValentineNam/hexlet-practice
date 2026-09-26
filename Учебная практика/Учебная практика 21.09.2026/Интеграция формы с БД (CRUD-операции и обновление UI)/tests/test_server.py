import unittest
from unittest.mock import MagicMock, patch

import server


class PartnerValidationTests(unittest.TestCase):
    def setUp(self):
        self.partner = {
            'company_name': 'ООО Проверка',
            'partner_type': 'ООО',
            'rating': 4,
            'address': 'Москва',
            'director': 'Иванов Иван Иванович',
            'phone': '+79990000000',
            'inn': '1234567890',
            'email': 'check@example.ru',
        }

    def test_accepts_valid_partner(self):
        result = server.validate_partner(self.partner)
        self.assertEqual(result['rating'], 4)
        self.assertEqual(result['company_name'], 'ООО Проверка')

    def test_rejects_missing_company_name(self):
        with self.assertRaises(ValueError):
            server.validate_partner({**self.partner, 'company_name': ' '})

    def test_rejects_missing_email(self):
        with self.assertRaises(ValueError):
            server.validate_partner({**self.partner, 'email': ''})

    def test_rejects_invalid_email(self):
        with self.assertRaises(ValueError):
            server.validate_partner({**self.partner, 'email': 'not-an-email'})

    def test_rejects_negative_fractional_and_out_of_range_rating(self):
        for rating in (-1, 1.5, 6):
            with self.subTest(rating=rating):
                with self.assertRaises(ValueError):
                    server.validate_partner({**self.partner, 'rating': rating})


class PartnerCrudTests(unittest.TestCase):
    def setUp(self):
        self.cursor = MagicMock()
        self.cursor.__enter__.return_value = self.cursor
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.connection.cursor.return_value = self.cursor

    @patch.object(server, 'get_db_connection')
    def test_create_uses_parameterized_insert(self, get_connection):
        get_connection.return_value = self.connection
        self.cursor.fetchone.return_value = (17,)
        payload = {
            'company_name': "ООО O'Reilly",
            'partner_type': 'ООО',
            'rating': 4,
            'address': '',
            'director': '',
            'phone': '+79990000000',
            'inn': '1234567890',
            'email': 'safe@example.ru',
        }

        partner_id = server.create_partner(payload)

        self.assertEqual(partner_id, 17)
        query, values = self.cursor.execute.call_args.args
        self.assertIn('VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', query)
        self.assertIn("ООО O'Reilly", values)
        self.assertNotIn("ООО O'Reilly", query)

    @patch.object(server, 'get_db_connection')
    def test_update_uses_parameterized_partner_id(self, get_connection):
        get_connection.return_value = self.connection
        self.cursor.fetchone.return_value = (9,)
        payload = {
            'company_name': 'ООО Обновлено',
            'partner_type': 'ООО',
            'rating': 2,
            'address': '',
            'director': '',
            'phone': '',
            'inn': '1234567890',
            'email': 'updated@example.ru',
        }

        partner_id = server.update_partner(9, payload)

        self.assertEqual(partner_id, 9)
        query, values = self.cursor.execute.call_args.args
        self.assertIn('WHERE partner_id = %s', query)
        self.assertEqual(values[-1], 9)

    def test_discount_handles_missing_sales(self):
        self.assertEqual(server.calculate_discount(None), 0)
        self.assertEqual(server.calculate_discount(0), 0)


if __name__ == '__main__':
    unittest.main()
