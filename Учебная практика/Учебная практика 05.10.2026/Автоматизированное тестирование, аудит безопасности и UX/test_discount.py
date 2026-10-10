import unittest

from discount import calculate_partner_discount


class TestPartnerDiscount(unittest.TestCase):
    def test_discount_boundaries(self):
        self.assertEqual(calculate_partner_discount(9999), 0)
        self.assertEqual(calculate_partner_discount(10000), 5)
        self.assertEqual(calculate_partner_discount(49999), 5)
        self.assertEqual(calculate_partner_discount(50000), 10)
        self.assertEqual(calculate_partner_discount(300000), 15)


if __name__ == "__main__":
    unittest.main()
