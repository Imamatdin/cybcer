from flask import Flask, request, render_template, redirect, session, send_from_directory
import os
import json
import time
from datetime import datetime, timezone
from collections import deque

app = Flask(__name__)
app.secret_key = 'terrible-secret-key-12345'

# Hardcoded creds (vuln #1: weak credentials)
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# Fake user database
USERS_DB = [
    {"id": 1, "username": "admin", "email": "admin@company.local", "role": "admin", "ssn": "123-45-6789"},
    {"id": 2, "username": "john.doe", "email": "john@company.local", "role": "user", "ssn": "234-56-7890"},
    {"id": 3, "username": "jane.smith", "email": "jane@company.local", "role": "user", "ssn": "345-67-8901"},
    {"id": 4, "username": "bob.wilson", "email": "bob@company.local", "role": "user", "ssn": "456-78-9012"},
]

# ── Telemetry ──────────────────────────────────────────────────────────
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
_admin_hits = deque(maxlen=50)  # recent timestamps for burst detection


def _emit_event(event_type, severity, message, src_ip="0.0.0.0", dst_ip="10.0.1.20"):
    """Append one SOC-canonical event to logs/events.jsonl."""
    os.makedirs(_LOG_DIR, exist_ok=True)
    ev = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "event_type": event_type,
        "host": "web-srv-01",
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "severity": severity,
        "message": message,
        "fields": {},
    }
    with open(os.path.join(_LOG_DIR, "events.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(ev) + "\n")


@app.after_request
def _telemetry_hook(response):
    """Emit SOC events based on every inbound request."""
    src = request.remote_addr or "0.0.0.0"
    path = request.path
    method = request.method
    status = response.status_code
    now = time.time()

    # --- base web event (every request) ---
    sev = "high" if status >= 400 else "low"
    _emit_event("web", sev, f"{method} {path} status={status}", src_ip=src)

    # --- route-specific synthetic events ---
    if path == "/login" and method == "POST":
        if status == 302:                          # redirect → success
            _emit_event("auth", "medium", f"auth success user=admin src={src}", src_ip=src)
        else:                                      # 200 with error rendered → failure
            _emit_event("auth", "high", f"auth fail src={src}", src_ip=src)

    elif path.startswith("/backup/"):
        _emit_event("file", "high",
                    f"sensitive file_read path={path} src={src}", src_ip=src)

    elif path == "/admin/upload" and method == "POST" and status == 200:
        _emit_event("process", "high",
                    f"file upload detected src={src}", src_ip=src)

    elif path.startswith("/uploads/") and ".php" in path and request.args.get("cmd"):
        cmd = request.args.get("cmd", "")
        _emit_event("process", "critical",
                    f"process_start cmd={cmd} src={src}", src_ip=src)
        _emit_event("edr", "critical",
                    "child process anomaly: shell cmd execution detected", src_ip=src)
        if any(kw in cmd.lower() for kw in ("users", "data", "db", "dump", "passwd")):
            _emit_event("alert", "critical",
                        f"exfil suspected: bytes_out=150000 dst={src}", src_ip=src)

    elif path == "/admin":
        _admin_hits.append(now)
        burst = sum(1 for t in _admin_hits if now - t < 5)
        if burst > 3:
            _emit_event("alert", "high",
                        f"admin access burst ({burst} hits/5s) src={src}", src_ip=src)

    return response


@app.route("/telemetry")
def telemetry():
    """Return last N events as JSON array. Used by SOC runner for live ingest."""
    n = int(request.args.get("n", 100))
    log_path = os.path.join(_LOG_DIR, "events.jsonl")
    events = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return json.dumps(events[-n:]), 200, {"Content-Type": "application/json"}
# ── End telemetry ──────────────────────────────────────────────────────


@app.route('/')
def index():
    return '''
    <h1>ACME Corp Internal Portal</h1>
    <p>Welcome to the internal employee portal.</p>
    <a href="/login">Employee Login</a>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            session['user'] = username
            return redirect('/admin')
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('admin.html', users=USERS_DB)

# Vuln #2: Exposed backup directory
@app.route('/backup/<path:filename>')
def backup(filename):
    return send_from_directory('backup', filename)

# Vuln #3: File upload without validation
@app.route('/admin/upload', methods=['POST'])
def upload():
    if not session.get('logged_in'):
        return "Unauthorized", 401
    file = request.files.get('file')
    if file:
        filepath = os.path.join('uploads', file.filename)
        file.save(filepath)
        return f"File uploaded to /uploads/{file.filename}"
    return "No file provided", 400

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Simulate shell execution for .php files
    if filename.endswith('.php') and request.args.get('cmd'):
        cmd = request.args.get('cmd')
        # Simulated command execution output
        if cmd == 'whoami':
            return "www-data"
        elif cmd == 'cat /etc/passwd':
            return "root:x:0:0:root:/root:/bin/bash\nwww-data:x:33:33:www-data:/var/www:/bin/bash"
        elif 'users' in cmd.lower() or 'data' in cmd.lower() or 'db' in cmd.lower() or 'dump' in cmd.lower():
            return json.dumps(USERS_DB, indent=2)
        elif cmd == 'ls' or cmd == 'ls .' or cmd == 'dir':
            return "users.db\nconfig.php\nindex.php\nuploads/"
        elif cmd == 'ls /' or cmd == 'ls -la /':
            return "bin\netc\nhome\nroot\nvar\nusr\ntmp"
        else:
            return f"Command executed: {cmd}"
    return send_from_directory('uploads', filename)

# Vuln #2 setup: Create exposed backup with credentials
@app.before_request
def setup_vulns():
    os.makedirs('backup', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    
    # Create exposed config file
    config_content = '''<?php
// Database configuration - DO NOT EXPOSE
$db_host = "localhost";
$db_user = "admin";
$db_pass = "admin123";
$db_name = "acme_internal";

// Admin panel credentials (legacy)
$admin_user = "admin";
$admin_pass = "admin123";
?>'''
    
    with open('backup/config.php.bak', 'w') as f:
        f.write(config_content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
