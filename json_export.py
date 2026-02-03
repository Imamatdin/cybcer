import json
from datetime import datetime
from typing import Any


def generate_json_report(state: Any, genome: dict, blue_team: dict, attack_graph: dict, benchmark: dict = None) -> dict:
    """Generate structured JSON report for integration with other tools."""
    
    report = {
        "meta": {
            "tool": "Cerebras Red Team Simulator",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "target": state.target_url
        },
        "summary": {
            "attack_duration_seconds": len(state.attack_log) * 1.5,  # Estimate
            "steps_executed": len(state.attack_log),
            "credentials_found": len(state.credentials),
            "footholds_gained": len(state.footholds),
            "data_exfiltrated": len(state.loot),
            "attack_successful": len(state.loot) > 0
        },
        "findings": [],
        "attack_chain": [],
        "credentials": [],
        "recommendations": []
    }
    
    # Add findings with CWE mappings
    if state.discovered_paths:
        report["findings"].append({
            "id": "FIND-001",
            "title": "Exposed Backup File",
            "severity": "CRITICAL",
            "cwe": "CWE-530",
            "cwe_name": "Exposure of Backup File to an Unauthorized Control Sphere",
            "evidence": f"Found accessible path: {state.discovered_paths}",
            "impact": "Attacker can access sensitive configuration data",
            "recommendation": "Remove backup files from web-accessible directories"
        })
    
    if state.credentials:
        report["findings"].append({
            "id": "FIND-002",
            "title": "Hardcoded Credentials",
            "severity": "CRITICAL",
            "cwe": "CWE-798",
            "cwe_name": "Use of Hard-coded Credentials",
            "evidence": f"Found credentials in config file",
            "impact": "Attacker can authenticate as privileged user",
            "recommendation": "Use environment variables or secrets manager"
        })
    
    if "webshell" in str(state.footholds):
        report["findings"].append({
            "id": "FIND-003",
            "title": "Unrestricted File Upload",
            "severity": "HIGH",
            "cwe": "CWE-434",
            "cwe_name": "Unrestricted Upload of File with Dangerous Type",
            "evidence": "Successfully uploaded PHP webshell",
            "impact": "Remote code execution on server",
            "recommendation": "Validate file types and use allowlist"
        })
    
    if state.loot:
        report["findings"].append({
            "id": "FIND-004",
            "title": "Sensitive Data Exposure",
            "severity": "CRITICAL",
            "cwe": "CWE-200",
            "cwe_name": "Exposure of Sensitive Information",
            "evidence": "Exfiltrated user database with PII",
            "impact": "Data breach affecting user privacy",
            "recommendation": "Encrypt sensitive data at rest"
        })
    
    # Add attack chain
    for i, entry in enumerate(state.attack_log, 1):
        report["attack_chain"].append({
            "step": i,
            "tool": entry.get("tool", "unknown"),
            "params": entry.get("params", {}),
            "result_preview": entry.get("result", "")[:200]
        })
    
    # Add credentials
    for cred in state.credentials:
        report["credentials"].append({
            "username": cred[0],
            "password": cred[1],
            "source": "config.php.bak"
        })
    
    # Add recommendations from genome analysis
    report["genome_analysis_summary"] = genome.get("analysis", "")[:500] + "..."
    report["blue_team_summary"] = blue_team.get("analysis", "")[:500] + "..."
    
    # Add benchmark if available
    if benchmark:
        report["benchmark"] = {
            "cerebras_latency": benchmark.get("cerebras", {}).get("avg_latency"),
            "cerebras_tokens_per_sec": benchmark.get("cerebras", {}).get("tokens_per_sec"),
            "speedup_vs_gpt4": benchmark.get("speedup")
        }
    
    return report


def save_json_report(report: dict, filename: str = "report.json"):
    """Save report to JSON file."""
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    return filename


def print_json_summary(report: dict):
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    findings_count = len(report["findings"])
    critical = sum(1 for f in report["findings"] if f["severity"] == "CRITICAL")
    high = sum(1 for f in report["findings"] if f["severity"] == "HIGH")
    
    console.print()
    console.print(Panel(
        f"[bold]JSON REPORT GENERATED[/bold]\n\n"
        f"Findings: {findings_count} total ({critical} critical, {high} high)\n"
        f"Attack steps: {len(report['attack_chain'])}\n"
        f"Credentials: {len(report['credentials'])}\n"
        f"File: report.json",
        border_style="green"
    ))
    console.print()
    
