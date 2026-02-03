import requests
import time
from typing import Any


class SecurityGenomeAnalyzer:
    def __init__(self, api_key: str, model: str = "llama-4-scout-17b-16e-instruct"):
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
        
        analysis_prompt = f"""You are a security research analyst. An autonomous red team AI just completed an attack. Analyze the attack chain and extract deeper insights.

ATTACK CHAIN:
{attack_chain}

EXFILTRATED DATA:
- Credentials: {state.credentials}
- Footholds: {state.footholds}
- Loot items: {len(state.loot)}

Provide a SECURITY GENOME ANALYSIS with these exact sections:

## ROOT CAUSE ANALYSIS
What fundamental security failure enabled this attack? Go deeper than "config file was exposed" - why was it there? What process failed?

## VULNERABILITY PATTERN
This specific vulnerability is an instance of what broader pattern? Name the pattern and explain how it manifests across different systems.

## ATTACK CHAIN DEPENDENCIES  
Which steps depended on which? Draw the dependency graph in text. Which single fix would have broken the most steps?

## DETECTION OPPORTUNITIES
At each step, what security control could have detected or blocked the attack? Be specific (name tools, rules, techniques).

## SIMILAR PATTERNS TO SCAN FOR
What other files, paths, or configurations would exhibit the same vulnerability pattern? Give specific examples to grep/scan for.

## REMEDIATION PRIORITY
Rank fixes by impact. What one change prevents the entire attack class, not just this instance?

## GENERATIVE INSIGHT
What does this attack reveal about how vulnerabilities are CREATED (not just found)? What development practice or architecture decision generates this class of vulnerability?

Be specific, technical, and actionable. No generic advice."""

        genome_result = self._call_cerebras(analysis_prompt)
        
        analysis_time = time.time() - start_time
        
        return {
            "analysis": genome_result,
            "analysis_time": analysis_time
        }
    
    def _format_attack_chain(self, attack_log: list) -> str:
        chain = []
        for i, entry in enumerate(attack_log, 1):
            tool = entry.get("tool", "unknown")
            params = entry.get("params", {})
            result = entry.get("result", "")[:200]
            chain.append(f"Step {i}: {tool}\n  Params: {params}\n  Result: {result}...")
        return "\n\n".join(chain)


def print_genome_analysis(result: dict):
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    
    console = Console()
    
    console.print()
    console.print(Panel(
        "[bold cyan]SECURITY GENOME ANALYSIS[/bold cyan]\n"
        f"[dim]Analysis completed in {result['analysis_time']:.1f}s[/dim]",
        border_style="cyan"
    ))
    console.print()
    console.print(Markdown(result["analysis"]))
    console.print()