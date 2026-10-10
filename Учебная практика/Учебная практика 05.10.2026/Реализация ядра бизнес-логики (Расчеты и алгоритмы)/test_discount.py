import unittest

from discount import calculate_partner_discount


class TestPartnerDiscount(unittest.TestCase):
    def test_discount_boundaries(self):
        for quantity, expected in ((0, 0), (1, 0), (9999, 0), (10000, 5),
                                   (10001, 5), (49999, 5), (50000, 10),
                                   (50001, 10), (299999, 10), (300000, 15), (300001, 15)):
            with self.subTest(quantity=quantity):
                self.assertEqual(calculate_partner_discount(quantity), expected)


if __name__ == "__main__":
    unittest.main()
