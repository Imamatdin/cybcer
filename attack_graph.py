import requests
import time
from typing import Any


class AttackGraphGenerator:
    def __init__(self, api_key: str, model: str = "zai-glm-4.7"):
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
                "temperature": 0.4
            }
        )
        return response.json()["choices"][0]["message"]["content"]
    
    def generate(self, attack_log: list, state: Any) -> dict:
        start_time = time.time()
        
        attack_chain = self._format_attack_chain(attack_log)
        
        prompt = f"""You are a security architect analyzing an attack. Generate an ATTACK GRAPH showing ALL possible attack paths, not just the one taken.

ATTACK THAT SUCCEEDED:
{attack_chain}

DISCOVERED ASSETS:
- Paths found: {state.discovered_paths}
- Credentials: {state.credentials}
- Footholds: {state.footholds}

Generate a comprehensive attack graph:

## ATTACK GRAPH

### Primary Path (What Happened)
Show the actual attack path as a text diagram:
```
[Entry] -> [Step1] -> [Step2] -> ... -> [Goal]
```

### Alternative Attack Paths
What OTHER paths could an attacker have taken? For each:
- Path name
- Steps involved
- Likelihood (High/Medium/Low)
- Why it might succeed

### Attack Tree (Text Format)
```
[GOAL: Data Exfiltration]
├── Path A: Config Leak -> Cred Reuse -> Admin -> Shell -> Data
│   ├── Requires: Exposed backup
│   └── Blocked by: Removing backup files
├── Path B: [Alternative path]
│   ├── Requires: [What's needed]
│   └── Blocked by: [What stops it]
└── Path C: [Another alternative]
    ├── Requires: [What's needed]
    └── Blocked by: [What stops it]
```

### Chokepoints
Which nodes in the graph, if secured, would block the MOST paths?
Rank by impact.

### Path Probability Matrix
| Path | Likelihood | Impact | Risk Score |
|------|------------|--------|------------|
| A    | High       | Critical | 9/10     |
| B    | Medium     | High   | 6/10       |

### Defensive Priority
Based on the graph, what should defenders fix FIRST to eliminate the most attack paths?

Be specific and show the graph structure clearly."""

        result = self._call_cerebras(prompt)
        analysis_time = time.time() - start_time
        
        return {
            "graph": result,
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


def print_attack_graph(result: dict):
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    
    console = Console()
    
    console.print()
    console.print(Panel(
        "[bold yellow]ATTACK GRAPH ANALYSIS[/bold yellow]\n"
        f"[dim]Generated in {result['analysis_time']:.1f}s[/dim]",
        border_style="yellow"
    ))
    console.print()
    console.print(Markdown(result["graph"]))
    console.print()
