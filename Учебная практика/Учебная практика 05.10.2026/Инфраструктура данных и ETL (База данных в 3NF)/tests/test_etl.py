import tempfile
import unittest
from pathlib import Path

from etl import clean_partner_name, parse_date, transform_sources


RAW_DIR = Path(__file__).resolve().parents[1] / 'raw'


class SourceCleaningTests(unittest.TestCase):
    def test_partner_whitespace_and_initials_are_normalized(self):
        self.assertEqual(clean_partner_name('ИП ...Петров  A.B.'), 'ИП Петров А.В.')

    def test_all_supported_date_formats_become_iso_dates(self):
        expected = '2023-10-25'
        samples = ('25.10.2023', '2023/10/25', '2023-10-25', '25-10-2023', '2023.10.25')
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual(parse_date(sample).isoformat(), expected)

    def test_raw_files_transform_and_reject_only_broken_partner_reference(self):
        partners, products, sales, rejections = transform_sources(RAW_DIR)
        self.assertEqual(len(partners), 5)
        self.assertEqual(len(products), 3)
        self.assertEqual(len(sales), 5)
        self.assertEqual(len(rejections), 1)
        self.assertIn('partner_id=999', rejections[0][2])
        self.assertEqual(partners[1][1], 'Петров А.В.')
        self.assertEqual(partners[1][2], 'ИП')
        self.assertEqual(products[0][1], 'Ноутбук Pro')
        self.assertEqual(sales[0][3].isoformat(), '2023-10-25')

    def test_raw_transform_does_not_change_source_files(self):
        original_hashes = {
            path.name: path.read_bytes()
            for path in RAW_DIR.glob('*.csv')
        }
        transform_sources(RAW_DIR)
        updated_hashes = {
            path.name: path.read_bytes()
            for path in RAW_DIR.glob('*.csv')
        }
        self.assertEqual(updated_hashes, original_hashes)


