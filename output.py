import time
from dataclasses import dataclass
from typing import Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

console = Console()

class AttackLogger:
    def __init__(self):
        self.step_count = 0
        self.start_time = None
    
    def start(self, target: str):
        self.start_time = time.time()
        console.print()
        console.print(Panel.fit(
            f"[bold red]🎯 CEREBRAS RED TEAM SIMULATOR[/bold red]\n"
            f"[dim]Target: {target}[/dim]",
            border_style="red"
        ))
        console.print()
    
    def _elapsed(self) -> str:
        if self.start_time:
            return f"{time.time() - self.start_time:.1f}s"
        return "0.0s"
    
    def think(self, thought: str, inference_time: float) -> dict:
        self.step_count += 1
        console.print(f"[dim][{self._elapsed()}][/dim] [bold cyan]🧠 THINK:[/bold cyan] {thought[:200]}{'...' if len(thought) > 200 else ''}")
        console.print(f"[dim]   └─ Inference: {inference_time*1000:.0f}ms[/dim]")
        return {"type": "think", "content": thought, "time": inference_time}
    
    def action(self, tool: str, params: dict) -> dict:
        params_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in params.items())
        console.print(f"[dim][{self._elapsed()}][/dim] [bold yellow]⚡ ACTION:[/bold yellow] {tool}({params_str})")
        return {"type": "action", "tool": tool, "params": params}
    
    def observation(self, result: str, tool_time: float) -> dict:
        # Truncate long results for display
        display_result = result[:300] + "..." if len(result) > 300 else result
        
        # Color based on content
        if "SUCCESS" in result or "FOUND" in result.upper():
            style = "bold green"
            icon = "✅"
        elif "FAIL" in result.upper() or "ERROR" in result.upper():
            style = "bold red"
            icon = "❌"
        else:
            style = "white"
            icon = "📋"
        
        console.print(f"[dim][{self._elapsed()}][/dim] [{style}]{icon} OBSERVE:[/{style}] {display_result}")
        console.print(f"[dim]   └─ Execution: {tool_time*1000:.0f}ms[/dim]")
        console.print()
        return {"type": "observation", "content": result, "time": tool_time}
    
    def success(self, message: str) -> dict:
        console.print()
        console.print(Panel(
            f"[bold green]🏆 {message}[/bold green]",
            border_style="green",
            box=box.DOUBLE
        ))
        return {"type": "success", "message": message}
    
    def warning(self, message: str) -> dict:
        console.print(f"[dim][{self._elapsed()}][/dim] [bold yellow]⚠️  {message}[/bold yellow]")
        return {"type": "warning", "message": message}
    
    def error(self, message: str) -> dict:
        console.print(f"[dim][{self._elapsed()}][/dim] [bold red]❌ ERROR: {message}[/bold red]")
        return {"type": "error", "message": message}
    
    def summary(self, state: Any, total_time: float) -> dict:
        console.print()
        
        table = Table(title="Attack Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Time", f"{total_time:.2f} seconds")
        table.add_row("Steps Taken", str(self.step_count))
        table.add_row("Paths Discovered", str(len(state.discovered_paths)))
        table.add_row("Credentials Found", str(len(state.credentials)))
        table.add_row("Footholds Gained", str(len(state.footholds)))
        table.add_row("Data Exfiltrated", f"{len(state.loot)} items")
        
        console.print(table)
        
        if state.credentials:
            console.print("\n[bold]Credentials Found:[/bold]")
            for cred in state.credentials:
                console.print(f"  • {cred[0]}:{cred[1]}")
        
        if state.loot:
            console.print("\n[bold]Sensitive Data Exfiltrated:[/bold]")
            for item in state.loot[:3]:
                console.print(f"  • {item[:100]}...")
        
        # Comparison with GPT-4 estimate
        gpt4_estimate = self.step_count * 3  # ~3 sec per step
        speedup = gpt4_estimate / total_time if total_time > 0 else 0
        
        console.print()
        console.print(Panel(
            f"[bold]⚡ SPEED COMPARISON[/bold]\n\n"
            f"Cerebras:  [green]{total_time:.1f} seconds[/green]\n"
            f"GPT-4 est: [red]~{gpt4_estimate} seconds[/red]\n"
            f"Speedup:   [cyan]{speedup:.1f}x faster[/cyan]",
            border_style="cyan"
        ))
        
        return {
            "type": "summary",
            "total_time": total_time,
            "steps": self.step_count,
            "speedup": speedup
        }
