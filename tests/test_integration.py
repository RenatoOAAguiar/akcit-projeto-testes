"""Casos gerados com os prompts P1 e P2 e executados contra APIs HTTP reais."""

import json
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import (
    Inventory, inventory_handler, orders_handler, server_url, start_server, stop_server,
)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.inventory = Inventory()
        self.addCleanup(self.inventory.close)
        self.stock_server, self.stock_thread = start_server(inventory_handler(self.inventory))
        self.stock_running = True
        self.addCleanup(self.stop_inventory)
        self.orders_server, self.orders_thread = start_server(
            orders_handler(server_url(self.stock_server))
        )
        self.addCleanup(stop_server, self.orders_server, self.orders_thread)

    def stop_inventory(self):
        if self.stock_running:
            stop_server(self.stock_server, self.stock_thread)
            self.stock_running = False

    def post(self, payload=None, *, raw=None, url=None):
        data = raw if raw is not None else json.dumps(payload).encode()
        request = Request(
            url or server_url(self.orders_server) + "/orders",
            data=data, headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response), response.headers

    def assert_rejected(self, payload, status=400, error="invalid_payload"):
        actual_status, body, _ = self.post(payload)
        self.assertEqual(actual_status, status)
        self.assertEqual(body, {"error": error})
        self.assertEqual(self.inventory.quantity(), 5)

    def test_ct01_order_reserves_stock(self):
        status, body, headers = self.post({"sku": "LIVRO-001", "quantity": 2})
        self.assertEqual(status, 201)
        self.assertEqual(set(body), {"order_id", "status", "sku", "quantity"})
        self.assertEqual(str(uuid.UUID(body["order_id"])), body["order_id"])
        self.assertEqual(body["status"], "confirmed")
        self.assertEqual(body["sku"], "LIVRO-001")
        self.assertIs(type(body["quantity"]), int)
        self.assertEqual(body["quantity"], 2)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(self.inventory.quantity(), 3)

    def test_ct02_insufficient_stock(self):
        self.assert_rejected({"sku": "LIVRO-001", "quantity": 6}, 409, "insufficient_stock")

    def test_ct03_unknown_sku(self):
        self.assert_rejected({"sku": "INEXISTENTE", "quantity": 1}, 422, "unknown_sku")
        self.assertIsNone(self.inventory.quantity("INEXISTENTE"))

    def test_ct04_zero_quantity(self):
        self.assert_rejected({"sku": "LIVRO-001", "quantity": 0})

    def test_ct05_negative_quantity(self):
        self.assert_rejected({"sku": "LIVRO-001", "quantity": -1})

    def test_ct06_string_quantity(self):
        self.assert_rejected({"sku": "LIVRO-001", "quantity": "2"})

    def test_ct07_missing_quantity(self):
        self.assert_rejected({"sku": "LIVRO-001"})

    def test_ct08_boolean_quantity(self):
        self.assert_rejected({"sku": "LIVRO-001", "quantity": True})

    def test_ct09_exact_stock_boundary(self):
        status, _, _ = self.post({"sku": "LIVRO-001", "quantity": 5})
        self.assertEqual(status, 201)
        self.assertEqual(self.inventory.quantity(), 0)
        status, body, _ = self.post({"sku": "LIVRO-001", "quantity": 1})
        self.assertEqual(status, 409)
        self.assertEqual(body, {"error": "insufficient_stock"})
        self.assertEqual(self.inventory.quantity(), 0)

    def test_ct10_malformed_json(self):
        status, body, _ = self.post(raw=b'{"sku":')
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "invalid_json"})
        self.assertEqual(self.inventory.quantity(), 5)

    def test_ct11_inventory_unavailable(self):
        self.stop_inventory()
        status, body, _ = self.post({"sku": "LIVRO-001", "quantity": 1})
        self.assertEqual(status, 503)
        self.assertEqual(body, {"error": "inventory_unavailable"})
        self.assertEqual(self.inventory.quantity(), 5)

    def test_ct12_concurrent_orders_do_not_oversell(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda _: self.post({"sku": "LIVRO-001", "quantity": 4}), range(2)
            ))
        self.assertEqual(sorted(result[0] for result in results), [201, 409])
        self.assertEqual(self.inventory.quantity(), 1)
        failure = next(result[1] for result in results if result[0] == 409)
        self.assertEqual(failure, {"error": "insufficient_stock"})

    def test_ct13_empty_sku(self):
        self.assert_rejected({"sku": "   ", "quantity": 1})

    def test_ct14_non_object_json(self):
        self.assert_rejected(["LIVRO-001", 1])

    def test_ct15_inventory_contract(self):
        status, body, headers = self.post(
            {"sku": "LIVRO-001", "quantity": 1},
            url=server_url(self.stock_server) + "/reservations",
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, {"sku": "LIVRO-001", "quantity": 1, "remaining": 4})
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(self.inventory.quantity(), 4)


if __name__ == "__main__":
    unittest.main()
