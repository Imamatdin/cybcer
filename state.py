"""
Attack State Tracking
Maintains state throughout the red team assessment.
"""
import json
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class AttackState:
    """
    Tracks all information discovered during the attack.
    """
    target: str
    
    # Reconnaissance
    open_ports: List[int] = field(default_factory=list)
    discovered_paths: List[str] = field(default_factory=list)
    forms: List[str] = field(default_factory=list)
    
    # Exploitation
    vulnerabilities: List[str] = field(default_factory=list)
    credentials: List[str] = field(default_factory=list)
    shell_path: str = ""
    
    # Post-exploitation
    command_outputs: List[Dict] = field(default_factory=list)
    files_read: List[str] = field(default_factory=list)
    
    # Action history
    actions: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_action(self, tool: str, input_data: Dict, result: str):
        """Record an action taken."""
        self.actions.append({
            "tool": tool,
            "input": input_data,
            "result": result
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "target": self.target,
            "open_ports": self.open_ports,
            "discovered_paths": self.discovered_paths,
            "forms": self.forms,
            "vulnerabilities": self.vulnerabilities,
            "credentials": self.credentials,
            "shell_path": self.shell_path,
            "actions": self.actions
        }
    
    def save(self, path: str = "state.json"):
        """Save state to file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def summary(self) -> str:
        """Get a text summary of current state."""
        parts = []
        
        if self.open_ports:
            parts.append(f"Open ports: {self.open_ports}")
        if self.discovered_paths:
            parts.append(f"Discovered paths: {self.discovered_paths}")
        if self.vulnerabilities:
            parts.append(f"Vulnerabilities: {self.vulnerabilities}")
        if self.credentials:
            parts.append(f"Credentials: {self.credentials}")
        if self.shell_path:
            parts.append(f"Shell at: {self.shell_path}")
        
        return "\n".join(parts) if parts else "No findings yet"
