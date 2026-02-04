from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add cybcer-soc to path
sys.path.insert(0, str(Path(__file__).parent / "cybcer-soc"))

from orchestrator import CerebrasAttacker
from genome_analysis import SecurityGenomeAnalyzer

# Load .env file
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val.strip('"').strip("'")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ RED TEAM ENDPOINT ============
@app.get("/attack")
async def run_attack(target: str):
    api_key = os.environ.get("CEREBRAS_API_KEY")
    attacker = CerebrasAttacker(api_key=api_key, target_url=target)

    if not api_key:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'message': 'CEREBRAS_API_KEY not found'})}\n\n"]),
            media_type="text/event-stream"
        )

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'think', 'content': 'Initializing attack sequence...', 'time': 0})}\n\n"
            for event in attacker.run(max_steps=20):
                yield f"data: {json.dumps(event)}\n\n"

            analyzer = SecurityGenomeAnalyzer(api_key=api_key)
            genome = analyzer.analyze(attacker.state.attack_log, attacker.state)

            yield f"data: {json.dumps({'type': 'genome', 'content': genome})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Server Error: {str(e)}'})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============ SOC AUTOPILOT ENDPOINT ============
@app.get("/soc")
async def run_soc(bots_path: str = "cybcer-soc/data/bots"):
    api_key = os.environ.get("CEREBRAS_API_KEY")
    
    if not api_key:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'message': 'CEREBRAS_API_KEY not found'})}\n\n"]),
            media_type="text/event-stream"
        )

    def generate():
        try:
            start = time.time()
            
            # Step 1: Load events
            yield f"data: {json.dumps({'type': 'status', 'step': 1, 'message': 'Ingesting events...'})}\n\n"
            
            from ingest.bots_loader import load_bots_folder, CanonicalEvent
            events = load_bots_folder(bots_path, limit=10000)
            
            if not events:
                yield f"data: {json.dumps({'type': 'status', 'step': 1, 'message': 'Using demo events...'})}\n\n"
                events = get_demo_events()
            
            yield f"data: {json.dumps({'type': 'progress', 'step': 1, 'events_count': len(events)})}\n\n"
            
            # Step 2: Build case
            yield f"data: {json.dumps({'type': 'status', 'step': 2, 'message': 'Building case...'})}\n\n"
            
            from agent.case_builder import build_case_from_events
            case_id = f"CASE-{datetime.now().strftime('%Y%m%d')}-001"
            case = build_case_from_events(events, case_id)
            
            yield f"data: {json.dumps({'type': 'progress', 'step': 2, 'hosts': len(case.hosts), 'ips': len(case.src_ips), 'evidence': len(case.evidence)})}\n\n"
            
            # Step 3: Enrich CVEs
            yield f"data: {json.dumps({'type': 'status', 'step': 3, 'message': 'Enriching CVEs (KEV + EPSS)...'})}\n\n"
            
            from intel.enrich import enrich_cve_list
            cve_intel = enrich_cve_list(["CVE-2021-44228", "CVE-2021-45046", "CVE-2021-45105"])
            
            yield f"data: {json.dumps({'type': 'progress', 'step': 3, 'cves': cve_intel})}\n\n"
            
            # Step 4: Patch plan
            yield f"data: {json.dumps({'type': 'status', 'step': 4, 'message': 'Generating patch plan...'})}\n\n"
            
            from agent.patch_plan import generate_patch_plan, ExposedService
            services = [
                ExposedService("api-gateway", "web-srv-01", "log4j-core", "2.14.0", ["CVE-2021-44228"], "internet-facing", "critical"),
                ExposedService("search-service", "app-srv-02", "log4j-core", "2.14.1", ["CVE-2021-44228", "CVE-2021-45046"], "internal", "high"),
                ExposedService("payment-processor", "app-srv-03", "log4j-core", "2.12.1", ["CVE-2021-44228"], "internal", "critical"),
                ExposedService("logging-aggregator", "log-srv-01", "log4j-core", "2.10.0", ["CVE-2021-44228"], "isolated", "medium"),
            ]
            patch_plan = generate_patch_plan(services)
            
            # Convert to serializable format
            patch_plan_data = [
                {"priority": p.priority, "service": p.service, "urgency": p.urgency, "rationale": p.rationale}
                for p in patch_plan
            ]
            
            yield f"data: {json.dumps({'type': 'progress', 'step': 4, 'patch_plan': patch_plan_data[:5]})}\n\n"
            
            # Step 5: Generate brief (Cerebras)
            yield f"data: {json.dumps({'type': 'status', 'step': 5, 'message': 'Generating incident brief (Cerebras)...'})}\n\n"
            
            llm_start = time.time()
            from llm.cerebras_client import generate_incident_brief
            brief_result = generate_incident_brief(
                case_data=case.to_dict(),
                cve_intel=cve_intel,
                patch_plan=patch_plan_data,
                provider="cerebras"
            )
            llm_time = time.time() - llm_start
            
            yield f"data: {json.dumps({'type': 'brief', 'brief': brief_result.get('brief', {}), 'time': round(llm_time, 2), 'tokens_per_sec': brief_result.get('tokens_per_sec', 0)})}\n\n"
            
            # Final summary
            total_time = time.time() - start
            yield f"data: {json.dumps({'type': 'summary', 'total_time': round(total_time, 2), 'events_count': len(events), 'cerebras_time': round(llm_time, 2), 'tokens_per_sec': brief_result.get('tokens_per_sec', 0)})}\n\n"
            
            yield "data: {\"type\": \"done\"}\n\n"
            
        except Exception as e:
            import traceback
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            print(f"SOC Error: {traceback.format_exc()}")
            yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get('/api/state')
