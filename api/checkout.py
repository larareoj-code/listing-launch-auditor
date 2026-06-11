from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from passive_income_studio.billing import BillingConfigurationError, create_checkout_session  # noqa: E402


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
            if length > 10_000:
                self._respond({"error": "Request is too large."}, 413)
                return
            payload = json.loads(self.rfile.read(length) or b"{}")
            plan = payload.get("plan")
            if plan not in {"monthly", "yearly"}:
                self._respond({"error": "Choose a valid subscription plan."}, 400)
                return
            forwarded_proto = self.headers.get("x-forwarded-proto", "https")
            host = self.headers.get("host", "")
            checkout_url = create_checkout_session(plan, f"{forwarded_proto}://{host}")
            self._respond({"url": checkout_url}, 200)
        except BillingConfigurationError as exc:
            self._respond({"error": str(exc), "code": "billing_not_configured"}, 503)
        except (ValueError, json.JSONDecodeError):
            self._respond({"error": "Request body must be valid JSON."}, 400)
        except Exception:
            self._respond({"error": "Checkout could not be started. Please try again."}, 502)

