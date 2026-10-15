"""A tiny local shop API. Run: python3 server.py (port 8766)."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

ITEMS = [
    {"name": "Blue Mug", "price_cents": 1999},
    {"name": "Sticker Pack", "price_cents": 549},
    {"name": "Desk Lamp", "price_cents": 12000},
]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.rstrip("/") == "/api/v1/items":
            body, code = json.dumps({"items": ITEMS}).encode(), 200
        else:
            body, code = json.dumps({"error": "not found"}).encode(), 404
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8766), Handler).serve_forever()
