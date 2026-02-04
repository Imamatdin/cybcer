#!/usr/bin/env python3
"""
CISA KEV (Known Exploited Vulnerabilities) loader with cache.
"""

import json
import os
from pathlib import Path
from typing import Set, Optional
import urllib.request

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "kev.json"


def fetch_kev_online() -> dict:
    """Fetch KEV from CISA."""
    with urllib.request.urlopen(KEV_URL, timeout=15) as r:
        return json.loads(r.read())


def load_kev(use_cache: bool = True, update_cache: bool = True) -> Set[str]:
    """Load KEV CVE IDs. Cache-first."""
    CACHE_DIR.mkdir(exist_ok=True)
    
    # Try cache first
    if use_cache and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
            return {v["cveID"] for v in data.get("vulnerabilities", [])}
        except Exception as e:
            print(f"[!] KEV cache read failed: {e}")
    
    # Fetch online
    try:
        data = fetch_kev_online()
        if update_cache:
            with open(CACHE_FILE, "w") as f:
                json.dump(data, f)
        return {v["cveID"] for v in data.get("vulnerabilities", [])}
    except Exception as e:
        print(f"[!] KEV fetch failed: {e}")
        return set()


def is_in_kev(cve_id: str, kev_set: Optional[Set[str]] = None) -> bool:
    """Check if CVE is in KEV."""
    if kev_set is None:
        kev_set = load_kev()
    return cve_id.upper() in kev_set


if __name__ == "__main__":
    kev = load_kev()
    print(f"KEV list: {len(kev)} CVEs")
    print(f"CVE-2021-44228 in KEV: {is_in_kev('CVE-2021-44228', kev)}")