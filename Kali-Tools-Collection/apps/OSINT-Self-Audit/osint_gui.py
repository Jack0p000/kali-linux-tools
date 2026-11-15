
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'OSINT Self-Audit GUI'
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
import json, os, secrets, threading, time, webbrowser, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote
from pathlib import Path
from pypdf import PdfReader
import osint_self_audit_v2 as core

HOST="127.0.0.1"
PORT=8766
GUI_USER=os.getenv("TOOL_AUTH_USER",os.getenv("OSINT_GUI_USER","Admin"))
GUI_PASSWORD=os.getenv("TOOL_AUTH_PASS",os.getenv("OSINT_GUI_PASSWORD",""))
SESSIONS={}
LOCK=threading.Lock()
LAST_DATA={}

HERE = Path(__file__).resolve().parent
HTML_FILE = HERE / "osint_web_gui.html"
HTML = HTML_FILE.read_text(encoding="utf-8")


def stats_from_data(data):
    emails=set();domains=set();dns=0;accounts=0
    target=data.get("target",{})
    def walk(o):
        nonlocal dns,accounts
        if isinstance(o,dict):
            for k,v in o.items():
                lk=str(k).lower()
                vals=v if isinstance(v,list) else [v]
                if lk in ("email","emails","mail"):
                    emails.update(x for x in vals if isinstance(x,str) and "@" in x)
                if lk in ("domain","domains"):
                    domains.update(x for x in vals if isinstance(x,str) and "." in x)
                if "dns" in lk and isinstance(v,(list,dict)): dns+=len(v)
                if lk in ("accounts","profiles","social_profiles","username_hits"): accounts+=len(v) if isinstance(v,(list,dict)) else 0
                walk(v)
        elif isinstance(o,list):
            for x in o: walk(x)
    walk(data)
    if target.get("domain"): domains.add(target["domain"])
    if target.get("email") and "@" in target["email"]: domains.add(target["email"].split("@",1)[1])
    return {"domains":len(domains),"emails":len(emails),"dns":dns,"accounts":accounts}

def run_scan(p):
    username=(p.get("username") or "").strip() or None
    email=(p.get("email") or "").strip() or None
    phone=(p.get("phone") or "").strip() or None
    domain=(p.get("domain") or "").strip() or None

    data=core.build_report(
        username=username,
        email=email,
        phone=phone,
        domains=[domain] if domain else [],
    )

    pdf=core.create_pdf(data)
    core.run_report_manager()

    s=stats_from_data(data)
    LAST_DATA.clear()
    LAST_DATA.update(s)

    events=[]

    if username:
        events.append({"kind":"Username","text":username})
    if email:
        events.append({"kind":"Email","text":email})
    if phone:
        events.append({"kind":"Phone","text":phone})
    if domain:
        events.append({"kind":"Domain","text":domain})

    for item in data.get("phone_results", []):
        if item.get("public_results"):
            for result in item["public_results"][:30]:
                events.append({
                    "kind":"Phone public result",
                    "text":result.get("title") or result.get("url") or "Risultato pubblico",
                })
        else:
            events.append({
                "kind":"Phone public result",
                "text":"Nessuna occorrenza pubblica rilevata",
            })

    # Riporta nel log i risultati pubblici realmente trovati.
    for key, label in (
        ("username_results", "Username"),
        ("email_results", "Email"),
        ("domain_results", "Domain"),
    ):
        for item in data.get(key, [])[:30]:
            if isinstance(item, dict):
                value=item.get("title") or item.get("url") or item.get("value")
            else:
                value=str(item)
            if value:
                events.append({"kind":label, "text":value})

    return os.path.basename(pdf),s,events

def latest_pdf_data():
    """Legge l'ultimo report PDF realmente presente nella cartella reports."""
    files=sorted((p for p in Path(core.REPORT_DIR).glob("*.pdf") if p.is_file()), key=lambda p:p.stat().st_mtime, reverse=True)
    if not files:
        return {"ok":False,"reason":"Nessun report PDF disponibile."}
    fp=files[0]
    text="\n".join((page.extract_text() or "") for page in PdfReader(str(fp)).pages)
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    target=""
    for i,line in enumerate(lines):
        if line.lower()=="username" and i+1<len(lines): target=lines[i+1]; break
        if line.lower()=="email" and i+1<len(lines): target=lines[i+1]; break
        if line.lower()=="domain" and i+1<len(lines): target=lines[i+1]; break
    social=0
    in_social=False
    for line in lines:
        if line.upper() in ("USERNAME / SOCIAL","SOCIAL / USERNAME"):
            in_social=True; continue
        if in_social and line.upper() in ("EMAIL","CORRELAZIONI WEB PUBBLICHE"):
            in_social=False
        elif in_social and line in ("FOUND","NOT FOUND"):
            social += 1
    domains=set()
    for line in lines:
        if line.startswith("Domini pubblicamente rilevati:"):
            domains.update(x.strip() for x in line.split(":",1)[1].split(",") if x.strip())
        elif line.startswith("Dominio:"):
            domains.add(line.split(":",1)[1].strip())
    dns=sum(1 for line in lines if line.startswith(("A:","AAAA:","MX:","NS:","RDAP:","TLS subject")))
    emails=sum(1 for line in lines if "Email pubbliche trovate:" in line and "nessuna" not in line.lower())
    if emails == 0:
        emails=sum(1 for line in lines if "@" in line and (line.lower().startswith(("email:","emails:")) or "email pubblic" in line.lower()))
    return {"ok":True,"file":fp.name,"target":target,"text":text,"stats":{"domains":len(domains),"emails":emails,"dns":dns,"accounts":social}}

