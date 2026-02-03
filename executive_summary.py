from typing import Any


def generate_executive_summary(state: Any, attack_time: float, genome: dict, benchmark: dict = None) -> dict:
    """Generate executive summary for non-technical stakeholders."""
    
    # Calculate risk score
    risk_factors = 0
    if state.credentials:
        risk_factors += 3
    if state.footholds:
        risk_factors += 2
    if state.loot:
        risk_factors += 4
    if len(state.attack_log) < 10:
        risk_factors += 1  # Fast attack = easy target
    
    risk_score = min(risk_factors, 10)
    
    risk_level = "LOW" if risk_score < 4 else "MEDIUM" if risk_score < 7 else "CRITICAL"
    
    summary = {
        "risk_score": f"{risk_score}/10",
        "risk_level": risk_level,
        "attack_duration": f"{attack_time:.1f} seconds",
        "bottom_line": "",
        "top_findings": [],
        "immediate_actions": [],
        "business_impact": ""
    }
    
    # Generate bottom line
    if state.loot:
        summary["bottom_line"] = f"BREACH SUCCESSFUL: Attacker exfiltrated sensitive data in {attack_time:.0f} seconds."
        summary["business_impact"] = "High risk of regulatory fines, reputational damage, and customer notification requirements."
    elif state.footholds:
        summary["bottom_line"] = f"PARTIAL BREACH: Attacker gained system access but did not exfiltrate data."
        summary["business_impact"] = "System integrity compromised. Full incident response required."
    else:
        summary["bottom_line"] = "ATTACK BLOCKED: Security controls prevented full compromise."
        summary["business_impact"] = "Minimal impact, but vulnerabilities exist that require remediation."
    
    # Top findings
    if state.discovered_paths:
        summary["top_findings"].append("Sensitive backup files exposed to internet")
    if state.credentials:
        summary["top_findings"].append("Hardcoded credentials discovered and exploited")
    if "webshell" in str(state.footholds):
        summary["top_findings"].append("Unrestricted file upload allowed remote code execution")
    if state.loot:
        summary["top_findings"].append("User database with PII successfully exfiltrated")
    
    # Immediate actions
    summary["immediate_actions"] = [
        "Remove all backup files from web-accessible directories",
        "Rotate all credentials found in config files",
        "Implement file upload validation",
        "Enable web application firewall",
        "Conduct full incident response"
    ][:3]  # Top 3
    
    return summary


def print_executive_summary(summary: dict):
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    
    console = Console()
    
    # Color based on risk
    color = "green" if summary["risk_level"] == "LOW" else "yellow" if summary["risk_level"] == "MEDIUM" else "red"
    
    console.print()
    console.print(Panel(
        f"[bold {color}]EXECUTIVE SUMMARY[/bold {color}]\n\n"
        f"[bold]Risk Score:[/bold] {summary['risk_score']} ({summary['risk_level']})\n"
        f"[bold]Attack Duration:[/bold] {summary['attack_duration']}\n\n"
        f"[bold]Bottom Line:[/bold]\n{summary['bottom_line']}\n\n"
        f"[bold]Business Impact:[/bold]\n{summary['business_impact']}",
        border_style=color
    ))
    
    if summary["top_findings"]:
        console.print("\n[bold]Top Findings:[/bold]")
        for i, finding in enumerate(summary["top_findings"], 1):
            console.print(f"  {i}. {finding}")
    
    if summary["immediate_actions"]:
        console.print("\n[bold]Immediate Actions Required:[/bold]")
        for i, action in enumerate(summary["immediate_actions"], 1):
            console.print(f"  {i}. {action}")
    
    console.print()
