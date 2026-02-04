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
from llm.cerebras_client import generate_incident_brief, generate_incident_brief_parallel


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
# Sanitized: no actual payloads, consistent with api.py demo events
DEMO_EVENTS = [
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


def run_soc_demo(bots_path: str = None, events_path: str = None, rate: int = 2000, window_size: int = 300,
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

    # Data source diagnostics
    print(f"[DATA] events_path={events_path!r}")
    if events_path:
        print(f"[DATA] exists={Path(events_path).exists()} size={Path(events_path).stat().st_size if Path(events_path).exists() else 'NA'}")
    else:
        print(f"[DATA] bots_path={bots_path!r} exists={Path(bots_path).exists() if bots_path else False}")

    # Require a provided events_path or existing bots_path; fail loud otherwise
    if events_path:
        ep = Path(events_path)
        if not ep.exists():
            raise FileNotFoundError(f"events_path not found: {events_path}")

        # Load JSONL or JSON list, map fields to canonical shape
        raw = []
        if ep.suffix == '.jsonl':
            with open(ep, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    raw.append(json.loads(line))
        else:
            with open(ep, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    raw = data
                else:
                    raw = [data]

        events = []
        for e in raw:
            # map common fields
            ts = e.get('ts') or e.get('timestamp') or e.get('_time')
            event_type = e.get('event_type') or e.get('sourcetype') or e.get('source')
            dst_ip = e.get('dst_ip') or e.get('dest_ip') or e.get('dst')
            src_ip = e.get('src_ip') or e.get('source_ip') or e.get('src')
            host = e.get('host') or e.get('hostname')
            user = e.get('user') or e.get('username')
            message = e.get('message') or e.get('msg') or ''

            ev = {
                'ts': ts,
                'event_type': event_type,
                'host': host,
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'user': user,
                'severity': e.get('severity') or e.get('sev') or 'low',
                'message': message,
                'fields': e.get('fields', {})
            }
            events.append(CanonicalEvent.from_dict(ev))
        print(f"      Loaded {len(events)} events from {events_path}")
    else:
        # require bots_path to exist
        if not bots_path or not Path(bots_path).exists():
            raise FileNotFoundError(f"No events_path provided and bots_path not found: {bots_path}")
        events = load_bots_folder(bots_path, limit=10000)
        print(f"      Loaded {len(events)} events from {bots_path}")
    
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
    # STEP 5: LLM incident brief (Cerebras + optional Gemini PARALLEL)
    # ─────────────────────────────────────────────────────────────────────
    # Initialize compare tracking
    compare_info = {
        "enabled": compare_gemini,
        "cerebras": {"called": False, "ok": False, "latency_ms": 0, "error": None},
        "gemini": {"called": False, "ok": False, "latency_ms": 0, "error": None},
        "speedup": None
    }

    if compare_gemini:
        # PARALLEL comparison - both calls run simultaneously
        print("[5/6] Generating incident briefs (Cerebras + Gemini PARALLEL)...")
        llm_start = time.time()

        parallel_results = generate_incident_brief_parallel(
            case_data=case.to_dict(),
            cve_intel=cve_intel,
            patch_plan=patch_plan
        )

        # Extract Cerebras result
        cerebras_result = parallel_results.get("cerebras", {})
        brief_result = cerebras_result  # Use Cerebras as primary

        # Update bench with Cerebras metrics
        bench["cerebras_time_sec"] = cerebras_result.get("generation_time_sec", 0)
        bench["cerebras_tokens_out"] = cerebras_result.get("tokens_out", 0)
        bench["cerebras_tokens_per_sec"] = cerebras_result.get("tokens_per_sec", 0)

        # Update compare info for Cerebras
        compare_info["cerebras"]["called"] = True
        compare_info["cerebras"]["ok"] = cerebras_result.get("ok", False)
        compare_info["cerebras"]["latency_ms"] = int(bench["cerebras_time_sec"] * 1000)
        compare_info["cerebras"]["error"] = cerebras_result.get("error")

        # Update bench with Gemini metrics
        gemini_result = parallel_results.get("gemini", {})
        bench["gemini_time_sec"] = gemini_result.get("generation_time_sec", 0)
        bench["gemini_ok"] = gemini_result.get("ok", False)
        bench["gemini_error"] = gemini_result.get("error")

        # Update compare info for Gemini
        compare_info["gemini"]["called"] = True
        compare_info["gemini"]["ok"] = gemini_result.get("ok", False)
        compare_info["gemini"]["latency_ms"] = int(bench["gemini_time_sec"] * 1000)
        compare_info["gemini"]["error"] = gemini_result.get("error")

        # Speedup calculation
        if parallel_results.get("both_ok"):
            bench["speedup_vs_gemini"] = parallel_results.get("speedup", 0)
            compare_info["speedup"] = bench["speedup_vs_gemini"]
            print(f"      Cerebras: {bench['cerebras_time_sec']}s ({bench['cerebras_tokens_per_sec']} tok/s)")
            print(f"      Gemini:   {bench['gemini_time_sec']}s")
            print(f"      >>> CEREBRAS SPEEDUP: {bench['speedup_vs_gemini']}x faster <<<")
        else:
            print(f"      Cerebras: {bench['cerebras_time_sec']}s - {'OK' if compare_info['cerebras']['ok'] else 'FAILED: ' + str(compare_info['cerebras']['error'])}")
            print(f"      Gemini:   {bench['gemini_time_sec']}s - {'OK' if compare_info['gemini']['ok'] else 'FAILED: ' + str(compare_info['gemini']['error'])}")
            if not compare_info["gemini"]["ok"]:
                print(f"      [!] Gemini failed - speedup cannot be calculated")

        bench["parallel_time_sec"] = parallel_results.get("parallel_time_sec", 0)
        print(f"      Parallel wall time: {bench['parallel_time_sec']}s")
        print()

    else:
        # Cerebras only (no comparison)
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

        compare_info["cerebras"]["called"] = True
        compare_info["cerebras"]["ok"] = brief_result.get("ok", False)
        compare_info["cerebras"]["latency_ms"] = int(bench["cerebras_time_sec"] * 1000)
        compare_info["cerebras"]["error"] = brief_result.get("error")

        print(f"      Time: {bench['cerebras_time_sec']}s, Speed: {bench['cerebras_tokens_per_sec']} tokens/sec")

    # Write brief artifact
    brief_path = artifacts_dir / "incident_brief.json"
    with open(brief_path, "w") as f:
        json.dump(brief_result.get("brief", brief_result), f, indent=2)
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

    # Store compare info in bench for ui_state
    bench["compare"] = compare_info

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

    # Red stage heuristic - matches stage-locked data from gen_wargame_data.py
    # Moved outside build_ui_state so it can be called independently
    def detect_stage(evts):
        types = " ".join([str(getattr(x, 'event_type', x.get('event_type') if isinstance(x, dict) else '')) for x in evts]).lower()
        msgs = " ".join([str(getattr(x, 'message', x.get('message') if isinstance(x, dict) else '')) for x in evts]).lower()

        # Check for blocked indicator first
        if 'blocked' in msgs or 'egress blocked' in msgs:
            return 'blocked'

        # Stage detection based on attack chain phases
        # Stage 7: auth anomalies / lateral movement
        if 'auth' in types or 'auth fail' in msgs or 'auth success' in msgs or 'privilege' in msgs or 'sudo' in msgs:
            return 'lateral_auth'

        # Stage 6: exfil spike (large bytes_out)
        if 'bytes_out=' in msgs:
            # Check for large transfers (exfil indicator)
            import re
            bytes_matches = re.findall(r'bytes_out=(\d+)', msgs)
            if any(int(b) > 100000 for b in bytes_matches):
                return 'exfil_suspected'

        # Stage 5: sensitive file access
        if 'file_read' in msgs or 'sensitive' in msgs or 'sensitive:redacted' in msgs:
            return 'file_access'

        # Stage 4: EDR anomalies (process + net)
        if 'edr' in types or 'child' in msgs or 'process_start' in msgs or 'net_connect' in msgs:
            return 'edr_anomaly'

        # Stage 3: LDAP egress
        if 'ldap' in msgs or 'outbound ldap' in msgs or ':389' in msgs:
            return 'ldap_egress'

        # Stage 2: DNS callbacks
        if 'dns' in types or 'unusual domain' in msgs or 'callback' in msgs:
            return 'dns_callbacks'

        # Stage 1: Web indicator
        if 'log4j' in msgs or 'jndi' in msgs or 'indicator:redacted' in msgs:
            return 'web_indicator'

        # No attack indicators found - incomplete analysis
        if not evts:
            return 'incomplete'

        return 'complete'

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

    # write final ui_state atomically (status=done) and include result
    ui_state_path = artifacts_dir / "ui_state.json"
    try:
        # Determine result based on detected stage
        detected_stage = detect_stage(events)

        # Explicit result classification based on attack chain stage
        if detected_stage == 'blocked':
            result_status = 'blocked'
        elif detected_stage in ('exfil_suspected', 'lateral_auth'):
            result_status = 'success'  # Full attack chain detected
        elif detected_stage in ('incomplete', 'web_indicator', 'dns_callbacks'):
            result_status = 'inconclusive'  # Insufficient evidence
        elif not case or not getattr(case, 'evidence', None):
            result_status = 'inconclusive'
        else:
            result_status = 'success'

        final_ui = build_ui_state(status="done")  # Changed from "complete" to "done" for frontend
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
    parser.add_argument("--events_path", help="Path to a single events JSON/JSONL file to use (overrides bots_path)")
    parser.add_argument("--rate", "-r", type=int, default=2000, help="Replay rate (events/sec)")
    parser.add_argument("--window_size", "-w", type=int, default=300, help="Window size for batching")
    parser.add_argument("--output_dir", "-o", default="artifacts", help="Output directory")
    parser.add_argument("--compare", "-c", action="store_true", help="Compare Cerebras vs Gemini")
    
    args = parser.parse_args()
    # Data source banner
    print(f"[DATA] args.events_path={args.events_path!r}")
    print(f"[DATA] args.bots_path={args.bots_path!r} exists={Path(args.bots_path).exists() if args.bots_path else False}")
    
    run_soc_demo(
        bots_path=args.bots_path,
        events_path=args.events_path,
        rate=args.rate,
        window_size=args.window_size,
        output_dir=args.output_dir,
        compare_gemini=args.compare
    )


if __name__ == "__main__":
    main()