# Cerebras Red Team Simulator

Autonomous AI-powered penetration testing that exploits vulnerabilities in seconds, then analyzes WHY the attack worked.

## What This Does

1. **Red Team Attack** — AI autonomously hacks a target system using multi-step reasoning
2. **Security Genome Analysis** — Extracts vulnerability PATTERNS, not just instances
3. **Blue Team Replay** — Shows where defenders could have stopped the attack (coming soon)
4. **Attack Graph** — Maps ALL possible attack paths (coming soon)

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Cerebras API Key
```bash
# Windows
set CEREBRAS_API_KEY=your-key-here

# Mac/Linux
export CEREBRAS_API_KEY=your-key-here
```

### 3. Start the Vulnerable Target
```bash
cd vulnerable_app
python app.py
```

Keep this running in a separate terminal.

### 4. Run the Attack
```bash
python main.py --target http://127.0.0.1:5000
```

## Project Structure
```
cybcer/
├── main.py                 # CLI entry point
├── orchestrator.py         # ReAct loop + Cerebras integration
├── tools.py                # Attack tool implementations
├── prompts.py              # LLM prompts
├── output.py               # Terminal output formatting
├── genome_analysis.py      # Security pattern analysis
├── state.py                # Attack state tracking
├── vulnerable_app/
│   ├── app.py              # Flask vulnerable target
│   ├── templates/
│   │   ├── login.html
│   │   └── admin.html
│   └── uploads/
└── requirements.txt
```

## CLI Options
```bash
python main.py --target <URL> [options]

Options:
  --target, -t       Target URL (required)
  --api-key, -k      Cerebras API key (or use env var)
  --max-steps, -s    Max attack steps (default: 20)
  --model, -m        Cerebras model to use
  --skip-genome      Skip genome analysis after attack
```

## Output Format

The tool outputs:
1. **Live attack log** — Each step with timing
2. **Attack summary** — Credentials, footholds, data exfiltrated
3. **Speed comparison** — Cerebras vs GPT-4 timing
4. **Genome analysis** — Root cause, patterns, remediation

## For UI Development

### Key Files to Integrate

**`orchestrator.py`** — The `CerebrasAttacker` class
- `run()` method yields events as the attack progresses
- Each event has a `type`: `think`, `action`, `observation`, `success`, `warning`, `summary`

**Event types:**
```python
{"type": "think", "content": "...", "time": 0.5}
{"type": "action", "tool": "scan_paths", "params": {...}}
{"type": "observation", "content": "...", "time": 0.2}
{"type": "success", "message": "Attack completed"}
{"type": "summary", "total_time": 13.5, "steps": 6, "speedup": 2.1}
```

**`genome_analysis.py`** — The `SecurityGenomeAnalyzer` class
- `analyze()` returns `{"analysis": "...", "analysis_time": 3.2}`

### API Endpoints Needed

For a web UI, wrap these in a Flask/FastAPI backend:
```
POST /attack/start
  body: { target: "http://...", api_key: "..." }
  returns: { attack_id: "..." }

GET /attack/{id}/stream
  returns: Server-Sent Events with attack progress

GET /attack/{id}/result
  returns: { summary: {...}, genome_analysis: {...} }
```

### State Object

After attack completes, `attacker.state` contains:
```python
{
  "target_url": "http://...",
  "discovered_paths": ["/admin", "/backup/config.php.bak"],
  "credentials": [("admin", "admin123")],
  "footholds": ["admin_session", "webshell:/uploads/shell.php"],
  "loot": ["user database with SSNs..."],
  "attack_log": [{"tool": "...", "params": {...}, "result": "..."}]
}
```

## Features In Progress

- [ ] Blue Team Replay — Show detection opportunities
- [ ] Attack Graph — Visualize all possible attack paths
- [ ] Benchmark Harness — Real Cerebras vs GPT-4 comparison
- [ ] JSON Export — Machine-readable findings
- [ ] Sigma Rules — Auto-generate detection signatures

## The Deeper Insight

This isn't just "AI hacks faster."

Traditional security tools find vulnerability INSTANCES. This tool extracts vulnerability PATTERNS — the generative grammar of how security failures are created.

The insight: Security vulnerabilities aren't random bugs. They're expressions of underlying patterns in how systems are built. Cerebras speed enables real-time pattern analysis that was previously impossible.

## Demo

Attack completes in ~15 seconds:
- Scans target
- Finds exposed config with credentials
- Logs in as admin
- Uploads webshell
- Exfiltrates user database
- Analyzes WHY the attack worked

## Team

Built for Cerebras "Need for Speed" Challenge.