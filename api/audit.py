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
    def _respond(self, payload: object, status: int) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 100_000:
                self._respond({"error": "Request is too large."}, 413)
                return
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("Request must be an object.")
            request = ListingAuditRequest.model_validate(payload)
            self._respond(audit_listing(request).model_dump(mode="json"), 200)
        except (ValueError, json.JSONDecodeError, ValidationError):
            self._respond({"error": "Please complete the required listing fields."}, 422)
        except Exception:
            self._respond({"error": "The audit could not be completed. Please try again."}, 500)

