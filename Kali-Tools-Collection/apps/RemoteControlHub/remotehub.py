
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'RemoteControlHub'
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
import json, re, socket, subprocess, shlex, time
from pathlib import Path

BASE=Path(__file__).resolve().parent
LOG=BASE/"logs"; LOG.mkdir(exist_ok=True)
COMMON=[22,80,443,3389,5900,5985,5986,445,139,5555,6466,6467,8008,8009,8060,8443]

def log(msg):
    with open(LOG/"remotehub.log","a",encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S")+" "+msg+"\n")

def valid_target(t):
    return bool(re.fullmatch(r"[A-Za-z0-9_.:-]+", t)) and len(t)<=253

def scan(target):
    if not valid_target(target):
        raise ValueError("IP/hostname non valido")
    cmd=["nmap","-Pn","-T3","-sV","--version-light","-p",",".join(map(str,COMMON)),target]
    log("scan "+target)
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
    out=p.stdout
    ports=[]
    for line in out.splitlines():
        m=re.match(r"^(\d+)/(tcp|udp)\s+(open|closed|filtered)\s+([^\s]+)(?:\s+(.*))?$",line.strip())
        if m:
            ports.append({"port":int(m.group(1)),"protocol":m.group(2),"state":m.group(3),
                          "service":m.group(4),"version":(m.group(5) or "").strip()})
    hostname=None
    m=re.search(r"Nmap scan report for (.+)",out)
    if m:
        val=m.group(1).strip()
        if " (" in val: hostname=val.split(" (",1)[0]
        else: hostname=val
    online="Host is up" in out
    return {"target":target,"online":online,"hostname":hostname,"ports":ports,
            "services":service_summary(ports),"raw":out[-12000:]}

def service_summary(ports):
    mapping={22:"SSH",80:"HTTP",443:"HTTPS",3389:"RDP",5900:"VNC",5985:"WinRM HTTP",
             5986:"WinRM HTTPS",445:"SMB",139:"NetBIOS",5555:"ADB"}
    return [{"port":p["port"],"name":mapping.get(p["port"],p["service"])} for p in ports if p["state"]=="open"]

def connection_command(target, method):
    cmds={
      "ssh":f"ssh {shlex.quote(target)}",
      "rdp":f"xfreerdp3 /v:{shlex.quote(target)}",
      "vnc":f"vncviewer {shlex.quote(target)}:5900",
      "adb":f"adb connect {shlex.quote(target)}:5555",
      "winrm":f"evil-winrm -i {shlex.quote(target)}"
    }
    return cmds.get(method)

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(description="RemoteControlHub - authorized remote administration")
    ap.add_argument("target")
    ap.add_argument("--json",action="store_true")
    a=ap.parse_args()
    result=scan(a.target)
    print(json.dumps(result,ensure_ascii=False,indent=2) if a.json else result["raw"])
