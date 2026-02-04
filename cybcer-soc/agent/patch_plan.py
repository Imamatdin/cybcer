#!/usr/bin/env python3
"""
Patch Priority Generator - ranks services by KEV/EPSS/exposure.
Deterministic, no LLM required.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))
from intel.enrich import enrich_cve_list


@dataclass
class ExposedService:
    """Service with vulnerable dependency."""
    name: str
    host: Optional[str]
    component: str  # e.g., "log4j-core"
    version: str
    cves: List[str]
    exposure: str  # internet-facing|internal|isolated
    criticality: str  # critical|high|medium|low


def calculate_priority_score(service: ExposedService, cve_intel: Dict[str, dict]) -> float:
    """Calculate priority score (higher = patch first)."""
    score = 0.0
    
    # Base score from criticality
    crit_scores = {"critical": 40, "high": 30, "medium": 20, "low": 10}
    score += crit_scores.get(service.criticality, 15)
    
    # Exposure multiplier
    exp_mult = {"internet-facing": 2.0, "internal": 1.2, "isolated": 0.8}
    score *= exp_mult.get(service.exposure, 1.0)
    
    # CVE-based scoring
    for cve in service.cves:
        intel = cve_intel.get(cve.upper(), {})
        
        # KEV = actively exploited = highest priority
        if intel.get("in_kev"):
            score += 50
        
        # EPSS score contribution
        epss = intel.get("epss_score")
        if epss:
            score += epss * 30  # 0-30 points based on EPSS
    
    return round(score, 2)


def generate_patch_plan(services: List[ExposedService], 
                        output_path: Optional[str] = None) -> List[dict]:
    """Generate prioritized patch plan."""
    
    # Collect all CVEs
    all_cves = set()
    for svc in services:
        all_cves.update(svc.cves)
    
    # Enrich CVEs
    print(f"[*] Enriching {len(all_cves)} CVEs...")
    enriched = enrich_cve_list(list(all_cves))
    cve_intel = {e["cve"]: e for e in enriched}
    
    # Calculate scores and sort
    scored = []
    for svc in services:
        score = calculate_priority_score(svc, cve_intel)
        
        # Determine urgency
        has_kev = any(cve_intel.get(c, {}).get("in_kev") for c in svc.cves)
        max_epss = max((cve_intel.get(c, {}).get("epss_score") or 0) for c in svc.cves)
        
        if has_kev or max_epss > 0.9:
            urgency = "immediate"
        elif max_epss > 0.5:
            urgency = "24h"
        elif max_epss > 0.2:
            urgency = "7d"
        else:
            urgency = "30d"
        
        scored.append({
            "service": svc.name,
            "host": svc.host,
            "component": svc.component,
            "version": svc.version,
            "cves": svc.cves,
            "exposure": svc.exposure,
            "criticality": svc.criticality,
            "priority_score": score,
            "urgency": urgency,
            "kev_flagged": has_kev,
            "max_epss": round(max_epss, 4) if max_epss else None,
            "rationale": f"KEV={has_kev}, EPSS={max_epss:.2%}, {svc.exposure}"
        })
    
    # Sort by score descending
    scored.sort(key=lambda x: x["priority_score"], reverse=True)
    
    # Add priority rank
    for i, item in enumerate(scored, 1):
        item["priority"] = i
    
    if output_path:
        with open(output_path, "w") as f:
            json.dump(scored, f, indent=2)
    
    return scored


def parse_dependency_check_report(report_path: str) -> List[ExposedService]:
    """Parse OWASP Dependency-Check JSON report to ExposedService list."""
    with open(report_path) as f:
        data = json.load(f)
    
    services = []
    for dep in data.get("dependencies", []):
        vulns = dep.get("vulnerabilities", [])
        if not vulns:
            continue
        
        cves = [v.get("name", "") for v in vulns if v.get("name", "").startswith("CVE-")]
        if not cves:
            continue
        
        services.append(ExposedService(
            name=dep.get("fileName", "unknown"),
            host=None,
            component=dep.get("fileName", ""),
            version=dep.get("version", "unknown"),
            cves=cves,
            exposure="internal",  # default; override with inventory
            criticality="medium"  # default; override with inventory
        ))
    
    return services


if __name__ == "__main__":
    # Test with sample data
    test_services = [
        ExposedService("api-gateway", "srv01", "log4j-core", "2.14.0", 
                       ["CVE-2021-44228"], "internet-facing", "critical"),
        ExposedService("payment-svc", "srv02", "log4j-core", "2.14.1",
                       ["CVE-2021-44228", "CVE-2021-45046"], "internal", "critical"),
        ExposedService("logging-svc", "srv03", "log4j-core", "2.10.0",
                       ["CVE-2021-44228"], "isolated", "low"),
    ]
    
    plan = generate_patch_plan(test_services)
    print(json.dumps(plan, indent=2))