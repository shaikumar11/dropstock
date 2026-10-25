import unittest

from app import validation


class ProductValidationTests(unittest.TestCase):
    def test_valid_product_is_trimmed(self):
        data = validation.parse_product({"name": "  Shoe ", "price_cents": 100, "stock": 3})
        self.assertEqual(data, {"name": "Shoe", "price_cents": 100, "stock": 3})

    def test_rejects_missing_or_blank_name(self):
        for body in ({}, {"name": "   ", "price_cents": 1, "stock": 1}):
            with self.assertRaises(validation.ValidationError):
                validation.parse_product(body)

    def test_rejects_negative_and_non_integer_numbers(self):
        for price, stock in [(-1, 1), (1, -1), (1.5, 1), ("1", 1), (True, 1), (1, False)]:
            with self.assertRaises(validation.ValidationError):
                validation.parse_product({"name": "x", "price_cents": price, "stock": stock})

    def test_rejects_non_object_body(self):
        with self.assertRaises(validation.ValidationError):
            validation.parse_product(["not", "an", "object"])


class ReservationValidationTests(unittest.TestCase):
    def test_quantity_must_be_between_one_and_five(self):
        for quantity in (0, 6, -2, 2.5, "2"):
            with self.assertRaises(validation.ValidationError):
                validation.parse_reservation({"quantity": quantity, "customer": "a"})

    def test_customer_required(self):
        with self.assertRaises(validation.ValidationError):
            validation.parse_reservation({"quantity": 1, "customer": " "})

    def test_valid_reservation(self):
        data = validation.parse_reservation({"quantity": 2, "customer": " Asha "})
        self.assertEqual(data, {"quantity": 2, "customer": "Asha"})


if __name__ == "__main__":
    unittest.main()
