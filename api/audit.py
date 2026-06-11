from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from passive_income_studio.auditor import audit_listing  # noqa: E402
from passive_income_studio.schemas import ListingAuditRequest  # noqa: E402
from pydantic import ValidationError  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 100_000:
                body = json.dumps({"error": "Request is too large."}).encode("utf-8")
                self.send_response(413)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            payload = json.loads(self.rfile.read(length) or b"{}")
            request = ListingAuditRequest.model_validate(payload)
            body = audit_listing(request).model_dump_json().encode("utf-8")
            status = 200
        except (ValueError, json.JSONDecodeError, ValidationError) as exc:
            body = json.dumps({"error": "Please complete the required listing fields.", "details": str(exc)}).encode("utf-8")
            status = 422
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

