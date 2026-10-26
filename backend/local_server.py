"""Run the Lambda handlers locally over HTTP with an in-memory DynamoDB.

No AWS account needed:  python local_server.py   (serves on :8000, or on $PORT when set)
"""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("AWS_ACCESS_KEY_ID", "local")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "local")

from moto import mock_aws  # noqa: E402

from app import handlers, infra  # noqa: E402
from app.repository import Repository  # noqa: E402

ROUTES = [
    ("GET", re.compile(r"^/products$"), handlers.list_products),
    ("POST", re.compile(r"^/products$"), handlers.create_product),
    ("GET", re.compile(r"^/products/(?P<id>[^/]+)$"), handlers.get_product),
    ("POST", re.compile(r"^/products/(?P<id>[^/]+)/reserve$"), handlers.reserve),
]

INFO = {
    "service": "DropStock API",
    "status": "ok",
    "endpoints": [
        "GET /products",
        "POST /products",
        "GET /products/{id}",
        "POST /products/{id}/reserve",
    ],
}


class Handler(BaseHTTPRequestHandler):
    def _dispatch(self, method):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode() if length else None
        if method == "GET" and path in ("/", "/health"):
            return self._send(200, json.dumps(INFO), handlers.HEADERS)
        for route_method, pattern, fn in ROUTES:
            match = pattern.match(path)
            if route_method == method and match:
                event = {
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "pathParameters": match.groupdict(),
                    "body": body,
                }
                result = fn(event, None)
                return self._send(result["statusCode"], result["body"], result["headers"])
        self._send(404, json.dumps({"error": "Not found"}), handlers.HEADERS)

    def _send(self, status, body, headers):
        data = body.encode()
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_OPTIONS(self):
        self._send(204, "", {**handlers.HEADERS, "Access-Control-Allow-Methods": "GET,POST,OPTIONS"})


def seed():
    repo = Repository()
    for name, price, stock in [
        ("Air Zoom Pegasus", 11995, 5),
        ("Court Vision Low", 7495, 3),
        ("Dunk Retro Drop", 9995, 2),
    ]:
        repo.create_product({"name": name, "price_cents": price, "stock": stock})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    with mock_aws():
        infra.create_tables()
        seed()
        print(f"DropStock API listening on 0.0.0.0:{port}")
        ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()