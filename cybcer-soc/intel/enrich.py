#!/usr/bin/env python3
"""
CVE Enrichment: combines KEV + EPSS + optional NVD metadata.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Set

sys.path.insert(0, str(Path(__file__).parent.parent))
from intel.kev import load_kev
from intel.epss import get_epss, load_epss_cache, save_epss_cache


def enrich_cve(cve_id: str, kev_set: Optional[Set[str]] = None, 
               epss_cache: Optional[Dict] = None) -> dict:
    """Enrich a single CVE with KEV + EPSS."""
    cve_id = cve_id.upper()
    
    if kev_set is None:
        kev_set = load_kev()
    if epss_cache is None:
        epss_cache = load_epss_cache()
    
    epss_data = get_epss(cve_id, epss_cache)
    
    return {
        "cve": cve_id,
        "in_kev": cve_id in kev_set,
        "epss_score": float(epss_data.get("epss", 0)) if epss_data else None,
        "epss_percentile": float(epss_data.get("percentile", 0)) if epss_data else None,
    }


def enrich_cve_list(cve_ids: List[str], output_path: Optional[str] = None) -> List[dict]:
    """Enrich multiple CVEs and optionally save to file."""
    kev_set = load_kev()
    epss_cache = load_epss_cache()
    
    results = []
    for cve_id in cve_ids:
        enriched = enrich_cve(cve_id, kev_set, epss_cache)
        results.append(enriched)
        print(f"  {cve_id}: KEV={enriched['in_kev']}, EPSS={enriched['epss_score']}")
    
    # Save EPSS cache
    save_epss_cache(epss_cache)
    
    if output_path:
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
    
    return results


if __name__ == "__main__":
    # Test with common CVEs
    test_cves = ["CVE-2021-44228", "CVE-2021-45046", "CVE-2023-44487"]
    print("Enriching CVEs:")
    results = enrich_cve_list(test_cves)
    print(json.dumps(results, indent=2))