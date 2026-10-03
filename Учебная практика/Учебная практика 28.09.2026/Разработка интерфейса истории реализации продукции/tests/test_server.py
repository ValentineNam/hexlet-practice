import unittest
from unittest.mock import MagicMock, patch

import server


class PartnerHistoryTests(unittest.TestCase):
    @patch.object(server.backend, 'get_db_connection')
    @patch.object(server.backend, 'get_partner')
    def test_returns_partner_and_formatted_history(self, get_partner, get_connection):
        get_partner.return_value = {'id': 2, 'company_name': 'ООО Партнер 2'}
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [('Ткань', 25, '28.09.2026')]
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value = cursor
        get_connection.return_value = connection

        result = server.get_partner_history(2)

        self.assertEqual(result['partner']['id'], 2)
        self.assertEqual(result['rows'][0]['product_name'], 'Ткань')
        self.assertEqual(result['rows'][0]['quantity'], 25)
        self.assertEqual(result['rows'][0]['sale_date'], '28.09.2026')
        query, values = cursor.execute.call_args.args
        self.assertIn('JOIN products', query)
        self.assertIn('JOIN shipment_items', query)
        self.assertIn('TO_CHAR(s.shipment_date', query)
        self.assertEqual(values, (2,))

    @patch.object(server.backend, 'get_partner')
    def test_unknown_partner_returns_none(self, get_partner):
        get_partner.return_value = None
        self.assertIsNone(server.get_partner_history(999999))


if __name__ == '__main__':
    unittest.main()
