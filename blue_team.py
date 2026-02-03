import requests
import time
from typing import Any


class BlueTeamAnalyzer:
    def __init__(self, api_key: str, model: str = "llama3.1-8b"):
        self.api_key = api_key
        self.model = model
    
    def _call_cerebras(self, prompt: str) -> str:
        response = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.3
            }
        )
        return response.json()["choices"][0]["message"]["content"]
    
    def analyze(self, attack_log: list, state: Any) -> dict:
        start_time = time.time()
        
        attack_chain = self._format_attack_chain(attack_log)
        
        prompt = f"""You are a SOC analyst reviewing an attack that just occurred. Analyze from the DEFENDER's perspective.

ATTACK CHAIN THAT OCCURRED:
{attack_chain}

ATTACKER RESULTS:
- Credentials stolen: {state.credentials}
- Footholds gained: {state.footholds}
- Data exfiltrated: {len(state.loot)} items

For EACH step in the attack, provide:

## BLUE TEAM REPLAY ANALYSIS

For each attack step, analyze:

### Step 1: [Tool used]
- **What happened:** Brief description
- **Alert that SHOULD have fired:** Specific alert name/type
- **Detection rule:** Sigma/YARA rule or log query that would catch this
- **Why it was likely missed:** Common reason this goes undetected
- **Immediate response:** What SOC should do if detected

[Repeat for each step]

## DETECTION COVERAGE SCORE
Rate the organization's detection capability for this attack: X/10
Explain gaps.

## RECOMMENDED SIGMA RULES
Provide 2-3 actual Sigma rule snippets that would detect this attack chain.

## SOC PLAYBOOK
If this attack was detected at Step 2, what's the response playbook?
1. Immediate actions
2. Containment steps
3. Investigation queries
4. Recovery steps

## EARLIEST DETECTION POINT
Which step could have been detected EARLIEST with basic security controls?
What single detection would have prevented the entire breach?

Be specific and actionable. Include actual rule syntax where possible."""

        result = self._call_cerebras(prompt)
        
        analysis_time = time.time() - start_time
        
        return {
            "analysis": result,
            "analysis_time": analysis_time
        }
    
    def _format_attack_chain(self, attack_log: list) -> str:
        chain = []
        for i, entry in enumerate(attack_log, 1):
            tool = entry.get("tool", "unknown")
            params = entry.get("params", {})
            result = entry.get("result", "")[:300]
            chain.append(f"Step {i}: {tool}\n  Params: {params}\n  Result: {result}")
        return "\n\n".join(chain)


def print_blue_team_analysis(result: dict):
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    
    console = Console()
    
    console.print()
    console.print(Panel(
        "[bold blue]BLUE TEAM REPLAY ANALYSIS[/bold blue]\n"
        f"[dim]Analysis completed in {result['analysis_time']:.1f}s[/dim]",
        border_style="blue"
    ))
    console.print()
    console.print(Markdown(result["analysis"]))
    console.print()