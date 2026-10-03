import unittest

from material_calculator import calculate_material_requirement


class MaterialCalculatorTests(unittest.TestCase):
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
