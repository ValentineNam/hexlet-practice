import unittest

import server


class CalculatorIntegrationTests(unittest.TestCase):
    def test_valid_payload_returns_calculated_amount(self):
        payload = {
            'product_type_id': 1,
            'material_type_id': 2,
            'quantity': 100,
            'param_1': 1.0,
            'param_2': 1.0,
        }
        self.assertEqual(server.calculate_from_payload(payload), 126)

    def test_invalid_type_id_returns_calculator_error_sentinel(self):
        payload = {
            'product_type_id': 999,
            'material_type_id': 2,
            'quantity': 100,
            'param_1': 1.0,
            'param_2': 1.0,
        }
        self.assertEqual(server.calculate_from_payload(payload), -1)

    def test_negative_dimension_returns_calculator_error_sentinel(self):
        payload = {
            'product_type_id': 1,
            'material_type_id': 2,
            'quantity': 100,
            'param_1': -1.0,
            'param_2': 1.0,
        }
        self.assertEqual(server.calculate_from_payload(payload), -1)

    def test_missing_field_is_reported_as_request_error(self):
        with self.assertRaisesRegex(ValueError, 'все пять параметров'):
            server.calculate_from_payload({'product_type_id': 1})


if __name__ == '__main__':
    unittest.main()
