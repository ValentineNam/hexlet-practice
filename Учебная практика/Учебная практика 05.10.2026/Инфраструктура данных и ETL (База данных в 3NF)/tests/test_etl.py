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


if __name__ == '__main__':
    unittest.main()