class RegressionTests(unittest.TestCase):
    def transform_modified(self, filename, change):
        import csv
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for source in RAW_DIR.glob('*.csv'):
                (target / source.name).write_bytes(source.read_bytes())
            path = target / filename
            encoding = 'cp1251' if filename == 'products_raw.csv' else 'utf-8-sig'
            with path.open(encoding=encoding, newline='') as stream:
                reader = csv.DictReader(stream)
                fields = reader.fieldnames
                rows = list(reader)
            change(rows)
            with path.open('w', encoding=encoding, newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            return transform_sources(target)

    def test_historical_amount_does_not_depend_on_current_price(self):
        from decimal import Decimal
        result = self.transform_modified('sales_history_raw.csv', lambda rows: rows[0].update(amount='100.01', quantity='3'))
        self.assertEqual(len(result[2]), 5)
        self.assertEqual(result[2][0][-1], Decimal('100.01'))
        self.assertEqual(len(result[3]), 1)

    def test_missing_amount_is_not_invented(self):
        result = self.transform_modified('sales_history_raw.csv', lambda rows: rows[0].update(amount=''))
        self.assertEqual(len(result[2]), 4)
        self.assertEqual(len(result[3]), 2)

    def test_fractional_kopecks_are_rejected_without_rounding(self):
        result = self.transform_modified('sales_history_raw.csv', lambda rows: rows[0].update(amount='1.001'))
        self.assertEqual(len(result[2]), 4)

    def test_eleven_digit_inn_is_rejected(self):
        result = self.transform_modified('partners_raw.csv', lambda rows: rows[0].update(inn='12345678901'))
        self.assertEqual(len(result[0]), 4)
        self.assertTrue(any('ИНН' in row[2] for row in result[3]))

    def test_duplicate_email_after_normalization_is_rejected(self):
        result = self.transform_modified('partners_raw.csv', lambda rows: rows[1].update(email=' VECTOR@MAIL.RU '))
        self.assertEqual(len(result[0]), 4)
        self.assertTrue(any('повторный email' in row[2] for row in result[3]))

    def test_duplicate_sale_id_is_rejected(self):
        result = self.transform_modified('sales_history_raw.csv', lambda rows: rows.append(dict(rows[0])))
        self.assertEqual(len(result[2]), 5)
        self.assertTrue(any('повторный sale_id' in row[2] for row in result[3]))

    def test_invalid_date_and_product_reference_are_rejected(self):
        for changes in ({'sale_date': '31.02.2023'}, {'product_id': '999'}):
            with self.subTest(changes=changes):
                result = self.transform_modified('sales_history_raw.csv', lambda rows: rows[0].update(changes))
                self.assertEqual(len(result[2]), 4)

    def test_integer_bounds_are_checked_before_database(self):
        for value in ('0', '-1', '2147483648'):
            with self.subTest(value=value):
                result = self.transform_modified('sales_history_raw.csv', lambda rows: rows[0].update(quantity=value))
                self.assertEqual(len(result[2]), 4)

    def test_nonfinite_and_oversized_prices_are_rejected(self):
        for value in ('NaN', 'Infinity', '-1', '1e100', '1e1000000'):
            with self.subTest(value=value):
                result = self.transform_modified('products_raw.csv', lambda rows: rows[0].update(price=value))
                self.assertEqual(len(result[1]), 2)


class SharedValidationTests(unittest.TestCase):
    def payload(self, **changes):
        data = {'company_name': '  Тест   компании ', 'partner_type': 'ооо',
                'inn': '1234567890', 'email': ' TEST@EXAMPLE.RU ', 'rating': 6}
        data.update(changes)
        return data

    def test_rating_above_five_and_text_normalization(self):
        from validation import validate_partner
        result = validate_partner(self.payload())
        self.assertEqual(result['rating'], 6)
        self.assertEqual(result['company_name'], 'Тест компании')
        self.assertEqual(result['email'], 'test@example.ru')
        self.assertEqual(result['partner_type'], 'ООО')
        self.assertIsNone(result['phone'])

    def test_rating_invalid_types_and_bounds(self):
        from validation import validate_partner
        for rating in (True, -1, 1.5, '1.5', None, 2147483648):
            with self.subTest(rating=rating), self.assertRaises(ValueError):
                validate_partner(self.payload(rating=rating))

    def test_invalid_partner_fields(self):
        from validation import validate_partner
        for changes in ({'company_name': ''}, {'partner_type': 'ТК'}, {'inn': '12345678901'},
                        {'inn': '１２３４５６７８９０'}, {'email': 'bad email'},
                        {'phone': '1' * 21}, {'company_name': 'x' * 256}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_partner(self.payload(**changes))


class ImportSafetyTests(unittest.TestCase):
    def test_identical_existing_row_is_not_written(self):
        from etl import merge_rows
        from unittest.mock import MagicMock
        cursor = MagicMock()
        row = (101, 'Ноутбук Pro', 75000)
        cursor.fetchone.return_value = row
        self.assertEqual(merge_rows(cursor, 'products', [row]), 0)
        self.assertEqual(cursor.execute.call_count, 1)

    def test_modified_existing_row_aborts_instead_of_overwriting(self):
        from etl import merge_rows
        from unittest.mock import MagicMock
        cursor = MagicMock()
        cursor.fetchone.return_value = (101, 'Изменено пользователем', 75000)
        with self.assertRaisesRegex(ValueError, 'Конфликт'):
            merge_rows(cursor, 'products', [(101, 'Ноутбук Pro', 75000)])
        self.assertEqual(cursor.execute.call_count, 1)

    def test_new_row_uses_bound_parameters(self):
        from etl import merge_rows
        from unittest.mock import MagicMock
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        payload = "X'); DROP TABLE products; --"
        row = (900, payload, 1)
        self.assertEqual(merge_rows(cursor, 'products', [row]), 1)
        query, parameters = cursor.execute.call_args.args
        self.assertEqual(parameters, row)
        self.assertNotIn(payload, str(query))

    def test_post_import_verification_detects_mismatch(self):
        from etl import verify_rows
        from unittest.mock import MagicMock
        cursor = MagicMock()
        cursor.fetchone.return_value = (101, 'Wrong', 1)
        with self.assertRaisesRegex(ValueError, 'Проверка загрузки'):
            verify_rows(cursor, 'products', [(101, 'Ноутбук Pro', 75000)])

    def test_conflict_exits_transaction_with_error_and_closes_connection(self):
        import etl
        from unittest.mock import MagicMock, patch
        connection = MagicMock()
        connection.__enter__.return_value = connection
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(etl, 'get_connection', return_value=connection), patch.object(
                etl, 'merge_rows', side_effect=ValueError('Конфликт')
            ):
                with self.assertRaisesRegex(ValueError, 'Конфликт'):
                    etl.run_etl(output_path=Path(directory) / 'rejections.csv')
        self.assertIs(connection.__exit__.call_args.args[0], ValueError)
        connection.close.assert_called_once()

    def test_demo_catalogs_use_existing_values_and_explicit_provenance(self):
        from decimal import Decimal
        from etl import load_demo_catalogs
        catalogs = load_demo_catalogs()
        self.assertEqual(catalogs['product_types'][0], (1, Decimal('1.20'), 'demo'))
        self.assertEqual(catalogs['material_types'][1], (2, Decimal('5'), 'demo'))
        self.assertTrue(all(row[2] == 'demo' for rows in catalogs.values() for row in rows))


if __name__ == '__main__':
    unittest.main()