async def api_state():
    """Return the single ui_state.json file for the frontend."""
    ui_path = Path(__file__).parent / 'cybcer-soc' / 'artifacts' / 'ui_state.json'
    if not ui_path.exists():
        return {"status": "error", "message": "ui_state.json not found"}
    try:
        with open(ui_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"Failed to read ui_state.json: {e}"}


from pydantic import BaseModel


class StartRequest(BaseModel):
    bots_path: str | None = None
    events_path: str | None = None
    scenario: str | None = None


@app.post('/api/start')
async def api_start(req: StartRequest):
    """Start a demo run in background and write initial ui_state.json with status=running.

    Accepts either `events_path` (explicit file), `bots_path`, or high-level `scenario`.
    Known scenarios: 'success', 'blocked', 'inconclusive'.
    """
    import subprocess
    soc_dir = Path(__file__).parent / 'cybcer-soc'

    # Resolve events_path from scenario if provided
    events_path = None
    if req.scenario:
        name = req.scenario.lower()
        mapping = {
            'success': soc_dir / 'data' / 'events_success.json',
            'blocked': soc_dir / 'data' / 'events_blocked.json',
            'inconclusive': soc_dir / 'data' / 'events_inconclusive.json'
        }
        if name in mapping:
            events_path = mapping[name]
    # explicit events_path overrides scenario
    if req.events_path:
        events_path = Path(req.events_path)

    # Build command
    cmd = [sys.executable, str(soc_dir / 'demo_soc.py'), '--output_dir', str(soc_dir / 'artifacts')]
    if events_path:
        cmd += ['--events_path', str(events_path)]
    elif req.bots_path:
        cmd += ['--bots_path', req.bots_path]

    try:
        subprocess.Popen(cmd, cwd=str(soc_dir))
    except Exception as e:
        return {"status": "error", "message": f"Failed to start demo: {e}"}

    # write minimal ui_state with status running so UI flips immediately
    ui_path = soc_dir / 'artifacts' / 'ui_state.json'
    try:
        ui = {"run_id": datetime.utcnow().isoformat() + 'Z', "status": "running", "metrics": {}, "red": {}, "blue": {}}
        ui_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ui_path, 'w', encoding='utf-8') as f:
            json.dump(ui, f)
    except Exception as e:
        return {"status": "error", "message": f"Failed to write ui_state: {e}"}

    return {"status": "started"}


def get_demo_events():
    """Return demo events when no BOTS data available."""
    from ingest.bots_loader import CanonicalEvent
    
    demo_data = [
        {"ts": "2024-01-15T10:01:00Z", "source": "bots", "event_type": "web", "host": "web-srv-01",
         "src_ip": "203.0.113.50", "dst_ip": "10.0.1.20", "severity": "high",
         "message": "GET /api/search?q=[log4j-jndi-pattern:redacted] HTTP/1.1 200", "fields": {}},
        {"ts": "2024-01-15T10:01:01Z", "source": "bots", "event_type": "dns", "host": "web-srv-01",
         "src_ip": "10.0.1.20", "message": "DNS query: suspicious-domain.com -> 198.51.100.10", "fields": {}},
        {"ts": "2024-01-15T10:01:02Z", "source": "bots", "event_type": "alert", "host": "web-srv-01",
         "src_ip": "10.0.1.20", "dst_ip": "198.51.100.10", "severity": "critical",
         "message": "IDS Alert: Outbound LDAP to suspicious IP 198.51.100.10:1389", "fields": {}},
        {"ts": "2024-01-15T10:01:03Z", "source": "bots", "event_type": "process", "host": "web-srv-01",
         "severity": "critical", "message": "Java process loaded remote class from 198.51.100.10", "fields": {}},
        {"ts": "2024-01-15T10:01:04Z", "source": "bots", "event_type": "process", "host": "web-srv-01",
         "user": "www-data", "severity": "critical",
         "message": "Process spawned: shell command execution detected", "fields": {}},
        {"ts": "2024-01-15T10:01:05Z", "source": "bots", "event_type": "alert", "host": "web-srv-01",
         "src_ip": "10.0.1.20", "dst_ip": "198.51.100.10", "severity": "high",
         "message": "Netflow: Large outbound transfer detected (15KB)", "fields": {}},
        {"ts": "2024-01-15T10:01:10Z", "source": "bots", "event_type": "file", "host": "web-srv-01",
         "user": "www-data", "severity": "high",
         "message": "Sensitive file access: /etc/passwd", "fields": {}},
        {"ts": "2024-01-15T10:01:15Z", "source": "bots", "event_type": "auth", "host": "web-srv-01",
         "user": "www-data", "severity": "critical",
         "message": "Privilege escalation attempt detected", "fields": {}},
    ]
    
    return [CanonicalEvent.from_dict(e) for e in demo_data]


@app.get("/health")
async def health():
    return {"status": "ok", "modes": ["red", "soc"]}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', '8000'))
    uvicorn.run(app, host="0.0.0.0", port=port)