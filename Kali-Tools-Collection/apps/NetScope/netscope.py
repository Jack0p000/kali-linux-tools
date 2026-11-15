
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'NetScope'
_ts_register(_TS_NAME)
_ts_publish(_TS_NAME, 'startup', {'pid': __import__('os').getpid()})
# --- ToolAuth integration ---
if '/home/jack0p000/ToolAuth' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolAuth')
from auth import login as _ta_login
_ta_login(_TS_NAME)
# --- end ToolAuth integration ---
# --- end ToolShare integration ---
#!/usr/bin/env python3
import argparse, json, os, re, sqlite3, subprocess, time
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "database", "netscope.sqlite")
os.makedirs(os.path.dirname(DB), exist_ok=True)

def db():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS scans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT, target TEXT, host_count INTEGER, duration REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS hosts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id INTEGER, ip TEXT, mac TEXT, hostname TEXT,
        status TEXT, device TEXT, vendor TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS ports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id INTEGER, host_id INTEGER, port INTEGER,
        protocol TEXT, state TEXT, service TEXT)""")
    cols = [r[1] for r in c.execute("PRAGMA table_info(hosts)")]
    if "device" not in cols:
        c.execute("ALTER TABLE hosts ADD COLUMN device TEXT")
    if "vendor" not in cols:
        c.execute("ALTER TABLE hosts ADD COLUMN vendor TEXT")
    if "device_confidence" not in cols:
        c.execute("ALTER TABLE hosts ADD COLUMN device_confidence TEXT")
    if "device_reason" not in cols:
        c.execute("ALTER TABLE hosts ADD COLUMN device_reason TEXT")
    c.commit()
    return c

def detect_target():
    r = subprocess.run(["ip", "-o", "-4", "addr", "show", "up"],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) >= 4 and p[1] != "lo":
            ip = p[3].split("/")[0].split(".")
            if len(ip) == 4:
                return ".".join(ip[:3]) + ".0/24"

def nmap(target, ports=None):
    # Per la scansione delle porte usiamo -Pn: alcuni dispositivi della LAN
    # non rispondono ai probe ICMP/ARP standard di Nmap, ma hanno comunque porte aperte.
    cmd = ["nmap", "-T3"]
    if ports:
        cmd += ["-Pn", "-sV", "-p", ports]
    else:
        cmd += ["-sn"]
    cmd += [target]
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return r.stdout, r.stderr, r.returncode, time.time() - t

def parse_hosts(out):
    hs, cur = [], None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Nmap scan report for "):
            value = s[len("Nmap scan report for "):]
            m = re.match(r"(.+) \((\d+\.\d+\.\d+\.\d+)\)$", value)
            if m:
                hostname, ip = m.group(1), m.group(2)
            else:
                hostname, ip = None, value
            cur = {"ip": ip, "mac": None, "hostname": hostname,
                   "status": "up", "device": "Sconosciuto",
                   "vendor": None, "ports": []}
            hs.append(cur)
        elif s.startswith("MAC Address:") and cur:
            parts = s.split()
            if len(parts) >= 3:
                cur["mac"] = parts[2]
            if "(" in s and ")" in s:
                cur["vendor"] = s.rsplit("(", 1)[1].rsplit(")", 1)[0]
    return hs

def enrich_netbios(hosts):
    """Cerca nomi NetBIOS sulla LAN. È utile per PC, Mac e alcune stampanti/NAS."""
    try:
        r = subprocess.run(
            ["nbtscan", detect_target() or "192.168.1.0/24"],
            capture_output=True, text=True, timeout=12, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return

    for line in r.stdout.splitlines():
        m = re.match(r"^(\d+\.\d+\.\d+\.\d+)\s+(\S+)", line.strip())
        if not m or m.group(1).endswith(".0") or m.group(2) == "NetBIOS":
            continue
        ip, name = m.group(1), m.group(2)
        for h in hosts:
            if h["ip"] == ip and name not in ("<unknown>", "<server>"):
                h["hostname"] = name
                break

def parse_ports(out):
    result, cur = {}, None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Nmap scan report for "):
            value = s[len("Nmap scan report for "):]
            m = re.match(r".+ \((\d+\.\d+\.\d+\.\d+)\)$", value)
            cur = m.group(1) if m else value
            result[cur] = []
        elif cur and "/" in s and s[:1].isdigit():
            p = s.split()
            if len(p) >= 3 and (p[0].endswith("/tcp") or p[0].endswith("/udp")):
                result[cur].append({
                    "port": int(p[0].split("/")[0]),
                    "protocol": p[0].split("/")[1],
                    "state": p[1],
                    "service": p[2]
                })
    return result

def probe_tv_services(host):
    """Verifica rapidamente alcune firme HTTP tipiche di TV/streaming sulla LAN."""
    import urllib.request
    ip = host.get("ip")
    ports = {p["port"] for p in host.get("ports", []) if p.get("state") == "open"}
    hits = []

    checks = []
    if 8060 in ports:
        checks.append((8060, "/query/device-info", "roku"))
    if 8008 in ports:
        checks.append((8008, "/ssdp/device-desc.xml", "google cast"))

    for port, path, marker in checks:
        try:
            req = urllib.request.Request(
                f"http://{ip}:{port}{path}",
                headers={"User-Agent": "NetScope/1.0"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as r:
                body = r.read(4096).decode("utf-8", "ignore").lower()
                if marker in body or (port == 8060 and "model-name" in body):
                    hits.append(marker)
        except Exception:
            pass
    return hits

def classify_device(host):
    """Classifica il tipo usando hostname, vendor, porte e servizi.
    È una stima: l'IP da solo non identifica con certezza il dispositivo.
    """
    ports = {p["port"] for p in host.get("ports", []) if p.get("state") == "open"}
    services = " ".join(
        f'{p.get("service","")} {p.get("version","")}' for p in host.get("ports", [])
    ).lower()
    name = (host.get("hostname") or "").lower()
    vendor = (host.get("vendor") or "").lower()

    def result(device, confidence, reason):
        return {"device": device, "confidence": confidence, "reason": reason}

    tv_ports = {
        3000, 3001, 52323, 55000, 8001, 8002, 8008, 8009,
        8060, 7000, 7100, 9080
    }
    tv_words = (
        "tv", "smarttv", "smart-tv", "tizen", "webos", "roku",
        "bravia", "aquos", "viera", "philips", "androidtv", "google tv",
        "chromecast", "firetv"
    )
    tv_vendors = (
        "samsung", "lg electronics", "roku", "sony", "hisense",
        "philips", "panasonic", "tcl", "vestel", "sharp"
    )
    if any(x in name or x in services for x in tv_words):
        return result("Smart TV / TV", "alta", "hostname o servizio TV")
    if ports & tv_ports and any(x in vendor for x in tv_vendors):
        return result("Smart TV / TV", "alta", "vendor TV + porte tipiche TV")
    if ports & {8008, 8009} and (
        "google" in vendor or "android" in vendor or "chromecast" in services
    ):
        return result("Smart TV / Chromecast / Google TV", "media", "porte Google Cast")
    tv_probe = probe_tv_services(host)
    if "roku" in tv_probe:
        return result("Roku / Smart TV", "alta", "firma HTTP Roku sulla porta 8060")
    if "google cast" in tv_probe:
        return result("Google TV / Chromecast", "alta", "firma Google Cast sulla porta 8008")
    if 8060 in ports:
        return result("Possibile Roku / Smart TV", "media", "porta 8060 compatibile Roku, firma non confermata")
    if 8001 in ports or 8002 in ports:
        return result("Samsung Smart TV", "alta", "porte Samsung 8001/8002")

    if "brother" in vendor or "printer" in name or "print" in name:
        return result("Stampante", "alta", "vendor/hostname stampante")
    if "synology" in vendor or "nas" in name:
        return result("NAS / Synology", "alta", "vendor/hostname NAS")
    if "apple" in vendor or any(x in name for x in ("iphone", "ipad", "macbook", "imac", "macmini")):
        if "iphone" in name or "ipad" in name:
            return result("Smartphone / Tablet Apple", "alta", "hostname Apple mobile")
        return result("Apple / Mac", "media", "vendor Apple")

    android_vendors = (
        "xiaomi", "samsung electronics", "oneplus", "oppo", "vivo",
        "realme", "motorola", "huawei", "honor", "google"
    )
    android_names = (
        "android", "redmi", "poco", "galaxy", "pixel", "oneplus",
        "oppo", "vivo", "realme", "motorola", "huawei", "honor"
    )
    if 5555 in ports:
        return result("Android / ADB", "alta", "ADB TCP 5555")
    if any(x in name for x in android_names):
        return result("Smartphone / Tablet Android", "alta", "hostname Android")
    if any(x in vendor for x in android_vendors):
        return result("Probabile smartphone/tablet Android", "media", "vendor mobile Android")

    if any(x in vendor for x in ("routerboard", "ubiquiti", "mikrotik", "tp-link", "netgear", "tenda")):
        return result("Router / Access Point", "alta", "vendor rete")
    if 3389 in ports or 445 in ports or 139 in ports:
        return result("PC Windows", "alta", "RDP/SMB/NetBIOS")
    if 548 in ports or 5000 in ports or "macbook" in name:
        return result("Mac", "media", "servizi macOS/hostname")
    if "camera" in name or "cam" in name or "hikvision" in vendor:
        return result("Telecamera / IoT", "alta", "hostname/vendor camera")
    if 22 in ports and (80 in ports or 443 in ports):
        return result("Server / Linux", "media", "SSH + web")
    if 80 in ports or 443 in ports:
        router_words = (
            "router", "gateway", "modem", "ap", "openwrt", "asus",
            "tp-link", "tenda", "netgear", "ubiquiti", "mikrotik",
            "vodafone", "tim", "fastweb"
        )
        if any(x in name or x in vendor for x in router_words):
            return result("Router / Access Point", "media", "hostname/vendor rete")
    if ports:
        return result("Dispositivo di rete", "bassa", "porte rilevate senza firma specifica")
    return result("Host", "bassa", "nessuna firma disponibile")

def run_scan(target, port_scan=True):
    c = db()
    started = datetime.now(timezone.utc).isoformat()
    t = time.time()

    out, err, rc, d = nmap(target)
    hosts = parse_hosts(out)
    # Non sovrascrivere una scansione LAN valida con una scansione
    # di un singolo host vuoto: se il target è una subnet, manteniamo
    # il comportamento normale; i target singoli restano supportati.

    # Nmap non sempre riceve hostname dalla rete locale.
    # Aggiungiamo una seconda fonte: NetBIOS.
    enrich_netbios(hosts)

    if port_scan:
        for h in hosts:
            po, _, _, _ = nmap(
                h["ip"],
                "22,53,80,110,139,443,445,3000,3001,3389,52323,55000,5900,7000,7100,8001,8002,8008,8009,8060,8080,8443,9080,5555"
            )
            h["ports"] = parse_ports(po).get(h["ip"], [])
    for h in hosts:
        info = classify_device(h)
        h["device"] = info["device"]
        h["device_confidence"] = info["confidence"]
        h["device_reason"] = info["reason"]

    cur = c.execute(
        "INSERT INTO scans(started_at,target,host_count,duration) VALUES(?,?,?,?)",
        (started, target, len(hosts), d))
    sid = cur.lastrowid

    for h in hosts:
        hc = c.execute(
            """INSERT INTO hosts(scan_id,ip,mac,hostname,status,device,vendor,device_confidence,device_reason)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (sid, h["ip"], h["mac"], h["hostname"], h["status"],
             h["device"], h.get("vendor"), h.get("device_confidence"), h.get("device_reason"))
        ).lastrowid
        for x in h.get("ports", []):
            c.execute(
                """INSERT INTO ports(scan_id,host_id,port,protocol,state,service)
                   VALUES(?,?,?,?,?,?)""",
                (sid, hc, x["port"], x["protocol"], x["state"], x["service"]))

    c.commit()
    c.close()
    return sid, hosts, time.time() - t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--discovery-only", action="store_true")
    a = ap.parse_args()
    target = a.target or detect_target()
    if not target:
        return 2

    sid, hosts, d = run_scan(target, not a.discovery_only)
    if a.json:
        print(json.dumps({
            "scan_id": sid, "target": target,
            "duration": round(d, 2), "hosts": hosts
        }, indent=2))
    else:
        print(f"[OK] Scan #{sid} | {target} | {len(hosts)} host | {d:.1f}s")
        for h in hosts:
            print(f"  {h['ip']}  {h.get('hostname') or '-'}  "
                  f"{h.get('device') or '-'}  "
                  f"VENDOR={h.get('vendor') or '-'}  MAC={h['mac'] or '-'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
