# Cybcer — Cerebras Red Team + SOC Autopilot

Autonomous AI-powered penetration testing that exploits vulnerabilities in seconds, then a Cerebras-powered SOC agent analyzes the attack, builds an incident case, and generates a patch plan — all in real time.

## Modes

| Mode | What it does |
|---|---|
| **Red Team** | AI agent autonomously hacks a target: recon → cred steal → webshell → exfil |
| **SOC Autopilot** | Ingests attack telemetry, builds a case, enriches CVEs, generates an incident brief via Cerebras |

## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
cd ui && npm install
```

### Set API Key

Copy `.env.example` to `.env` and fill in your key:

```bash
cp .env.example .env
# edit .env — set CEREBRAS_API_KEY
```

### Run (3 terminals)

**Terminal 1 — Backend API** (FastAPI, port 8000)
```powershell
python api.py
```

**Terminal 2 — Frontend** (Vite + React, port 5173)
```powershell
cd ui
npm run dev
```

**Terminal 3 — Vulnerable target app** (Flask, port 5000)
```powershell
cd vulnerable_app
python app.py
```

Open [http://localhost:5173](http://localhost:5173) in your browser. The Vite dev server proxies `/api`, `/attack`, and `/soc` through to the backend automatically.

## How It Works

### Red Team flow
1. You enter a target URL (defaults to `localhost:5000`)
2. Orchestrator does a preflight check — if the port is down it scans fallback ports and `localhost` automatically
3. Cerebras LLM runs a ReAct loop: THINK → ACTION → OBSERVE, up to 20 steps
4. Attack log + summary stream back to the UI in real time via SSE
5. Security Genome Analysis runs after the attack completes

### SOC Autopilot flow
1. Pick a scenario (Attack Chain Detected / Attack Blocked / Insufficient Evidence)
2. Backend spawns `demo_soc.py` which runs the full pipeline:
   - Ingest events → Build case → Enrich CVEs (KEV + EPSS) → Generate patch plan → Cerebras incident brief
3. `ui_state.json` is written atomically; the frontend polls `/api/state` every 750 ms
4. Results render as a full incident dashboard (entities, MITRE ATT&CK, containment, patch priority, timeline)

### Vulnerable app telemetry
The target app (`vulnerable_app/app.py`) emits SOC-canonical events on every request via an `after_request` hook:
- Every hit → `web` event
- `/login` POST → `auth` event (success or fail)
- `/backup/*` → `file` event (sensitive file read)
- `/uploads/*.php?cmd=…` → `process` + `edr` + optional `exfil` events
- `/admin` burst (>3 hits / 5s) → `alert` event

Events are written to `vulnerable_app/logs/events.jsonl` and exposed at `GET /telemetry?n=100`.

## Project Structure

```
cybcer/
├── api.py                      # FastAPI backend — /attack (SSE), /api/start, /api/state
├── orchestrator.py             # Red team ReAct loop + preflight port scan
├── tools.py                    # Attack tools (http_request, scan_paths, try_login, upload, exec)
├── prompts.py                  # LLM prompt templates
├── output.py                   # Terminal + SSE event formatting
├── genome_analysis.py          # Security Genome post-attack analysis
├── blue_team.py                # Blue team replay analysis
├── attack_graph.py             # Attack graph generation
├── benchmark.py                # Speed benchmark harness
├── main.py                     # CLI entry point (standalone, no UI needed)
├── .env.example                # API key template
│
├── vulnerable_app/
│   ├── app.py                  # Flask target + telemetry hook + /telemetry endpoint
│   ├── templates/
│   │   ├── login.html
│   │   └── admin.html
│   └── uploads/
│
├── cybcer-soc/
│   ├── demo_soc.py             # SOC pipeline runner (ingest → case → enrich → brief)
│   ├── ingest/                 # Event ingestion + canonical format
│   ├── agent/                  # Case builder + patch planner
│   ├── intel/                  # CVE enrichment (KEV + EPSS)
│   ├── llm/                    # Cerebras client + parallel Gemini comparison
│   └── data/                   # Scenario event files (success / blocked / inconclusive)
│
├── ui/
│   ├── vite.config.js          # Proxy rules → :8000
│   ├── src/
│   │   ├── App.jsx             # Mode toggle (Red / SOC), routing
│   │   ├── hooks/
│   │   │   ├── useAttackStream.js   # SSE consumer for red team
│   │   │   └── useSOCStream.js      # Polling consumer for SOC
│   │   └── components/
│   │       ├── AttackLaunch.jsx     # Target URL input
│   │       ├── AttackProgress.jsx   # Live attack feed
│   │       ├── EventCard.jsx        # Single event renderer
│   │       ├── ResultsDashboard.jsx # Post-attack summary + log + genome
│   │       └── SOCDashboard.jsx     # Full SOC incident dashboard
│   └── package.json
│
└── requirements.txt
```

## CLI (no UI)

You can still run red team attacks from the command line:

```bash
python main.py --target http://localhost:5000 [options]

Options:
  --target, -t          Target URL (required)
  --api-key, -k         Cerebras API key (or set CEREBRAS_API_KEY)
  --max-steps, -s       Max attack steps (default: 20)
  --model, -m           Cerebras model
  --skip-genome         Skip genome analysis
  --benchmark           Run speed benchmark after attack
  --json-output         Write JSON report to disk
  --fail-on-critical    Exit code 1 if exfiltration detected (CI/CD)
  --allowed-hosts       Comma-separated allowlist of target hosts (safety)
```

## API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/attack?target=URL` | SSE stream — red team attack events |
| GET | `/soc?bots_path=…` | SSE stream — SOC pipeline events |
| POST | `/api/start` | Start a SOC demo run (body: `{scenario, events_path, bots_path}`) |
| GET | `/api/state` | Poll current SOC run state (`ui_state.json`) |
| GET | `/health` | Liveness check |

Target app:
| GET | `/telemetry?n=100` | Last N SOC-canonical events from the vulnerable app |

## Built for

Cerebras "Need for Speed" Challenge.
