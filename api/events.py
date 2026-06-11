from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length > 5_000:
            self.send_response(413)
            self.end_headers()
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            payload = {}
        allowed = {"app_opened", "audit_completed", "checkout_started", "export_csv", "print_report", "sample_loaded", "upgrade_clicked"}
        event = payload.get("event") if isinstance(payload, dict) else None
        if event not in allowed:
            self.send_response(400)
            self.end_headers()
            return
        body = json.dumps({"recorded": True, "persistence": "local-runtime-only"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

