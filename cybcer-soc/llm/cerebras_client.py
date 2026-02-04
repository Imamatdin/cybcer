#!/usr/bin/env python3
"""
Cerebras LLM client for incident brief generation.
OpenAI-compatible API wrapper with timeouts and parallel support.
"""

import os
import json
import time
from typing import Optional, Dict
from dotenv import load_dotenv
from openai import OpenAI
import httpx

load_dotenv()

# Client setup with explicit timeouts
CEREBRAS_TIMEOUT = 30.0  # seconds
GEMINI_TIMEOUT = 12.0    # seconds - stricter for baseline

cerebras_client = OpenAI(
    base_url="https://api.cerebras.ai/v1",
    api_key=os.getenv("CEREBRAS_API_KEY"),
    timeout=httpx.Timeout(CEREBRAS_TIMEOUT, connect=5.0)
)

gemini_client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GEMINI_API_KEY"),
    timeout=httpx.Timeout(GEMINI_TIMEOUT, connect=5.0)
)

CEREBRAS_MODEL = "zai-glm-4.7"
GEMINI_MODEL = "gemini-2.0-flash"

# Token limits - SPEED FIRST
CEREBRAS_MAX_TOKENS = 1500  # Reduced for speed
GEMINI_MAX_TOKENS = 800     # Even smaller for baseline comparison


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
                            provider: str = "cerebras", max_retries: int = 3) -> dict:
    """Generate incident brief using LLM.

    SPEED-OPTIMIZED:
    - Hard timeouts per provider
    - Reduced max_tokens
    - Single retry (no sleep)
    - Returns detailed error info for UI
    """

    is_cerebras = provider == "cerebras"
    client = cerebras_client if is_cerebras else gemini_client
    model = CEREBRAS_MODEL if is_cerebras else GEMINI_MODEL
    max_tokens = CEREBRAS_MAX_TOKENS if is_cerebras else GEMINI_MAX_TOKENS

    # Truncate case data more aggressively for speed
    prompt = INCIDENT_BRIEF_PROMPT.format(
        case_data=json.dumps(case_data, indent=2)[:4000],  # Reduced from 6000
        cve_intel=json.dumps(cve_intel[:3], indent=2),     # Top 3 only
        patch_plan=json.dumps(patch_plan[:3], indent=2),   # Top 3 only
        case_id=case_data.get("case_id", "CASE-001"),
        patch_plan_json=json.dumps(patch_plan[:3])
    )

    # Track timing
    call_start = time.time()

    for attempt in range(max_retries + 1):
        try:
            start = time.time()

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.2
            )

            elapsed = time.time() - start
            content = response.choices[0].message.content

            if not content:
                raise ValueError("Model returned empty content")

            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            brief = json.loads(content.strip())

            usage = response.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0
            # zai-glm-4.7 doesn't populate completion_tokens — estimate from output
            if tokens_out == 0:
                tokens_out = max(1, len(content) // 4)

            return {
                "brief": brief,
                "provider": provider,
                "model": model,
                "generation_time_sec": round(elapsed, 3),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "tokens_per_sec": round(tokens_out / elapsed, 1) if elapsed > 0 else 0,
                "ok": True,
                "error": None
            }

        except json.JSONDecodeError as e:
            if attempt < max_retries:
                print(f"[{provider}] JSON parse failed, retrying... ({e})")
                continue
            return {
                "error": f"JSON parse failed: {e}",
                "provider": provider,
                "model": model,
                "ok": False,
                "generation_time_sec": round(time.time() - call_start, 3),
                "error_type": "json_parse"
            }

        except httpx.TimeoutException as e:
            if attempt < max_retries:
                print(f"[{provider}] Timeout after {CEREBRAS_TIMEOUT if is_cerebras else GEMINI_TIMEOUT}s, retrying...")
                continue
            return {
                "error": f"Timeout after {CEREBRAS_TIMEOUT if is_cerebras else GEMINI_TIMEOUT}s (all retries exhausted)",
                "provider": provider,
                "model": model,
                "ok": False,
                "generation_time_sec": round(time.time() - call_start, 3),
                "error_type": "timeout"
            }

        except Exception as e:
            error_msg = str(e)
            # Auth errors are permanent — bail immediately
            if "401" in error_msg or "403" in error_msg:
                return {
                    "error": error_msg,
                    "provider": provider,
                    "model": model,
                    "ok": False,
                    "generation_time_sec": round(time.time() - call_start, 3),
                    "error_type": "auth"
                }

            if attempt < max_retries:
                # Rate-limit: back off before retrying
                if "too_many_requests" in error_msg.lower() or "quota" in error_msg.lower() or "429" in error_msg:
                    print(f"[{provider}] Rate-limited, waiting 3s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(3)
                else:
                    print(f"[{provider}] LLM call failed, retrying... ({e})")
                continue
            return {
                "error": error_msg,
                "provider": provider,
                "model": model,
                "ok": False,
                "generation_time_sec": round(time.time() - call_start, 3),
                "error_type": "unknown"
            }

    return {
        "error": "Max retries exceeded",
        "provider": provider,
        "model": model,
        "ok": False,
        "generation_time_sec": round(time.time() - call_start, 3),
        "error_type": "max_retries"
    }


def generate_incident_brief_parallel(case_data: dict, cve_intel: list, patch_plan: list) -> dict:
    """Generate incident briefs from both Cerebras and Gemini IN PARALLEL.

    Returns a dict with both results and speedup calculation.
    This is the CORRECT way to compare - not sequential calls.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {
        "cerebras": None,
        "gemini": None,
        "speedup": None,
        "both_ok": False
    }

    def call_cerebras():
        return generate_incident_brief(case_data, cve_intel, patch_plan, provider="cerebras")

    def call_gemini():
        return generate_incident_brief(case_data, cve_intel, patch_plan, provider="gemini")

    parallel_start = time.time()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(call_cerebras): "cerebras",
            executor.submit(call_gemini): "gemini"
        }

        for future in as_completed(futures):
            provider = futures[future]
            try:
                results[provider] = future.result()
            except Exception as e:
                results[provider] = {
                    "error": str(e),
                    "provider": provider,
                    "ok": False,
                    "error_type": "executor_error"
                }

    results["parallel_time_sec"] = round(time.time() - parallel_start, 3)

    # Calculate speedup only if both succeeded
    cerebras_ok = results["cerebras"] and results["cerebras"].get("ok")
    gemini_ok = results["gemini"] and results["gemini"].get("ok")

    if cerebras_ok and gemini_ok:
        cerebras_time = results["cerebras"].get("generation_time_sec", 0)
        gemini_time = results["gemini"].get("generation_time_sec", 0)
        if cerebras_time > 0:
            results["speedup"] = round(gemini_time / cerebras_time, 2)
        results["both_ok"] = True
    else:
        results["speedup"] = None
        results["both_ok"] = False

    return results


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

    print("Testing parallel comparison...")
    result = generate_incident_brief_parallel(test_case, test_intel, test_plan)
    print(json.dumps({
        "cerebras_ok": result["cerebras"].get("ok") if result["cerebras"] else False,
        "gemini_ok": result["gemini"].get("ok") if result["gemini"] else False,
        "speedup": result["speedup"],
        "parallel_time_sec": result["parallel_time_sec"]
    }, indent=2))
