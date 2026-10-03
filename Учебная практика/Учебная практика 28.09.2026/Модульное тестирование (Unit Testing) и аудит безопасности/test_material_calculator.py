import unittest
from pathlib import Path
import sys

CORE_DIR = (
    Path(__file__).resolve().parents[1]
    / 'Разработка ядра алгоритма расчета материалов'
)
sys.path.insert(0, str(CORE_DIR))

from material_calculator import calculate_material_requirement


class MaterialRequirementTests(unittest.TestCase):
    def test_standard_calculation(self):
        self.assertEqual(
            calculate_material_requirement(1, 2, 100, 1.0, 1.0),
            126,
        )

    def test_fractional_result_rounds_up(self):
        self.assertEqual(
            calculate_material_requirement(1, 1, 1, 1.0, 1.0),
            2,
        )

    def test_unknown_product_type_returns_minus_one(self):
        self.assertEqual(
            calculate_material_requirement(999, 1, 1, 1.0, 1.0),
            -1,
        )

    def test_unknown_material_type_returns_minus_one(self):
        self.assertEqual(
            calculate_material_requirement(1, 999, 1, 1.0, 1.0),
            -1,
        )

    def test_negative_parameters_return_minus_one(self):
        invalid_parameters = ((-1.0, 1.0), (1.0, -1.0))
        for param_1, param_2 in invalid_parameters:
            with self.subTest(param_1=param_1, param_2=param_2):
                self.assertEqual(
                    calculate_material_requirement(1, 1, 1, param_1, param_2),
                    -1,
                )

    def test_zero_or_negative_quantity_returns_minus_one(self):
        for quantity in (0, -1):
            with self.subTest(quantity=quantity):
                self.assertEqual(
                    calculate_material_requirement(1, 1, quantity, 1.0, 1.0),
                    -1,
                )

    def test_non_finite_values_return_minus_one(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value):
                self.assertEqual(
                    calculate_material_requirement(1, 1, 1, value, 1.0),
                    -1,
                )


if __name__ == '__main__':
    unittest.main()