def new_session():
    t=secrets.token_urlsafe(32)
    with LOCK:SESSIONS[t]=time.time()+14400
    return t
def valid(t):
    with LOCK:
        e=SESSIONS.get(t)
        if not e:return False
        if e<time.time():SESSIONS.pop(t,None);return False
        return True

class Handler(BaseHTTPRequestHandler):
    def js(self,o,status=200):
        raw=json.dumps(o,ensure_ascii=False).encode();self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        p=urlparse(self.path);path=unquote(p.path)
        if path=="/":
            raw=HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if path=="/api/status":
            if not valid(self.headers.get("X-Session")):self.js({"ok":False},401);return
            report=latest_pdf_data()
            stats=dict(LAST_DATA) if LAST_DATA else (report.get("stats",{}) if report.get("ok") else {})
            self.js({"ok":True,"stats":stats,"report":report});return
        if path=="/api/report/latest":
            if not valid(self.headers.get("X-Session")):self.js({"ok":False},401);return
            self.js(latest_pdf_data());return
        if path=="/api/reports":
            if not valid(self.headers.get("X-Session")):self.js({"error":"Unauthorized"},401);return
            self.js({"reports":sorted([x for x in os.listdir(core.REPORT_DIR) if x.lower().endswith(".pdf")],reverse=True)});return
        if path.startswith("/reports/"):
            q=p.query;token=q.split("session=",1)[1].split("&",1)[0] if "session=" in q else ""
            if not valid(unquote(token)):self.send_error(401);return
            name=os.path.basename(path[len("/reports/"):]);fp=os.path.join(core.REPORT_DIR,name)
            if os.path.isfile(fp) and name.lower().endswith(".pdf"):
                with open(fp,"rb") as f:raw=f.read()
                self.send_response(200);self.send_header("Content-Type","application/pdf");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw);return
        self.send_error(404)
    def do_POST(self):
        if self.path=="/api/login":
            try:
                n=int(self.headers.get("Content-Length","0"));p=json.loads(self.rfile.read(n).decode())
                if p.get("user")==GUI_USER and p.get("pass")==GUI_PASSWORD:self.js({"ok":True,"session":new_session()})
                else:self.js({"ok":False,"error":"Username o password errati."},401)
            except Exception as e:self.js({"error":str(e)},400)
            return
        if self.path=="/api/logout":
            with LOCK:SESSIONS.pop(self.headers.get("X-Session"),None)
            self.js({"ok":True});return
        if self.path!="/api/scan":self.send_error(404);return
        if not valid(self.headers.get("X-Session")):self.js({"error":"Sessione scaduta."},401);return
        try:
            n=int(self.headers.get("Content-Length","0"));p=json.loads(self.rfile.read(n).decode());pdf,s,events=run_scan(p);self.js({"ok":True,"pdf":pdf,"stats":s,"events":events})
        except Exception as e:self.js({"ok":False,"error":str(e)},500)
    def log_message(self,fmt,*args):print("[GUI] "+(fmt%args))

def start():
    url=f"http://{HOST}:{PORT}"
    # Se la GUI è già attiva, non tentare di creare un secondo server:
    # apri semplicemente la dashboard esistente.
    import socket
    probe=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    probe.settimeout(0.5)
    try:
        already_running=(probe.connect_ex((HOST,PORT))==0)
    finally:
        probe.close()
    if already_running:
        print(f"[+] GUI già attiva: {url}")
        try:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            webbrowser.open(url)
        return

    srv=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f"[+] GUI: {url}\n[+] Username: {GUI_USER}")
    def open_browser():
        try:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            webbrowser.open(url)
    threading.Timer(.5, open_browser).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()

if __name__=="__main__":start()
