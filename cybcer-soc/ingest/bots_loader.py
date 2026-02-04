#!/usr/bin/env python3
"""
Splunk BOTS v3 log loader -> canonical events.
"""

import json
import csv
from pathlib import Path
from typing import Generator, List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class CanonicalEvent:
    """Normalized event format."""
    ts: str
    source: str
    event_type: str
    message: str
    host: Optional[str] = None
    user: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    severity: Optional[str] = None
    fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: dict) -> "CanonicalEvent":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def normalize_bots_event(row: dict) -> CanonicalEvent:
    ts = row.get("_time") or row.get("timestamp") or row.get("ts", "")
    
    sourcetype = row.get("sourcetype", "").lower()
    if "auth" in sourcetype or "login" in sourcetype:
        event_type = "auth"
    elif "web" in sourcetype or "access" in sourcetype or "http" in sourcetype:
        event_type = "web"
    elif "dns" in sourcetype:
        event_type = "dns"
    elif "process" in sourcetype or "sysmon" in sourcetype:
        event_type = "process"
    elif "file" in sourcetype:
        event_type = "file"
    elif "alert" in sourcetype or "ids" in sourcetype:
        event_type = "alert"
    else:
        event_type = "other"
    
    host = row.get("host") or row.get("hostname") or row.get("dest_host")
    user = row.get("user") or row.get("username") or row.get("src_user")
    src_ip = row.get("src_ip") or row.get("src") or row.get("clientip")
    dst_ip = row.get("dest_ip") or row.get("dest") or row.get("dst")
    
    severity = row.get("severity") or row.get("priority")
    if severity:
        severity = str(severity).lower()
        if severity in ["1", "critical", "crit"]:
            severity = "critical"
        elif severity in ["2", "high"]:
            severity = "high"
        elif severity in ["3", "medium", "med"]:
            severity = "med"
        else:
            severity = "low"
    
    message = row.get("_raw") or row.get("message") or row.get("event") or str(row)[:500]
    
    return CanonicalEvent(
        ts=ts, source="bots", event_type=event_type, message=message[:1000],
        host=host, user=user, src_ip=src_ip, dst_ip=dst_ip, severity=severity,
        fields={k: v for k, v in row.items() if k not in ["_raw", "message"]}
    )


def load_bots_csv(filepath: str, limit: int = None) -> Generator[CanonicalEvent, None, None]:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            yield normalize_bots_event(row)


def load_bots_json(filepath: str, limit: int = None) -> Generator[CanonicalEvent, None, None]:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            try:
                yield normalize_bots_event(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue


def load_bots_folder(folder: str = "data/bots", limit: int = 10000) -> List[CanonicalEvent]:
    folder = Path(folder)
    if not folder.exists():
        return []
    
    events = []
    count = 0
    for f in sorted(folder.glob("*.csv")):
        for e in load_bots_csv(str(f), limit - count if limit else None):
            events.append(e)
            count += 1
            if limit and count >= limit:
                return events
    for f in sorted(folder.glob("*.json*")):
        for e in load_bots_json(str(f), limit - count if limit else None):
            events.append(e)
            count += 1
            if limit and count >= limit:
                return events
    return events


def write_canonical_jsonl(events: List[CanonicalEvent], output_path: str):
    with open(output_path, "w") as f:
        for e in events:
            f.write(e.to_json() + "\n")