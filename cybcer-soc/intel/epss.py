#!/usr/bin/env python3
"""
FIRST EPSS (Exploit Prediction Scoring System) loader with cache.
"""

import json
from pathlib import Path
from typing import Dict, Optional
import urllib.request

EPSS_API = "https://api.first.org/data/v1/epss?cve="
CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "epss.json"


def fetch_epss_online(cve_id: str) -> dict:
    """Fetch EPSS for single CVE."""
    url = EPSS_API + cve_id.upper()
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    if data.get("data"):
        return data["data"][0]
    return {}


def load_epss_cache() -> Dict[str, dict]:
    """Load EPSS cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_epss_cache(cache: Dict[str, dict]):
    """Save EPSS cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_epss(cve_id: str, cache: Optional[Dict] = None, update_cache: bool = True) -> dict:
    """Get EPSS for CVE. Cache-first."""
    cve_id = cve_id.upper()
    
    if cache is None:
        cache = load_epss_cache()
    
    if cve_id in cache:
        return cache[cve_id]
    
    # Fetch online
    try:
        data = fetch_epss_online(cve_id)
        if data and update_cache:
            cache[cve_id] = data
            save_epss_cache(cache)
        return data
    except Exception as e:
        print(f"[!] EPSS fetch failed for {cve_id}: {e}")
        return {}


def get_epss_score(cve_id: str, cache: Optional[Dict] = None) -> Optional[float]:
    """Get just the EPSS score (0-1)."""
    data = get_epss(cve_id, cache)
    if data and "epss" in data:
        return float(data["epss"])
    return None


def get_epss_percentile(cve_id: str, cache: Optional[Dict] = None) -> Optional[float]:
    """Get EPSS percentile (0-1)."""
    data = get_epss(cve_id, cache)
    if data and "percentile" in data:
        return float(data["percentile"])
    return None


if __name__ == "__main__":
    # Test with Log4Shell
    cve = "CVE-2021-44228"
    data = get_epss(cve)
    print(f"{cve}: {json.dumps(data, indent=2)}")