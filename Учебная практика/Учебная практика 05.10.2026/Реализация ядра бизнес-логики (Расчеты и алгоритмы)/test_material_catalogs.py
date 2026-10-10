import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

import psycopg2
import material_catalogs as catalogs


class CatalogRepositoryTests(unittest.TestCase):
    def test_bound_ids_and_closed_connection(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (Decimal('2'), Decimal('3'))
        with patch.object(catalogs, 'get_db_connection', return_value=connection):
            self.assertEqual(catalogs.get_coefficients(1, 2), (Decimal('2'), Decimal('3')))
        query, args = cursor.execute.call_args.args
        self.assertEqual(args, (1, 2))
        self.assertEqual(query.count('%s'), 2)
        connection.close.assert_called_once()

    def test_connection_and_missing_table_errors(self):
        for error in (psycopg2.OperationalError('offline'), psycopg2.errors.UndefinedTable('missing')):
            with self.subTest(error=error), patch.object(catalogs, 'get_db_connection', side_effect=error):
                with self.assertRaises(catalogs.CatalogUnavailableError):
                    catalogs.get_coefficients(1, 2)
                with self.assertRaises(catalogs.CatalogUnavailableError):
                    catalogs.list_catalogs()

    def test_empty_catalogs_are_explicit_error(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value.fetchall.return_value = []
        with patch.object(catalogs, 'get_db_connection', return_value=connection):
            with self.assertRaisesRegex(catalogs.CatalogUnavailableError, 'пусты'):
                catalogs.list_catalogs()
