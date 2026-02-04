#!/usr/bin/env python3
"""
BREACH RACE: Can the defender outrun the attacker?

Simulates an active breach. Two defenders (Cerebras vs Gemini) race to
analyze attack steps faster than the attacker can execute them.

The defender that finishes analysis before the attacker completes = 
could have blocked the breach.

This is the core demo for the Cerebras Need for Speed Challenge.
"""

import time
import json
import os
import sys
import requests
from dataclasses import dataclass, field
from typing import List

# Load environment
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val.strip('"').strip("'")

# Try to import rich for nice output, fall back to plain print
try:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    RICH = True
except ImportError:
    RICH = False
    class Console:
        def print(self, *args, **kwargs):
            # Strip rich markup
            text = str(args[0]) if args else ""
            import re
            text = re.sub(r'\[.*?\]', '', text)
            print(text)
    console = Console()
    class Panel:
        @staticmethod
        def fit(text, **kwargs):
            return f"\n{'='*60}\n{text}\n{'='*60}"


# Configuration - UPDATE THESE IF NEEDED
CEREBRAS_MODEL = os.environ.get("CEREBRAS_MODEL", "llama3.1-8b")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


@dataclass
class AttackStep:
    timestamp: float
    action: str
    details: str
    success: bool = True


# Attack sequence - realistic breach pattern
ATTACK_CHAIN = [
    ("recon", "Port scan on target 192.168.1.0/24"),
    ("discover", "Found exposed /backup/config.bak"),
    ("extract", "Credentials found: admin:Passw0rd123"),
    ("access", "SSH login successful as admin"),
    ("escalate", "Privilege escalation via sudo misconfiguration"),
    ("persist", "Backdoor installed at /var/spool/.hidden"),
    ("collect", "Dumping /var/www/db/users.sqlite"),
    ("exfil", "Exfiltrating 15,247,891 user records..."),
]


DEFENSE_PROMPT = """You are a real-time SOC analyst AI. A breach is happening NOW.

Analyze this attack step and respond in JSON:
{{"threat": "LOW|MEDIUM|HIGH|CRITICAL", "next_move": "prediction", "action": "defensive recommendation", "block": true/false}}

Current step: {action} - {details}
Attack history: {history}

JSON only. Be concise."""


def call_cerebras(prompt: str, api_key: str) -> tuple[str, float]:
    """Call Cerebras API, return (response, time)"""
    start = time.time()
    try:
        r = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": CEREBRAS_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
                "temperature": 0.2
            },
            timeout=30
        )
        elapsed = time.time() - start
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"], elapsed
        return f"Error: {r.status_code}", elapsed
    except Exception as e:
        return f"Error: {e}", time.time() - start


def call_gemini(prompt: str, api_key: str) -> tuple[str, float]:
    """Call Gemini API, return (response, time)"""
    start = time.time()
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 150}
            },
            timeout=30
        )
        elapsed = time.time() - start
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"], elapsed
        return f"Error: {r.status_code}", elapsed
    except Exception as e:
        return f"Error: {e}", time.time() - start


def parse_threat_level(response: str) -> str:
    """Extract threat level from response"""
    try:
        # Try to parse as JSON
        data = json.loads(response)
        return data.get("threat", "MEDIUM")
    except:
        # Fallback: look for keywords
        response_upper = response.upper()
        if "CRITICAL" in response_upper:
            return "CRITICAL"
        if "HIGH" in response_upper:
            return "HIGH"
        if "LOW" in response_upper:
            return "LOW"
        return "MEDIUM"


