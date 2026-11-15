
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'System Health Center'
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
import os, signal, socket, subprocess, time
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PIDFILE = os.path.join(BASE, "health_center.pid")

def cleanup(*_):
    try:
        if os.path.exists(PIDFILE):
            os.remove(PIDFILE)
    finally:
        raise SystemExit(0)

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""

def get_cpu():
    line = next((x for x in read_file("/proc/stat").splitlines() if x.startswith("cpu ")), "")
    v = [int(x) for x in line.split()[1:8]]
    return v[3] + v[4], sum(v)

def cpu_percent():
    a = get_cpu()
    time.sleep(0.35)
    b = get_cpu()
    idle, total = b[0] - a[0], b[1] - a[1]
    return round(100 * (1 - idle / total), 1) if total else 0.0

def meminfo():
    d = {}
    for line in read_file("/proc/meminfo").splitlines():
        p = line.split()
        if len(p) >= 2:
            try: d[p[0].rstrip(":")] = int(p[1]) * 1024
            except ValueError: pass
    total = d.get("MemTotal", 0)
    avail = d.get("MemAvailable", 0)
    return total, total - avail

def swap_info():
    total = free = 0
    for line in read_file("/proc/swaps").splitlines()[1:]:
        p = line.split()
        if len(p) >= 4:
            total += int(p[2]); free += int(p[3])
    used = total - free
    return used, total

def disk_info():
    st = os.statvfs("/")
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    return total - free, total, free

def fmt_bytes(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB": return f"{n:.1f} {u}"
        n /= 1024

def fmt_uptime(sec):
    sec = int(sec)
    return f"{sec//86400}g {(sec%86400)//3600}h {(sec%3600)//60}m"

def battery():
    base = "/sys/class/power_supply"
    if not os.path.isdir(base): return "N/D"
    for name in os.listdir(base):
        p = os.path.join(base, name)
        cap = read_file(os.path.join(p, "capacity"))
        if cap:
            status = read_file(os.path.join(p, "status"))
            return f"{cap}% ({status})" if status else f"{cap}%"
    return "N/D"

def temperature():
    base = "/sys/class/thermal"
    if not os.path.isdir(base): return None
    for name in os.listdir(base):
        if name.startswith("thermal_zone"):
            raw = read_file(os.path.join(base, name, "temp"))
            typ = read_file(os.path.join(base, name, "type"))
            try:
                c = int(raw) / 1000
                if -20 < c < 120: return typ or name, c
            except ValueError: pass
    return None

def services():
    result = []
    for name in ("NetworkManager", "ssh", "cron"):
        try:
            p = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=2)
            result.append((name, p.stdout.strip() or "unknown"))
        except Exception:
            result.append((name, "unknown"))
    return result

def report():
    mem_total, mem_used = meminfo()
    disk_used, disk_total, disk_free = disk_info()
    swap_used, swap_total = swap_info()
    temp = temperature()
    print("\x1b[2J\x1b[H", end="")
    print("=== SYSTEM HEALTH CENTER ===")
    print(f"Host: {socket.gethostname()}    {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"Uptime: {fmt_uptime(float(read_file('/proc/uptime').split()[0]))}")
    print()
    print(f"CPU       {cpu_percent():>5}%")
    print(f"RAM       {100*mem_used/mem_total:>5.1f}%  {fmt_bytes(mem_used)} / {fmt_bytes(mem_total)}")
    print(f"DISCO     {100*disk_used/disk_total:>5.1f}%  {fmt_bytes(disk_used)} / {fmt_bytes(disk_total)}")
    print(f"SWAP      {100*swap_used/swap_total if swap_total else 0:>5.1f}%  {fmt_bytes(swap_used)} / {fmt_bytes(swap_total)}")
    print(f"BATTERIA  {battery()}")
    print(f"TEMP      {temp[1]:.1f} C ({temp[0]})" if temp else "TEMP      N/D")
    print()
    print("SERVIZI")
    for name, state in services():
        print(f"  {name:<16} {state}")
    print()
    print("Aggiornamento ogni 2 secondi. CTRL+C per uscire.")

def main():
    if os.path.exists(PIDFILE):
        try:
            old = int(read_file(PIDFILE)); os.kill(old, 0)
            print(f"[!] System Health Center già attivo (PID {old})."); return 1
        except Exception: pass
    with open(PIDFILE, "w", encoding="utf-8") as f: f.write(str(os.getpid()))
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP): signal.signal(sig, cleanup)
    try:
        while True:
            report(); time.sleep(2)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    raise SystemExit(main())
