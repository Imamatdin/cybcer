import argparse, json, os, random
from datetime import datetime, timedelta, timezone

SEED = 42

def iso(ts):
    return ts.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

def wchoice(items):
    # items: [(val, weight), ...]
    tot = sum(w for _, w in items)
    r = random.uniform(0, tot)
    acc = 0
    for v, w in items:
        acc += w
        if r <= acc:
            return v
    return items[-1][0]

def baseline_event(ts):
    hosts = ["web-srv-01","web-srv-02","proxy-01","dns-01","dc-01","db-01","filesrv-01","jumpbox-01"]
    internal = [f"10.0.{i}.{j}" for i in range(1,9) for j in (20,21,22,31,44)]
    external = ["93.184.216.34","198.51.100.12","203.0.113.99"]  # test/public examples
    kind = wchoice([("web",45),("auth",15),("dns",15),("proxy",10),("edr",15)])

    host = random.choice(hosts)
    src = random.choice(internal)
    dst = random.choice(internal + external)
    sev = wchoice([("low",80),("med",17),("high",2),("critical",1)])

    if kind == "web":
        path = random.choice(["/","/login","/api/search","/api/users","/health","/admin/login","/api/export"])
        msg = f'GET {path} status={wchoice([("200",85),("401",5),("403",3),("404",5),("500",2)])}'
    elif kind == "auth":
        user = random.choice(["alice","bob","charlie","diana","svc-backend","svc-ci","admin"])
        out = wchoice([("success",92),("fail",8)])
        msg = f'auth {out} user="{user}" method=kerberos'
        sev = "low" if out=="success" else "med"
    elif kind == "dns":
        q = random.choice(["updates.example.com","cdn.example.com","time.example.net","api.example.org"])
        msg = f'dns query qname="{q}" rcode={wchoice([("NOERROR",96),("NXDOMAIN",4)])}'
        host = "dns-01"
        dst = "192.0.2.53"
    elif kind == "proxy":
        dst = random.choice(external)
        msg = f'proxy connect dest="{dst}:443" bytes_out={random.randint(200,50000)}'
        host = "proxy-01"
    else:
        proc = random.choice(["java","nginx","powershell","python","ssh","svchost"])
        act = wchoice([("process_start",55),("file_read",25),("net_connect",20)])
        msg = f'edr {act} proc="{proc}"'
    return {
        "_time": iso(ts),
        "sourcetype": kind,
        "host": host,
        "src_ip": src,
        "dest_ip": dst,
        "message": msg,
        "severity": sev
    }