def run_breach_race():
    """Execute the breach race simulation"""
    
    cerebras_key = os.environ.get("CEREBRAS_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not cerebras_key:
        console.print("[red]ERROR: CEREBRAS_API_KEY not set[/red]")
        console.print("Add to .env file: CEREBRAS_API_KEY=your-key")
        return None
    
    if not gemini_key:
        console.print("[red]ERROR: GEMINI_API_KEY not set[/red]")
        console.print("Add to .env file: GEMINI_API_KEY=your-key")
        console.print("Get key at: https://aistudio.google.com/apikey")
        return None
    
    # Print header
    print()
    print("=" * 70)
    print("🚨  BREACH RACE: CEREBRAS vs GEMINI  🚨")
    print("=" * 70)
    print()
    print(f"  Cerebras model: {CEREBRAS_MODEL}")
    print(f"  Gemini model:   {GEMINI_MODEL}")
    print()
    print("  Question: Can the defender analyze faster than the attacker attacks?")
    print()
    print("-" * 70)
    
    # Track times
    cerebras_times = []
    gemini_times = []
    attack_steps = []
    history = []
    
    attack_start = time.time()
    
    for i, (action, details) in enumerate(ATTACK_CHAIN):
        step_num = i + 1
        
        # Simulate attack step delay (attacker isn't instant)
        time.sleep(0.2)
        
        step_time = time.time() - attack_start
        attack_steps.append(AttackStep(step_time, action, details))
        
        print(f"\n[STEP {step_num}/8] ATTACKER @ {step_time:.1f}s")
        print(f"  Action: {action}")
        print(f"  Detail: {details}")
        
        # Build prompt
        history_str = " → ".join(history[-3:]) if history else "None"
        prompt = DEFENSE_PROMPT.format(action=action, details=details, history=history_str)
        history.append(action)
        
        # Race: Cerebras vs Gemini
        print()
        
        # Cerebras
        sys.stdout.write(f"  CEREBRAS: analyzing... ")
        sys.stdout.flush()
        cer_response, cer_time = call_cerebras(prompt, cerebras_key)
        cer_threat = parse_threat_level(cer_response)
        cerebras_times.append(cer_time)
        print(f"{cer_time:.2f}s [{cer_threat}]")
        
        # Gemini
        sys.stdout.write(f"  GEMINI:   analyzing... ")
        sys.stdout.flush()
        gem_response, gem_time = call_gemini(prompt, gemini_key)
        gem_threat = parse_threat_level(gem_response)
        gemini_times.append(gem_time)
        print(f"{gem_time:.2f}s [{gem_threat}]")
        
        # Show speed difference for this step
        if cer_time < gem_time:
            speedup = gem_time / cer_time
            print(f"  → Cerebras {speedup:.1f}x faster on this step")
    
    # Calculate results
    total_attack_time = attack_steps[-1].timestamp
    total_cerebras = sum(cerebras_times)
    total_gemini = sum(gemini_times)
    speedup = total_gemini / total_cerebras if total_cerebras > 0 else 0
    
    # Print results
    print()
    print("=" * 70)
    print("📊  RACE RESULTS")
    print("=" * 70)
    print()
    print(f"  Attack completed in:      {total_attack_time:.1f}s")
    print(f"  Steps analyzed:           {len(ATTACK_CHAIN)}")
    print()
    print(f"  CEREBRAS total analysis:  {total_cerebras:.2f}s")
    print(f"  GEMINI total analysis:    {total_gemini:.2f}s")
    print()
    print(f"  ⚡ CEREBRAS SPEEDUP:       {speedup:.1f}x faster")
    print()
    
    # Determine if defense could have worked
    cerebras_avg = total_cerebras / len(ATTACK_CHAIN)
    gemini_avg = total_gemini / len(ATTACK_CHAIN)
    attack_avg = total_attack_time / len(ATTACK_CHAIN)
    
    print("-" * 70)
    print("🎯  BREACH PREVENTION ANALYSIS")
    print("-" * 70)
    print()
    print(f"  Average time per attack step:    {attack_avg:.2f}s")
    print(f"  Cerebras avg analysis time:      {cerebras_avg:.2f}s")
    print(f"  Gemini avg analysis time:        {gemini_avg:.2f}s")
    print()
    
    if cerebras_avg < attack_avg:
        print("  ✅ CEREBRAS can analyze faster than attacker moves")
        print("     → Could detect and block mid-attack")
    else:
        print("  ⚠️  CEREBRAS slightly behind attacker pace")
        print("     → Still much faster than Gemini for batch processing")
    
    if gemini_avg > attack_avg:
        print()
        print("  ❌ GEMINI cannot keep up with attack speed")
        print("     → By the time analysis completes, data is already gone")
    
    # The money shot
    time_saved = total_gemini - total_cerebras
    print()
    print("=" * 70)
    print("💡  THE BOTTOM LINE")
    print("=" * 70)
    print()
    print(f"  In a real breach, Cerebras gives defenders")
    print(f"  {time_saved:.1f} extra seconds to respond.")
    print()
    print("  That's the difference between:")
    print("    • Blocking the attacker at step 4")
    print("    • Reading about 15 million leaked records in the news")
    print()
    print("  The Uzbekistan government breach happened yesterday.")
    print("  15 million people. Gone.")
    print("  Defenders were too slow.")
    print()
    print("=" * 70)
    
    return {
        "cerebras_total": total_cerebras,
        "gemini_total": total_gemini,
        "speedup": speedup,
        "attack_time": total_attack_time,
        "steps": len(ATTACK_CHAIN),
        "time_saved": time_saved
    }


if __name__ == "__main__":
    results = run_breach_race()
    
    if results:
        # Save results for later use
        with open("race_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\n[Results saved to race_results.json]")