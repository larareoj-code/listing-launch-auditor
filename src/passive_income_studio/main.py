from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - used when optional dependency is absent

    def load_dotenv(path: Path) -> bool:
        if not path.exists():
            return False
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return True

from passive_income_studio.memory import LocalMemory
from passive_income_studio.exporter import export_product_bundle
from passive_income_studio.idea_sources import load_income_generator, load_make_money_with_ai
from passive_income_studio.orchestrator import PortfolioOrchestrator, agent_roster
from passive_income_studio.portfolio import generate_launch_queue
from passive_income_studio.schemas import Platform
from passive_income_studio.web import serve_auditor


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"status": "ok", "external_side_effects": 0}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def run_command(args: argparse.Namespace) -> int:
    load_dotenv(Path.cwd() / ".env.local")
    platform = Platform.payhip if args.platform.lower() == "payhip" else Platform.gumroad
    memory = None if args.no_memory else LocalMemory(Path(args.memory_db).resolve())
    orchestrator = PortfolioOrchestrator(brand_name=args.brand, memory=memory)
    package = orchestrator.run(niche=args.niche, platform=platform)

    output_path = Path(args.output).resolve()
    orchestrator.write_package(package, output_path)
    orchestrator.append_ledger(package, Path(args.ledger).resolve())

    print(json.dumps({
        "output": str(output_path),
        "decision": package.experiment.decision.value,
        "approval_status": package.experiment.approval_status.value,
        "risk_count": len(package.experiment.risk_flags),
        "memory_enabled": memory is not None,
        "external_side_effects": 0,
    }, indent=2))
    return 0


def launch_batch_command(args: argparse.Namespace) -> int:
    load_dotenv(Path.cwd() / ".env.local")
    memory = None if args.no_memory else LocalMemory(Path(args.memory_db).resolve())
    orchestrator = PortfolioOrchestrator(brand_name=args.brand, memory=memory)
    manifest = generate_launch_queue(orchestrator, Path(args.output_dir).resolve())
    print(json.dumps(manifest["summary"], indent=2))
    return 0


def export_product_command(args: argparse.Namespace) -> int:
    manifest = export_product_bundle(Path(args.package).resolve(), Path(args.output_dir).resolve())
    print(json.dumps(manifest, indent=2))
    return 0


def memory_search_command(args: argparse.Namespace) -> int:
    memory = LocalMemory(Path(args.memory_db).resolve())
    results = memory.search_sync(args.query, user_id=args.user_id, limit=args.limit)
    print(json.dumps([result.__dict__ for result in results], indent=2))
    return 0


def ingest_make_money_command(args: argparse.Namespace) -> int:
    digest = load_make_money_with_ai(Path(args.csv).resolve(), limit=args.limit)
    memory = LocalMemory(Path(args.memory_db).resolve())
    memory.add_sync(
        (
            f"Source {digest['source']} contains {digest['rows_total']} AI monetization repo ideas. "
            f"Top categories: {digest['category_counts']}. "
            f"Top examples: {' | '.join(digest['top_ideas'][:10])}"
        ),
        user_id=args.user_id,
        tags=["idea-source", "github", "make-money-with-ai"],
        meta={
            "source": digest["source"],
            "rows_total": digest["rows_total"],
            "rows_ingested": digest["rows_ingested"],
            "category_counts": digest["category_counts"],
        },
    )
    print(json.dumps(digest, indent=2))
    return 0


def ingest_income_generator_command(args: argparse.Namespace) -> int:
    digest = load_income_generator(Path(args.apps).resolve())
    memory = LocalMemory(Path(args.memory_db).resolve())
    memory.add_sync(
        (
            f"Source {digest['source']} catalogs {digest['apps_total']} bandwidth-sharing/proxy income apps. "
            f"Enabled apps={digest['enabled_apps']}; credentialed apps={digest['credentialed_apps']}; "
            f"proxy/device apps={digest['proxy_or_device_apps']}. Recommendation: {digest['recommendation']} "
            f"Sample risk notes: {' | '.join(digest['risk_notes'][:8])}"
        ),
        user_id=args.user_id,
        tags=["idea-source", "github", "income-generator", "high-risk", "bandwidth-sharing"],
        meta={
            "source": digest["source"],
            "apps_total": digest["apps_total"],
            "enabled_apps": digest["enabled_apps"],
            "credentialed_apps": digest["credentialed_apps"],
            "proxy_or_device_apps": digest["proxy_or_device_apps"],
            "recommendation": digest["recommendation"],
        },
    )
    print(json.dumps(digest, indent=2))
    return 0


