import unittest
from decimal import Decimal
from unittest.mock import patch

import material_calculator
from material_catalogs import CatalogUnavailableError

from material_calculator import calculate_material_requirement


class MaterialCalculatorTests(unittest.TestCase):
    def setUp(self):
        def coefficients(product_id, material_id):
            if product_id not in (1, 2, 3) or material_id not in (1, 2, 3):
                return None
            return Decimal('1.20'), Decimal('5')
        patcher = patch.object(material_calculator, 'get_coefficients', side_effect=coefficients)
        self.catalog = patcher.start()
        self.addCleanup(patcher.stop)

    def test_database_failure_is_not_reported_as_invalid_input(self):
        self.catalog.side_effect = CatalogUnavailableError('offline')
        with self.assertRaises(CatalogUnavailableError):
            calculate_material_requirement(1, 1, 1, 1, 1)

    def test_invalid_input_does_not_query_database(self):
        self.assertEqual(calculate_material_requirement(1, 1, 0, 1, 1), -1)
        self.catalog.assert_not_called()

    def test_decimal_tail_is_preserved_beyond_default_precision(self):
        self.catalog.side_effect = None
        self.catalog.return_value = (Decimal('1'), Decimal('0'))
        self.assertEqual(calculate_material_requirement(1, 1, 1, Decimal('1.00000000000000000000000000001'), 1), 2)

    def test_exact_integer_is_not_rounded_further(self):
        self.catalog.side_effect = None
        self.catalog.return_value = (Decimal('1'), Decimal('0'))
        self.assertEqual(calculate_material_requirement(1, 1, 10, Decimal('0.1'), 1), 1)

    def test_calculates_material_with_product_coefficient_and_scrap(self):
        result = calculate_material_requirement(1, 2, 100, 1.0, 1.0)
        self.assertEqual(result, 126)

    def test_rounds_fractional_material_amount_up(self):
        result = calculate_material_requirement(1, 1, 1, 1.0, 1.0)
        self.assertEqual(result, 2)

    def test_returns_minus_one_for_unknown_product_type(self):
        result = calculate_material_requirement(999, 1, 10, 1.0, 1.0)
        self.assertEqual(result, -1)

    def test_returns_minus_one_for_unknown_material_type(self):
        result = calculate_material_requirement(1, 999, 10, 1.0, 1.0)
        self.assertEqual(result, -1)

    def test_returns_minus_one_for_nonpositive_parameters(self):
        for param_1, param_2 in ((-1.0, 1.0), (1.0, -1.0), (0.0, 1.0), (1.0, 0.0)):
            with self.subTest(param_1=param_1, param_2=param_2):
                result = calculate_material_requirement(1, 1, 10, param_1, param_2)
                self.assertEqual(result, -1)

    def test_returns_minus_one_for_nonpositive_quantity(self):
        for quantity in (0, -1):
            with self.subTest(quantity=quantity):
                result = calculate_material_requirement(1, 1, quantity, 1.0, 1.0)
                self.assertEqual(result, -1)

    def test_returns_minus_one_for_nonfinite_or_non_numeric_parameters(self):
        for value in (float('nan'), float('inf'), '2.0', True):
            with self.subTest(value=value):
                result = calculate_material_requirement(1, 1, 10, value, 1.0)
                self.assertEqual(result, -1)

    def test_returns_minus_one_for_non_integer_ids_and_quantity(self):
        cases = (
            ('1', 1, 10),
            (1, 1.0, 10),
            (1, 1, 10.0),
            (True, 1, 10),
        )
        for product_type_id, material_type_id, quantity in cases:
            with self.subTest(
                product_type_id=product_type_id,
                material_type_id=material_type_id,
                quantity=quantity,
            ):
                result = calculate_material_requirement(
                    product_type_id,
                    material_type_id,
                    quantity,
                    1.0,
                    1.0,
                )
                self.assertEqual(result, -1)


if __name__ == '__main__':
    unittest.main()
