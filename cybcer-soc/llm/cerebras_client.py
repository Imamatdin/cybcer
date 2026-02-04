#!/usr/bin/env python3
"""
Cerebras LLM client for incident brief generation.
OpenAI-compatible API wrapper with retries.
"""

import os
import json
import time
from typing import Optional, Dict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Client setup
cerebras_client = OpenAI(
    base_url="https://api.cerebras.ai/v1",
    api_key=os.getenv("CEREBRAS_API_KEY")
)

gemini_client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GEMINI_API_KEY")
)

CEREBRAS_MODEL = "zai-glm-4.7"
GEMINI_MODEL = "gemini-2.5-flash"


INCIDENT_BRIEF_PROMPT = """You are a SOC analyst. Analyze this case data and produce a structured incident brief.

CASE DATA:
{case_data}

CVE INTEL (if relevant):
{cve_intel}

PATCH PLAN (pre-computed):
{patch_plan}

OUTPUT STRICT JSON (no markdown, no explanation):
{{
  "case_id": "{case_id}",
  "summary": "one sentence incident summary",
  "confidence": 0.0-1.0,
  "timeline": [
    {{"ts": "ISO8601", "event": "description", "evidence_id": "E0001"}}
  ],
  "key_entities": {{
    "hosts": ["list"],
    "users": ["list"],
    "ips": ["list"]
  }},
  "evidence": [
    {{"id": "E0001", "excerpt": "text", "reason": "why important"}}
  ],
  "attack_mapping": [
    {{"framework": "MITRE ATT&CK", "technique": "T1190 - Exploit Public-Facing Application", "rationale": "why"}}
  ],
  "containment_steps": [
    {{"action": "what to do", "why": "reason", "risk": "low|med|high"}}
  ],
  "remediation_steps": [
    {{"action": "what to do", "why": "reason", "owner": "secops|devops|app"}}
  ],
  "log4shell_patch_plan": {patch_plan_json}
}}

Generate the incident brief JSON:"""


def generate_incident_brief(case_data: dict, cve_intel: list, patch_plan: list,
                            provider: str = "cerebras", max_retries: int = 2) -> dict:
    """Generate incident brief using LLM."""
    
    client = cerebras_client if provider == "cerebras" else gemini_client
    model = CEREBRAS_MODEL if provider == "cerebras" else GEMINI_MODEL
    
    prompt = INCIDENT_BRIEF_PROMPT.format(
        case_data=json.dumps(case_data, indent=2)[:6000],
        cve_intel=json.dumps(cve_intel, indent=2),
        patch_plan=json.dumps(patch_plan[:5], indent=2),  # Top 5
        case_id=case_data.get("case_id", "CASE-001"),
        patch_plan_json=json.dumps(patch_plan[:5])
    )
    
    for attempt in range(max_retries + 1):
        try:
            start = time.time()
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=7000,
                temperature=0.2
            )
            
            elapsed = time.time() - start
            content = response.choices[0].message.content
            
            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            brief = json.loads(content.strip())
            
            usage = response.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0
            
            return {
                "brief": brief,
                "provider": provider,
                "model": model,
                "generation_time_sec": round(elapsed, 3),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "tokens_per_sec": round(tokens_out / elapsed, 1) if elapsed > 0 else 0
            }
            
        except json.JSONDecodeError as e:
            if attempt < max_retries:
                print(f"[!] JSON parse failed, retrying... ({e})")
                continue
            return {"error": f"JSON parse failed: {e}", "raw": content}
        
        except Exception as e:
            if attempt < max_retries:
                print(f"[!] LLM call failed, retrying... ({e})")
                time.sleep(1)
                continue
            return {"error": str(e)}
    
    return {"error": "Max retries exceeded"}


if __name__ == "__main__":
    # Test
    test_case = {
        "case_id": "CASE-TEST-001",
        "hosts": ["srv01", "srv02"],
        "users": ["admin"],
        "src_ips": ["1.2.3.4"],
        "timeline": [{"ts": "2024-01-15T10:00:00Z", "event": "Suspicious request", "evidence_id": "E0001"}],
        "evidence": [{"id": "E0001", "excerpt": "jndi:ldap://evil", "reason": "Log4Shell pattern"}]
    }
    
    test_intel = [{"cve": "CVE-2021-44228", "in_kev": True, "epss_score": 0.975}]
    test_plan = [{"priority": 1, "service": "api-gw", "urgency": "immediate"}]
    
    result = generate_incident_brief(test_case, test_intel, test_plan)
    print(json.dumps(result, indent=2))