def roster_command() -> int:
    print(json.dumps(agent_roster(), indent=2))
    return 0


def health_command() -> int:
    print(json.dumps({"status": "ok", "external_side_effects": 0}, indent=2))
    return 0


def serve() -> int:
    port = int(os.environ.get("PORT", "8787"))
    server = HTTPServer(("127.0.0.1", port), HealthHandler)
    print(f"Serving health endpoint on http://127.0.0.1:{port}/health")
    server.serve_forever()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parallel Agent Passive-Income Studio")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Generate a no-side-effect launch package")
    run_parser.add_argument("--niche", default="busy solo consultants")
    run_parser.add_argument("--platform", default="gumroad", choices=["gumroad", "payhip"])
    run_parser.add_argument("--brand", default="Quiet Systems Lab")
    run_parser.add_argument("--output", default="outputs/sample_launch_package.json")
    run_parser.add_argument("--ledger", default="data/learning-ledger.jsonl")
    run_parser.add_argument("--memory-db", default="data/memory.sqlite")
    run_parser.add_argument("--no-memory", action="store_true")
    batch_parser = subparsers.add_parser("launch-batch", help="Generate a ranked batch of launch-ready packages")
    batch_parser.add_argument("--brand", default="Quiet Systems Lab")
    batch_parser.add_argument("--output-dir", default="outputs/launch_queue")
    batch_parser.add_argument("--memory-db", default="data/memory.sqlite")
    batch_parser.add_argument("--no-memory", action="store_true")
    export_parser = subparsers.add_parser("export-product", help="Create buyer-facing files and ZIP for one launch package")
    export_parser.add_argument("--package", required=True)
    export_parser.add_argument("--output-dir", required=True)

    subparsers.add_parser("roster", help="Print agent roster")
    subparsers.add_parser("health", help="Print health JSON")
    subparsers.add_parser("serve", help="Start /health server")
    auditor_parser = subparsers.add_parser("serve-auditor", help="Start the Listing Launch Auditor web app")
    auditor_parser.add_argument("--host", default="127.0.0.1")
    auditor_parser.add_argument("--port", type=int, default=8790)
    memory_parser = subparsers.add_parser("memory-search", help="Search local experiment memory")
    memory_parser.add_argument("query")
    memory_parser.add_argument("--memory-db", default="data/memory.sqlite")
    memory_parser.add_argument("--user-id", default="passive-income-studio")
    memory_parser.add_argument("--limit", type=int, default=5)
    ingest_parser = subparsers.add_parser("ingest-make-money-with-ai", help="Summarize garylab/MakeMoneyWithAI repos.csv into memory")
    ingest_parser.add_argument("--csv", required=True)
    ingest_parser.add_argument("--memory-db", default="data/memory.sqlite")
    ingest_parser.add_argument("--user-id", default="passive-income-studio")
    ingest_parser.add_argument("--limit", type=int, default=40)
    income_parser = subparsers.add_parser("ingest-income-generator", help="Summarize XternA/income-generator apps.json into high-risk memory")
    income_parser.add_argument("--apps", required=True)
    income_parser.add_argument("--memory-db", default="data/memory.sqlite")
    income_parser.add_argument("--user-id", default="passive-income-studio")
    return parser


def main() -> int:
    if os.environ.get("PORT") and len(os.sys.argv) == 1:
        return serve()

    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run":
        return run_command(args)
    if args.command == "launch-batch":
        return launch_batch_command(args)
    if args.command == "export-product":
        return export_product_command(args)
    if args.command == "roster":
        return roster_command()
    if args.command == "health":
        return health_command()
    if args.command == "serve":
        return serve()
    if args.command == "serve-auditor":
        load_dotenv(Path.cwd() / ".env.local")
        return serve_auditor(args.host, args.port)
    if args.command == "memory-search":
        return memory_search_command(args)
    if args.command == "ingest-make-money-with-ai":
        return ingest_make_money_command(args)
    if args.command == "ingest-income-generator":
        return ingest_income_generator_command(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