def attack_chain(start, mode):
    # mode: success | blocked | inconclusive
    # Safe: no payload strings; redacted indicators only
    ext_attacker = "203.0.113.50"
    c2 = "198.51.100.77"
    dns = "192.0.2.53"
    callback = "callback.invalid"
    ldap = "ldap.callback.invalid"

    events = []
    web_host = "web-srv-01"
    web_ip = "10.0.1.20"

    # Stage 1: Web indicator (redacted)
    for i in range(4):
        ts = start + timedelta(seconds=i*2)
        events.append({
            "_time": iso(ts),
            "sourcetype": "web",
            "host": web_host,
            "src_ip": ext_attacker,
            "dest_ip": web_ip,
            "message": 'GET /api/search q="[log4j-indicator:redacted]" status=200',
            "severity": "high"
        })

    # Stage 2: DNS callback
    for i in range(3):
        ts = start + timedelta(seconds=20 + i*2)
        events.append({
            "_time": iso(ts),
            "sourcetype": "dns",
            "host": "dns-01",
            "src_ip": web_ip,
            "dest_ip": dns,
            "message": f'dns query qname="{callback}" rcode=NOERROR note="unusual domain after web indicator"',
            "severity": "high"
        })

    # Stage 3: Outbound LDAP-like egress (blocked path supported)
    if mode in ("success", "blocked"):
        action = "blocked" if mode == "blocked" else "allowed"
        sev = "high" if mode == "blocked" else "critical"
        ts0 = start + timedelta(seconds=35)
        events.append({
            "_time": iso(ts0),
            "sourcetype": "proxy",
            "host": "proxy-01",
            "src_ip": web_ip,
            "dest_ip": c2,
            "message": f'proxy connect dest="{ldap}:389" action={action} note="rare outbound ldap from web tier"',
            "severity": sev
        })

    # If blocked, we stop chain cleanly
    if mode == "blocked":
        ts = start + timedelta(seconds=50)
        events.append({
            "_time": iso(ts),
            "sourcetype": "edr",
            "host": web_host,
            "src_ip": web_ip,
            "dest_ip": web_ip,
            "message": 'edr alert note="egress blocked; monitor for follow-on activity"',
            "severity": "med"
        })
        return events

    # Stage 4: EDR anomalies (process + net)
    for i in range(2):
        ts = start + timedelta(seconds=50 + i*3)
        events.append({
            "_time": iso(ts),
            "sourcetype": "edr",
            "host": web_host,
            "src_ip": web_ip,
            "dest_ip": web_ip,
            "message": 'edr process_start parent="java" child="[redacted]" note="unexpected child from app process"',
            "severity": "critical"
        })
    events.append({
        "_time": iso(start + timedelta(seconds=58)),
        "sourcetype": "edr",
        "host": web_host,
        "src_ip": web_ip,
        "dest_ip": c2,
        "message": f'edr net_connect proc="java" dest="{c2}:443" note="suspicious outbound after indicator"',
        "severity": "critical"
    })

    # Stage 5: file access (redacted)
    events.append({
        "_time": iso(start + timedelta(seconds=65)),
        "sourcetype": "edr",
        "host": web_host,
        "src_ip": web_ip,
        "dest_ip": web_ip,
        "message": 'edr file_read proc="java" path="[sensitive:redacted]" note="unexpected sensitive file access"',
        "severity": "high"
    })

    # If inconclusive, stop here (no exfil/auth movement)
    if mode == "inconclusive":
        events.append({
            "_time": iso(start + timedelta(seconds=75)),
            "sourcetype": "proxy",
            "host": "proxy-01",
            "src_ip": web_ip,
            "dest_ip": c2,
            "message": 'proxy connect dest="198.51.100.77:443" bytes_out=1400 note="low volume; insufficient evidence of exfil"',
            "severity": "med"
        })
        return events

    # Stage 6: exfil spike
    events.append({
        "_time": iso(start + timedelta(seconds=80)),
        "sourcetype": "proxy",
        "host": "proxy-01",
        "src_ip": web_ip,
        "dest_ip": c2,
        "message": f'proxy connect dest="{c2}:443" bytes_out=874512 note="possible exfil spike from web tier"',
        "severity": "critical"
    })

    # Stage 7: auth anomalies / lateral movement indicators
    events.append({
        "_time": iso(start + timedelta(seconds=95)),
        "sourcetype": "auth",
        "host": "dc-01",
        "src_ip": web_ip,
        "dest_ip": "10.0.2.10",
        "message": 'auth fail user="svc-backend" note="service account auth anomaly after web compromise indicators"',
        "severity": "high"
    })
    events.append({
        "_time": iso(start + timedelta(seconds=100)),
        "sourcetype": "auth",
        "host": "jumpbox-01",
        "src_ip": web_ip,
        "dest_ip": "10.0.6.31",
        "message": 'auth success user="svc-backend" note="suspicious success after repeated failures"',
        "severity": "high"
    })

    return events

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output JSONL path, e.g. data/bots/events.json")
    ap.add_argument("--n", type=int, default=1200, help="baseline event count")
    ap.add_argument("--mode", choices=["success","blocked","inconclusive"], default="success")
    args = ap.parse_args()

    random.seed(SEED)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    events = []
    # baseline
    for i in range(args.n):
        ts = start + timedelta(seconds=i*2)
        events.append(baseline_event(ts))

    # inject attack chain in middle
    chain_start = start + timedelta(minutes=8, seconds=10)
    events.extend(attack_chain(chain_start, args.mode))

    # sort by time
    events.sort(key=lambda e: e["_time"])

    with open(args.out, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"Wrote {len(events)} events to {args.out} (mode={args.mode})")

if __name__ == "__main__":
    main()
