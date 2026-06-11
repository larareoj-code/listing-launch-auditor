# Parallel Agent Passive-Income Studio

This is a no-spend v1 implementation of the planned agent system. It creates a Gumroad/Payhip-ready digital product launch package for an anonymous niche brand while blocking publishing, spend, outreach, and platform changes.

It also includes the **Listing Launch Auditor**, a local-first web utility that checks digital-product listings for readiness, missing assets, unsupported claims, and platform-specific launch steps.

## What It Does

- Runs a manager-worker workflow with specialist agent contracts.
- Produces a structured experiment card and launch package.
- Applies compliance, IP, claims, outreach, platform, and spend gates.
- Writes a learning-ledger event for every local run.
- Saves and recalls local experiment memory to reduce repeated context generation.
- Defaults to deterministic local execution so no external side effects occur.
- Includes optional OpenAI Agents SDK definitions for future live model-backed runs.

## Local Commands

From this directory:

```powershell
$env:PYTHONPATH="src"
python -m passive_income_studio.main run --niche "busy solo consultants" --output "..\..\outputs\sample_launch_package.json"
python -m passive_income_studio.main launch-batch --output-dir "..\..\outputs\launch_queue"
python -m passive_income_studio.main ingest-make-money-with-ai --csv "..\vendor\MakeMoneyWithAI\repos.csv"
python -m passive_income_studio.main ingest-income-generator --apps "..\vendor\income-generator\apps.json"
python -m passive_income_studio.main memory-search "solo consultants pricing"
python -m passive_income_studio.main health
python -m passive_income_studio.main serve-auditor --port 8790
python -m pytest
```

Open `http://127.0.0.1:8790`. Audits are deterministic and anonymous. The app records aggregate operational events in `data/app-events.jsonl`; it does not store pasted listing copy or uploaded product files.

### Subscription checkout

Pro plan buttons use Stripe Checkout and remain fail-closed until these server-side variables are configured:

```text
STRIPE_SECRET_KEY
STRIPE_PRICE_MONTHLY
STRIPE_PRICE_YEARLY
APP_URL
```

The Stripe prices should be recurring prices for `$9/month` and `$49/year`. `APP_URL` must be the deployed HTTPS origin. Payment data is collected by Stripe Checkout, not this application.

If using the bundled Codex Python from the workspace root:

```powershell
& "C:\Users\larar\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest work\passive_income_studio
```

If `pytest` is not installed in the active runtime, install the dev extra in a virtual environment or run `python evals\run_local.py` for the built-in no-side-effect eval harness.

## Safety Model

The workflow may generate internal assets and launch copy, but it never publishes, spends money, sends outreach, creates accounts, uploads products, or changes settings. Those actions are represented as blocked approval gates in the launch checklist.

## Env

`.env.local` in the workspace root stores `OPENAI_API_KEY` for future live SDK runs. The current smoke path does not call the API.

## Memory

`src/passive_income_studio/memory.py` provides a lightweight OpenMemory-shaped store with `add`, `search`, `history`, and `delete`. It uses local SQLite by default at `data/memory.sqlite`, so repeated runs can recall prior niches, pricing, risks, and decisions without regenerating that context. The full OpenMemory source has also been downloaded to `work/vendor/OpenMemory` for reference; the local adapter keeps v1 lean while preserving an upgrade path to `openmemory-py`.

The `ingest-make-money-with-ai` command summarizes `garylab/MakeMoneyWithAI`'s curated repo CSV into a compact memory record. This gives the Opportunity Scout reusable idea context without pasting hundreds of repo rows into every prompt.

The `ingest-income-generator` command summarizes `XternA/income-generator` as a high-risk bandwidth-sharing/proxy-income source. It records the opportunity class, credential/proxy requirements, and a default recommendation to keep it out of autonomous v1 unless a human completes legal, ISP, security, account, tax, and platform review.

