import unittest
from concurrent.futures import ThreadPoolExecutor

from app import handlers
from app.repository import Repository
from tests.base import ApiTestCase


class ProductEndpointTests(ApiTestCase):
    def create(self, name="Pegasus", price=11995, stock=5):
        status, body = self.parse(
            handlers.create_product(self.event({"name": name, "price_cents": price, "stock": stock}))
        )
        self.assertEqual(status, 201)
        return body

    def test_create_then_get(self):
        product = self.create()
        status, body = self.parse(handlers.get_product(self.event(path_id=product["id"])))
        self.assertEqual(status, 200)
        self.assertEqual(body["name"], "Pegasus")
        self.assertEqual(body["stock"], 5)

    def test_list_is_sorted_by_name(self):
        self.create(name="zoom")
        self.create(name="Air")
        status, body = self.parse(handlers.list_products(self.event()))
        self.assertEqual(status, 200)
        self.assertEqual([p["name"] for p in body["products"]], ["Air", "zoom"])

    def test_get_unknown_product_is_404(self):
        status, body = self.parse(handlers.get_product(self.event(path_id="nope")))
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_invalid_product_is_400(self):
        status, _ = self.parse(handlers.create_product(self.event({"name": "", "price_cents": 1, "stock": 1})))
        self.assertEqual(status, 400)

    def test_missing_and_malformed_body_are_400(self):
        status, _ = self.parse(handlers.create_product(self.event()))
        self.assertEqual(status, 400)
        status, _ = self.parse(handlers.create_product({"headers": {}, "body": "{not json"}))
        self.assertEqual(status, 400)

    def test_responses_include_cors_header(self):
        response = handlers.list_products(self.event())
        self.assertEqual(response["headers"]["Access-Control-Allow-Origin"], "*")


class ReserveEndpointTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.product = Repository().create_product({"name": "Dunk", "price_cents": 9995, "stock": 3})

    def reserve(self, quantity=1, key="key-1", customer="Asha", product_id=None):
        headers = {"idempotency-key": key} if key else {}
        return self.parse(
            handlers.reserve(
                self.event(
                    {"quantity": quantity, "customer": customer},
                    path_id=product_id or self.product["id"],
                    headers=headers,
                )
            )
        )

    def stock(self):
        return Repository().get_product(self.product["id"])["stock"]

    def test_reserve_decrements_stock(self):
        status, body = self.reserve(quantity=2)
        self.assertEqual(status, 201)
        self.assertEqual(body["quantity"], 2)
        self.assertEqual(self.stock(), 1)

    def test_cannot_oversell(self):
        status, _ = self.reserve(quantity=4, key="a")
        self.assertEqual(status, 409)
        self.assertEqual(self.stock(), 3)

    def test_selling_out_exactly_then_rejecting(self):
        self.assertEqual(self.reserve(quantity=3, key="a")[0], 201)
        self.assertEqual(self.stock(), 0)
        self.assertEqual(self.reserve(quantity=1, key="b")[0], 409)

    def test_same_key_replays_without_double_charging_stock(self):
        first_status, first = self.reserve(quantity=1, key="same")
        second_status, second = self.reserve(quantity=1, key="same")
        self.assertEqual((first_status, second_status), (201, 201))
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(self.stock(), 2)

    def test_same_key_with_different_request_is_422(self):
        self.reserve(quantity=1, key="same")
        status, _ = self.reserve(quantity=2, key="same")
        self.assertEqual(status, 422)
        self.assertEqual(self.stock(), 2)

    def test_missing_idempotency_key_is_400(self):
        status, body = self.reserve(key=None)
        self.assertEqual(status, 400)
        self.assertIn("Idempotency-Key", body["error"])

    def test_unknown_product_is_404(self):
        status, _ = self.reserve(product_id="missing")
        self.assertEqual(status, 404)

    def test_invalid_quantity_is_400_and_stock_untouched(self):
        status, _ = self.reserve(quantity=9)
        self.assertEqual(status, 400)
        self.assertEqual(self.stock(), 3)

    def test_parallel_requests_never_oversell(self):
        def attempt(i):
            return self.reserve(quantity=1, key=f"k{i}", customer=f"c{i}")[0]

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(attempt, range(10)))

        self.assertEqual(statuses.count(201), 3)
        self.assertEqual(statuses.count(409), 7)
        self.assertEqual(self.stock(), 0)


if __name__ == "__main__":
    unittest.main()
