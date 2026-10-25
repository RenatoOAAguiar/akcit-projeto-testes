"""Duas APIs locais para demonstrar integração HTTP com estoque em SQLite."""

import json
import sqlite3
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Inventory:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.lock = threading.Lock()
        self.connection.execute("CREATE TABLE stock (sku TEXT PRIMARY KEY, quantity INTEGER)")
        self.connection.execute("INSERT INTO stock VALUES ('LIVRO-001', 5)")
        self.connection.commit()

    def quantity(self, sku="LIVRO-001"):
        with self.lock:
            row = self.connection.execute(
                "SELECT quantity FROM stock WHERE sku = ?", (sku,)
            ).fetchone()
            return None if row is None else row[0]

    def reserve(self, sku, quantity):
        with self.lock:
            row = self.connection.execute(
                "SELECT quantity FROM stock WHERE sku = ?", (sku,)
            ).fetchone()
            if row is None:
                return 404, {"error": "unknown_sku"}
            if row[0] < quantity:
                return 409, {"error": "insufficient_stock"}
            self.connection.execute(
                "UPDATE stock SET quantity = quantity - ? WHERE sku = ?", (quantity, sku)
            )
            self.connection.commit()
            return 200, {"sku": sku, "quantity": quantity, "remaining": row[0] - quantity}

    def close(self):
        self.connection.close()


class JsonHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_payload(self):
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except (ValueError, UnicodeError):
            self.respond(400, {"error": "invalid_json"})
            return None
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("sku"), str)
            or not payload["sku"].strip()
            or type(payload.get("quantity")) is not int
            or payload["quantity"] <= 0
        ):
            self.respond(400, {"error": "invalid_payload"})
            return None
        return payload


def inventory_handler(inventory):
    class InventoryHandler(JsonHandler):
        def do_POST(self):
            if self.path != "/reservations":
                self.respond(404, {"error": "not_found"})
                return
            payload = self.read_payload()
            if payload is not None:
                self.respond(*inventory.reserve(payload["sku"], payload["quantity"]))

    return InventoryHandler


def orders_handler(inventory_url):
    class OrdersHandler(JsonHandler):
        def do_POST(self):
            if self.path != "/orders":
                self.respond(404, {"error": "not_found"})
                return
            payload = self.read_payload()
            if payload is None:
                return
            request = Request(
                inventory_url + "/reservations",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=1) as response:
                    reservation = json.load(response)
            except HTTPError as error:
                if error.code == 404:
                    self.respond(422, {"error": "unknown_sku"})
                elif error.code == 409:
                    self.respond(409, {"error": "insufficient_stock"})
                else:
                    self.respond(502, {"error": "inventory_error"})
                error.close()
                return
            except (TimeoutError, URLError):
                self.respond(503, {"error": "inventory_unavailable"})
                return
            self.respond(201, {
                "order_id": str(uuid.uuid4()),
                "status": "confirmed",
                "sku": reservation["sku"],
                "quantity": reservation["quantity"],
            })

    return OrdersHandler


def start_server(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()
    return server, thread


def stop_server(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def server_url(server):
    return f"http://127.0.0.1:{server.server_address[1]}"
