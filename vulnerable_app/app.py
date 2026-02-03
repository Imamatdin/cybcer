from flask import Flask, request, render_template, redirect, session, send_from_directory
import os

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
            import json
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