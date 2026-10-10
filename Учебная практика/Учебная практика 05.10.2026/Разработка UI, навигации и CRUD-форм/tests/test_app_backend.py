import unittest
from unittest.mock import MagicMock, patch

import server


class FinalApplicationBackendTests(unittest.TestCase):
    def test_discount_boundaries(self):
        self.assertEqual(server.discount_module.calculate_partner_discount(9999), 0)
        self.assertEqual(server.discount_module.calculate_partner_discount(10000), 5)
        self.assertEqual(server.discount_module.calculate_partner_discount(50000), 10)
        self.assertEqual(server.discount_module.calculate_partner_discount(300000), 15)

    def test_material_error_sentinel_is_preserved(self):
        self.assertEqual(
            server.material_module.calculate_material_requirement(999, 1, 10, 1.0, 1.0),
            -1,
        )

    @patch.object(server, 'get_db_connection')
    def test_sales_history_query_uses_bound_partner_id(self, get_connection):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [('Notebook', 2, '25.10.2023')]
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value = cursor
        get_connection.return_value = connection
        with patch.object(server, 'get_partner', return_value={'id': 1, 'company_name': 'Partner'}):
            result = server.get_partner_history(1)
        query, values = cursor.execute.call_args.args
        self.assertIn('JOIN products', query)
        self.assertIn('WHERE sh.partner_id = %s', query)
        self.assertEqual(values, (1,))
        self.assertEqual(result['rows'][0]['quantity'], 2)

    @patch.object(server, 'get_db_connection')
    def test_create_query_binds_fields_instead_of_interpolating(self, get_connection):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (70,)
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value = cursor
        get_connection.return_value = connection
        injection = "X'); DROP TABLE partners; --"
        payload = {
            'company_name': injection,
            'partner_type': 'ООО',
            'inn': '1234567890',
            'rating': 3,
            'address': '',
            'director': '',
            'phone': '',
            'email': 'audit@example.test',
        }
        self.assertEqual(server.save_partner(None, payload), 70)
        query, values = cursor.execute.call_args.args
        self.assertEqual(query.count('%s'), 8)
        self.assertIn(injection, values)
        self.assertNotIn(injection, query)


if __name__ == '__main__':
    unittest.main()
