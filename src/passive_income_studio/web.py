from __future__ import annotations

import json
import mimetypes
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from passive_income_studio.auditor import RULESET_VERSION, audit_listing
from passive_income_studio.billing import BillingConfigurationError, create_checkout_session
from passive_income_studio.schemas import ListingAuditRequest


PACKAGE_ROOT = Path(__file__).resolve().parent
WEB_ROOT = PACKAGE_ROOT / "web_assets"
DATA_ROOT = PACKAGE_ROOT.parent.parent / "data"
APP_LEDGER = DATA_ROOT / "app-events.jsonl"


def record_event(event: str, details: dict[str, object] | None = None) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "app": "listing-launch-auditor",
        "details": details or {},
    }
    with APP_LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


class AuditorHandler(BaseHTTPRequestHandler):
    server_version = "ListingLaunchAuditor/0.1"

    def _json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _asset(self, filename: str) -> None:
        target = (WEB_ROOT / filename).resolve()
        if WEB_ROOT.resolve() not in target.parents or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json({"status": "ok", "ruleset_version": RULESET_VERSION, "external_side_effects": 0})
            return
        if path == "/":
            self._asset("index.html")
            return
        if path.startswith("/assets/"):
            self._asset(path.removeprefix("/assets/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json({"error": "Invalid content length."}, HTTPStatus.BAD_REQUEST)
            return
        if length > 100_000:
            self._json({"error": "Request is too large."}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json({"error": "Request body must be valid JSON."}, HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/audit":
            try:
                request = ListingAuditRequest.model_validate(payload)
            except ValidationError as exc:
                self._json({"error": "Please complete the required listing fields.", "details": exc.errors()}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            result = audit_listing(request)
            record_event("audit_completed", {"platform": request.platform.value, "decision": result.decision, "score": result.readiness_score})
            self._json(result.model_dump(mode="json"))
            return

        if path == "/api/events":
            event = str(payload.get("event", "")).strip()
            allowed = {"app_opened", "upgrade_clicked", "export_csv", "print_report", "sample_loaded"}
            if event not in allowed:
                self._json({"error": "Unsupported event."}, HTTPStatus.BAD_REQUEST)
                return
            details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
            record_event(event, details)
            self._json({"recorded": True})
            return

        if path == "/api/checkout":
            plan = payload.get("plan")
            if plan not in {"monthly", "yearly"}:
                self._json({"error": "Choose a valid subscription plan."}, HTTPStatus.BAD_REQUEST)
                return
            origin = f"http://{self.headers.get('Host', '127.0.0.1:8790')}"
            try:
                checkout_url = create_checkout_session(plan, origin)
            except BillingConfigurationError as exc:
                self._json({"error": str(exc), "code": "billing_not_configured"}, HTTPStatus.SERVICE_UNAVAILABLE)
                return
            except Exception:
                self._json({"error": "Checkout could not be started. Please try again."}, HTTPStatus.BAD_GATEWAY)
                return
            record_event("checkout_started", {"plan": plan})
            self._json({"url": checkout_url})
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve_auditor(host: str = "127.0.0.1", port: int = 8790) -> int:
    server = ThreadingHTTPServer((host, port), AuditorHandler)
    print(f"Listing Launch Auditor running at http://{host}:{port}")
    server.serve_forever()
    return 0

