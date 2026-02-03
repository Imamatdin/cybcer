import json
import time
import requests
from typing import Generator
from dataclasses import dataclass, field
from prompts import SYSTEM_PROMPT, format_react_prompt
from tools import ToolExecutor
from output import AttackLogger

@dataclass
class AttackState:
    target_url: str
    discovered_paths: list = field(default_factory=list)
    credentials: list = field(default_factory=list)
    session_cookies: dict = field(default_factory=dict)
    footholds: list = field(default_factory=list)
    loot: list = field(default_factory=list)
    attack_log: list = field(default_factory=list)
    
    def to_context(self) -> str:
        return f"""
CURRENT ATTACK STATE:
- Target: {self.target_url}
- Discovered paths: {self.discovered_paths}
- Credentials found: {self.credentials}
- Active sessions: {list(self.session_cookies.keys())}
- Footholds: {self.footholds}
- Loot collected: {len(self.loot)} items
"""

class CerebrasAttacker:
    def __init__(self, api_key: str, target_url: str, model: str = "zai-glm-4.7"):
        self.api_key = api_key
        self.target_url = target_url
        self.model = model
        self.state = AttackState(target_url=target_url)
        self.tools = ToolExecutor()
        self.logger = AttackLogger()
        self.conversation_history = []
        self.max_history = 10  # Keep only last 10 messages
        self.start_time = None
        
    def _call_cerebras(self, prompt: str) -> str:
        """Make a single Cerebras API call."""
        self.conversation_history.append({"role": "user", "content": prompt})
    
        # Truncate history to prevent context overflow
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
        response = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                *self.conversation_history
            ],
            "max_tokens": 512,
            "temperature": 0.7
        }
    )
    
        result = response.json()
    
        if "choices" not in result:
            # Handle error gracefully
            if "context_length_exceeded" in str(result):
                # Clear history and retry
                self.conversation_history = self.conversation_history[-4:]
                return self._call_cerebras(prompt)
            raise Exception(f"Unexpected API response: {result}")
    
        assistant_message = result["choices"][0]["message"]["content"]
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
    
        return assistant_message
    
    def _parse_action(self, response: str) -> tuple[str, dict] | None:
        """Extract tool call from LLM response."""
        # Look for ACTION: tool_name(params)
        if "ACTION:" not in response:
            return None
            
        try:
            action_line = response.split("ACTION:")[1].split("\n")[0].strip()
            
            # Parse tool_name(params)
            tool_name = action_line.split("(")[0].strip()
            params_str = action_line.split("(", 1)[1].rsplit(")", 1)[0]
            
            # Parse params as JSON or key=value pairs
            try:
                params = json.loads(params_str)
            except:
                # Try key=value format
                params = {}
                for part in params_str.split(","):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        params[k.strip()] = v.strip().strip('"\'')
                    else:
                        # Single positional arg
                        params["url"] = part.strip().strip('"\'')
            
            return tool_name, params
        except Exception as e:
            self.logger.error(f"Failed to parse action: {e}")
            return None
    
    def _is_goal_achieved(self, response: str) -> bool:
        """Check if the LLM thinks the attack is complete."""
        goal_indicators = [
            "GOAL_ACHIEVED",
            "attack complete",
            "successfully exfiltrated",
            "sensitive data obtained",
            "mission accomplished"
        ]
        return any(indicator.lower() in response.lower() for indicator in goal_indicators)
    
    def _is_stuck(self, response: str) -> bool:
        """Check if the LLM is stuck."""
        stuck_indicators = [
            "STUCK",
            "no further progress",
            "unable to proceed",
            "attack failed"
        ]
        return any(indicator.lower() in response.lower() for indicator in stuck_indicators)
    
    def run(self, max_steps: int = 20) -> Generator[dict, None, None]:
        """Execute the attack loop, yielding status updates."""
        self.start_time = time.time()
        self.logger.start(self.target_url)
        
        # Initial prompt
        prompt = format_react_prompt(
            target=self.target_url,
            state=self.state.to_context(),
            tools=self.tools.get_tool_descriptions(),
            observation="Starting attack. Begin with reconnaissance."
        )
        
        for step in range(max_steps):
            step_start = time.time()
            
            # Get LLM response
            response = self._call_cerebras(prompt)
            
            inference_time = time.time() - step_start
            
            # Log the thinking
            if "THINK:" in response:
                think = response.split("THINK:")[1].split("ACTION:")[0].strip()
                yield self.logger.think(think, inference_time)
            
            # Check for goal achieved
            if self._is_goal_achieved(response):
                yield self.logger.success("Attack completed successfully!")
                yield self.logger.summary(self.state, time.time() - self.start_time)
                return
            
            # Check if stuck
            if self._is_stuck(response):
                yield self.logger.warning("Attack reached dead end")
                yield self.logger.summary(self.state, time.time() - self.start_time)
                return
            
            # Parse and execute action
            action = self._parse_action(response)
            if action:
                tool_name, params = action
                yield self.logger.action(tool_name, params)
                
                # Execute tool
                tool_start = time.time()
                result = self.tools.execute(tool_name, params, self.state)
                tool_time = time.time() - tool_start
                
                yield self.logger.observation(result, tool_time)
                
                # Update state based on result
                self._update_state(tool_name, params, result)
                
                # Prepare next prompt
                prompt = format_react_prompt(
                    target=self.target_url,
                    state=self.state.to_context(),
                    tools=self.tools.get_tool_descriptions(),
                    observation=f"Tool '{tool_name}' returned:\n{result}"
                )
            else:
                yield self.logger.warning("No valid action parsed, retrying...")
                prompt = f"Your response didn't include a valid ACTION. Please respond with THINK: and ACTION: format.\n\nCurrent state:\n{self.state.to_context()}"
        
        yield self.logger.warning(f"Max steps ({max_steps}) reached")
        yield self.logger.summary(self.state, time.time() - self.start_time)
    
    def _update_state(self, tool_name: str, params: dict, result: str):
        """Update attack state based on tool results."""
        self.state.attack_log.append({
            "tool": tool_name,
            "params": params,
            "result": result[:500]  # Truncate for log
        })
        
        # Extract discoveries from results
        if "found" in result.lower() or "discovered" in result.lower():
            if "/backup" in result or "/admin" in result:
                path = result.split()[-1] if "/" in result else ""
                if path and path not in self.state.discovered_paths:
                    self.state.discovered_paths.append(path)
        
        if "password" in result.lower() or "credential" in result.lower():
            # Try to extract creds
            if "admin" in result.lower() and "admin123" in result.lower():
                cred = ("admin", "admin123")
                if cred not in self.state.credentials:
                    self.state.credentials.append(cred)
        
        if "logged in" in result.lower() or "session" in result.lower():
            self.state.footholds.append("admin_session")
        
        if "shell" in result.lower() or "uploaded" in result.lower():
            self.state.footholds.append("webshell")
        
        if "ssn" in result.lower() or "user" in result.lower() and "@" in result:
            self.state.loot.append(result[:200])
