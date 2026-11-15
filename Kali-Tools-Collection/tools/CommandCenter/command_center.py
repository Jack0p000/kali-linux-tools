#!/usr/bin/env python3
import sys, subprocess, threading, time, html, urllib.parse, json, os, shutil, signal
sys.path.insert(0,'/home/jack0p000/ToolShareHub')
sys.path.insert(0,'/home/jack0p000/ToolAuth')
from toolshare import register, publish, context, start_hub
from auth import login

NAME='Command Center'
login(NAME)
register(NAME)
publish(NAME,'startup',{'role':'controller','auth':'auto'})

T=[
 ('FileForensics','/home/jack0p000/Tools/FileForensics/run_tool.sh','terminal'),
 ('DNS Inspector','/home/jack0p000/Tools/DNSInspector/run_tool.sh','terminal'),
 ('Certificate Watcher','/home/jack0p000/Tools/CertificateWatcher/run_tool.sh','terminal'),
 ('Port Process Mapper','/home/jack0p000/Tools/PortProcessMapper/run_tool.sh','terminal'),
 ('WiFi Signal Mapper','/home/jack0p000/Tools/WiFiSignalMapper/run_tool.sh','terminal'),
 ('File Integrity Monitor','/home/jack0p000/Tools/FileIntegrityMonitor/run_tool.sh','terminal'),
 ('Packet Visualizer','/home/jack0p000/Tools/PacketVisualizer/run_tool.sh','terminal'),
 ('Kali Toolbox Builder','/home/jack0p000/Tools/KaliToolboxBuilder/run_tool.sh','terminal'),
 ('System Health Center','/home/jack0p000/SystemHealthCenter/run_tool.sh','terminal'),
 ('NetScope','/home/jack0p000/NetScope/run_tool.sh','gui'),
 ('RemoteControlHub','/home/jack0p000/RemoteControlHub/run_tool.sh','gui'),
 ('OSINT Self-Audit','/home/jack0p000/Scaricati/run_osint_tool.sh','gui'),
 ('BreachFinder','/home/jack0p000/Scaricati/data_breach_scanner/run_tool.sh','gui')
]

RUNNING={}
LOCK=threading.Lock()

def terminal_command(name,path):
    wrapper='/home/jack0p000/ToolAuth/launch_authenticated.sh'
    return f"bash -lc 'export TOOL_NAME={name!r}; {wrapper} {name!r} {path!r} terminal; echo; echo \'=== {name} terminato ===\'; exec bash'"

def launch(i):
    if not (0<=i<len(T)): return False
    name,path,mode=T[i]
    with LOCK:
        old=RUNNING.get(name)
        if old and old.poll() is None:
            return True
    publish(NAME,'launch',{'target':name,'mode':mode})
    try:
        # Un solo terminale per il Command Center: ogni tool viene aperto in una nuova
        # scheda dello stesso terminale, senza creare una nuova finestra.
        if mode == 'gui':
            cmd=f"bash -lc 'export TOOL_NAME={name!r}; /home/jack0p000/ToolAuth/launch_authenticated.sh {name!r} {path!r} gui'"
        else:
            cmd=f"bash -lc 'export TOOL_NAME={name!r}; /home/jack0p000/ToolAuth/launch_authenticated.sh {name!r} {path!r} terminal'"
        terminal=shutil.which('xfce4-terminal') or shutil.which('qterminal')
        if terminal and terminal.endswith('xfce4-terminal'):
            p=subprocess.Popen([terminal,'--tab','--title='+name,'--command='+cmd],start_new_session=False)
        elif terminal and terminal.endswith('qterminal'):
            p=subprocess.Popen([terminal,'--tab','--title',name,'-e',cmd],start_new_session=False)
        else:
            p=subprocess.Popen(['bash','-lc',cmd],start_new_session=False)
        with LOCK: RUNNING[name]=p
        publish(NAME,'started',{'target':name,'mode':mode,'pid':p.pid,'ui':'new_tab_same_window'})
        return True
    except Exception as e:
        publish(NAME,'start_error',{'target':name,'error':str(e)})
        return False

def stop(name):
    with LOCK: p=RUNNING.get(name)
    if not p:
        publish(NAME,'stop',{'target':name,'status':'not_running'})
        return True
    if p.poll() is not None:
        with LOCK: RUNNING.pop(name,None)
        publish(NAME,'stop',{'target':name,'status':'already_stopped'})
        return True
    try:
        os.killpg(p.pid,signal.SIGTERM)
        try: p.wait(timeout=2)
        except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL)
        with LOCK: RUNNING.pop(name,None)
        publish(NAME,'stopped',{'target':name,'pid':p.pid})
        return True
    except Exception as e:
        publish(NAME,'stop_error',{'target':name,'error':str(e)})
        return False

def status(name):
    with LOCK: p=RUNNING.get(name)
    return bool(p and p.poll() is None)

def event_rows(limit=80):
    r=context(limit)
    return r.get('events',[]) if isinstance(r,dict) else []

def fmt_time(ts):
    try:return time.strftime('%H:%M:%S',time.localtime(float(ts)))
    except:return '--:--:--'

def event_card(e):
    tool=html.escape(str(e.get('tool','Tool')))
    ev=html.escape(str(e.get('event','evento')))
    data=e.get('data') or {}
    parts=[]
    if isinstance(data,dict):
        for k,v in data.items():
            if k in ('pid','role','auth') and ev not in ('started','stopped','launch','startup'): continue
            label=html.escape(str(k).replace('_',' ').capitalize())
            if isinstance(v,(dict,list)): val=html.escape(json.dumps(v,ensure_ascii=False))
            else: val=html.escape(str(v))
            parts.append(f'<span class="kv"><b>{label}:</b> {val}</span>')
    elif data: parts.append(f'<span class="kv">{html.escape(str(data))}</span>')
    details=''.join(parts) or '<span class="muted">Nessun dettaglio</span>'
    return f'''<div class="event"><div><span class="time">{fmt_time(e.get("ts"))}</span><b>{tool}</b><span class="eventname">{ev}</span></div><div class="details">{details}</div></div>'''

def gui():
    start_hub()
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    class H(BaseHTTPRequestHandler):
        def log_message(self,*a): pass
        def send_html(self,b):
            raw=b.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def do_GET(self):
            p=urllib.parse.urlparse(self.path); q=urllib.parse.parse_qs(p.query)
            if p.path.startswith('/start/'):
                launch(int(p.path.split('/')[2])); self.send_html('<meta http-equiv="refresh" content="0;url=/">'); return
            if p.path.startswith('/stop/'):
                stop(T[int(p.path.split('/')[2])][0]); self.send_html('<meta http-equiv="refresh" content="0;url=/">'); return
            if p.path=='/events':
                events=event_rows(100)
                body='''<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Eventi · Command Center</title>
<style>
:root{color-scheme:dark;--bg:#070d17;--panel:#102137;--line:#29445f;--text:#eaf3ff;--muted:#8da4bd;--blue:#55b8ff;--green:#57d6a5;--red:#ff8494}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(ellipse at 10% 0%,#16487555,transparent 38%),linear-gradient(145deg,#070d17,#0a1524 60%,#08111e);color:var(--text);font:14px/1.55 Inter,system-ui,sans-serif}
.shell{min-height:100vh;display:grid;grid-template-columns:235px minmax(0,1fr)}
.rail{position:sticky;top:0;height:100vh;padding:24px 17px;background:#081321e8;border-right:1px solid #20364e}
.brand{font-weight:900;letter-spacing:.13em;font-size:13px;padding:8px 9px 24px;border-bottom:1px solid #20364e}
.mark{display:inline-grid;place-items:center;width:34px;height:34px;margin-right:10px;border-radius:11px;background:linear-gradient(140deg,#1d9be8,#1b587f);vertical-align:middle}
.rail small{display:block;color:#7891aa;font-size:9px;letter-spacing:.14em;margin:4px 0 0 45px}
.navlabel{margin:26px 9px 10px;color:#5e7893;font-size:9px;letter-spacing:.18em;text-transform:uppercase}
.nav a{display:block;padding:10px 12px;margin:5px 0;border:1px solid transparent;border-radius:9px;color:#a8bfd6;text-decoration:none;font-size:12px}
.nav a:hover,.nav a.active{background:#143450;border-color:#2b5271;color:#eaf6ff}
.main{min-width:0;padding:30px clamp(16px,4vw,52px) 55px}
.top{display:flex;justify-content:space-between;align-items:center;gap:16px;border-bottom:1px solid #20364e;padding-bottom:18px}
.crumb{color:#7894af;font:10px ui-monospace,monospace;letter-spacing:.14em}
.live{color:#8ce4bd;background:#0d2b25;border:1px solid #285744;padding:7px 11px;border-radius:999px;font:10px ui-monospace,monospace}
h1{font-size:clamp(30px,4vw,44px);line-height:1.05;letter-spacing:-.055em;margin:32px 0 8px}
h2{font-size:15px;color:#cfe6ff;margin:28px 0 14px}
.muted{color:var(--muted)}
.card{padding:19px 20px;margin:12px 0;background:linear-gradient(145deg,#12263d,#0c1929);border:1px solid #29445f;border-radius:14px;box-shadow:0 16px 42px #0005}
.cardhead{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.tag{font:10px ui-monospace,monospace;letter-spacing:.1em;padding:5px 9px;border:1px solid #355878;border-radius:999px;color:#9acfff;background:#11263d}
.on{color:var(--green);font-weight:800}.off{color:var(--red);font-weight:800}
button,input{font:inherit;padding:11px 15px;margin:4px;background:#172b42;color:#e8f2ff;border:1px solid #385675;border-radius:9px;outline:none}
button{cursor:pointer;font-size:11px;font-weight:800;letter-spacing:.06em;transition:.18s}
button:hover{transform:translateY(-1px);border-color:#75c9ff;background:#1c3b5b}
input{min-width:min(360px,70vw);background:#081522}input:focus{border-color:#55b8ff;box-shadow:0 0 0 3px #55b8ff22}
.event{padding:16px 18px;margin:11px 0;background:linear-gradient(145deg,#122238,#0d1929);border:1px solid #2b4561;border-radius:13px}
.time{color:#83a3c1;margin-right:12px;font:11px ui-monospace,monospace}.eventname{margin-left:10px;color:#67ddb0;font:11px ui-monospace,monospace}
.details{margin-top:10px;color:#d7e7f7}.kv{display:inline-block;margin:3px 14px 3px 0;color:#b5cce2}
@media(max-width:760px){.shell{grid-template-columns:1fr}.rail{position:relative;height:auto;padding:12px 15px;border-right:0;border-bottom:1px solid #20364e}.brand{padding:0 4px 10px}.navlabel{display:none}.nav{display:flex;overflow:auto;padding-top:8px}.nav a{white-space:nowrap}.main{padding:18px 14px 35px}}
</style>
<div class="shell"><aside class="rail"><div class="brand"><span class="mark">K</span> KALI TOOLKIT<small>COMMAND CENTER</small></div><div class="navlabel">Control</div><nav class="nav"><a href="/">◈ &nbsp; Dashboard</a><a class="active" href="/events">⌁ &nbsp; Eventi condivisi</a></nav></aside><main class="main"><div class="top"><div class="crumb">KALI TOOLKIT / ACTIVITY STREAM</div><div class="live">TOOLSHARE ONLINE</div></div>
<h1>Eventi condivisi</h1><p class="muted"><a href="/">← Torna alla dashboard</a></p>'''
                body+=f'<p class="muted">Eventi reali pubblicati dai tool · {len(events)} mostrati</p>'
                body+=''.join(event_card(e) for e in events) or '<div class=event>Nessun evento condiviso.</div>'
                body+='</main></div>'
                self.send_html(body); return
            if p.path=='/broadcast':
                msg=q.get('message',[''])[0].strip()
                if msg: publish(NAME,'broadcast',{'message':msg})
                self.send_html('<meta http-equiv="refresh" content="0;url=/">'); return
            body='''<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Command Center · Kali Toolkit</title>
<style>
:root{color-scheme:dark;--bg:#070d17;--panel:#102137;--line:#29445f;--text:#eaf3ff;--muted:#8da4bd;--blue:#55b8ff;--green:#57d6a5;--red:#ff8494}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(ellipse at 10% 0%,#16487555,transparent 38%),linear-gradient(145deg,#070d17,#0a1524 60%,#08111e);color:var(--text);font:14px/1.55 Inter,system-ui,sans-serif}
.shell{min-height:100vh;display:grid;grid-template-columns:235px minmax(0,1fr)}
.rail{position:sticky;top:0;height:100vh;padding:24px 17px;background:#081321e8;border-right:1px solid #20364e}
.brand{font-weight:900;letter-spacing:.13em;font-size:13px;padding:8px 9px 24px;border-bottom:1px solid #20364e}
.mark{display:inline-grid;place-items:center;width:34px;height:34px;margin-right:10px;border-radius:11px;background:linear-gradient(140deg,#1d9be8,#1b587f);vertical-align:middle}
.rail small{display:block;color:#7891aa;font-size:9px;letter-spacing:.14em;margin:4px 0 0 45px}
.navlabel{margin:26px 9px 10px;color:#5e7893;font-size:9px;letter-spacing:.18em;text-transform:uppercase}
.nav a{display:block;padding:10px 12px;margin:5px 0;border:1px solid transparent;border-radius:9px;color:#a8bfd6;text-decoration:none;font-size:12px}
.nav a:hover,.nav a.active{background:#143450;border-color:#2b5271;color:#eaf6ff}
.main{min-width:0;padding:30px clamp(16px,4vw,52px) 55px}
.top{display:flex;justify-content:space-between;align-items:center;gap:16px;border-bottom:1px solid #20364e;padding-bottom:18px}
.crumb{color:#7894af;font:10px ui-monospace,monospace;letter-spacing:.14em}
.live{color:#8ce4bd;background:#0d2b25;border:1px solid #285744;padding:7px 11px;border-radius:999px;font:10px ui-monospace,monospace}
h1{font-size:clamp(30px,4vw,44px);line-height:1.05;letter-spacing:-.055em;margin:32px 0 8px}
h2{font-size:15px;color:#cfe6ff;margin:28px 0 14px}
.muted{color:var(--muted)}
.card{padding:19px 20px;margin:12px 0;background:linear-gradient(145deg,#12263d,#0c1929);border:1px solid #29445f;border-radius:14px;box-shadow:0 16px 42px #0005}
.cardhead{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.tag{font:10px ui-monospace,monospace;letter-spacing:.1em;padding:5px 9px;border:1px solid #355878;border-radius:999px;color:#9acfff;background:#11263d}
.on{color:var(--green);font-weight:800}.off{color:var(--red);font-weight:800}
button,input{font:inherit;padding:11px 15px;margin:4px;background:#172b42;color:#e8f2ff;border:1px solid #385675;border-radius:9px;outline:none}
button{cursor:pointer;font-size:11px;font-weight:800;letter-spacing:.06em;transition:.18s}
button:hover{transform:translateY(-1px);border-color:#75c9ff;background:#1c3b5b}
input{min-width:min(360px,70vw);background:#081522}input:focus{border-color:#55b8ff;box-shadow:0 0 0 3px #55b8ff22}
.event{padding:16px 18px;margin:11px 0;background:linear-gradient(145deg,#122238,#0d1929);border:1px solid #2b4561;border-radius:13px}
.time{color:#83a3c1;margin-right:12px;font:11px ui-monospace,monospace}.eventname{margin-left:10px;color:#67ddb0;font:11px ui-monospace,monospace}
.details{margin-top:10px;color:#d7e7f7}.kv{display:inline-block;margin:3px 14px 3px 0;color:#b5cce2}
@media(max-width:760px){.shell{grid-template-columns:1fr}.rail{position:relative;height:auto;padding:12px 15px;border-right:0;border-bottom:1px solid #20364e}.brand{padding:0 4px 10px}.navlabel{display:none}.nav{display:flex;overflow:auto;padding-top:8px}.nav a{white-space:nowrap}.main{padding:18px 14px 35px}}
</style>
<div class="shell"><aside class="rail"><div class="brand"><span class="mark">K</span> KALI TOOLKIT<small>COMMAND CENTER</small></div><div class="navlabel">Control</div><nav class="nav"><a class="active" href="/">◈ &nbsp; Dashboard</a><a href="/events">⌁ &nbsp; Eventi condivisi</a></nav></aside><main class="main"><div class="top"><div class="crumb">KALI TOOLKIT / SYSTEM CONTROL</div><div class="live">CONTROL CENTER READY</div></div>
<h1>Command Center</h1><p class="muted">Gestione centralizzata dei tool locali e delle comunicazioni tra processi.</p>'''
            body+=f'<div class="card"><b>Utente:</b> {html.escape(os.environ.get("TOOL_AUTH_USER","utente"))} · login automatico<br><b>ToolShare:</b> attivo su 127.0.0.1:8799</div><h2>Tool</h2>'
            for i,(n,_,m) in enumerate(T):
                on=status(n); state='<span class="on">● ATTIVO</span>' if on else '<span class="off">● FERMO</span>'
                if on:
                    actions=f'<a href="/stop/{i}"><button>■ Ferma</button></a>'
                else:
                    actions=f'<a href="/start/{i}"><button>▶ Avvia</button></a>'
                body+=f'<div class="card"><b>{html.escape(n)}</b><span class="tag">{m.upper()}</span> · {state}<div class="actions">{actions}</div></div>'
            body+='''<div class="card"><h3>Comunicazione tra tool</h3><form action="/broadcast"><input name="message" placeholder="Messaggio per tutti i tool" size="55"><button>Invia broadcast</button></form><p><a href="/events">Apri eventi condivisi</a></p></div>'''
            body+='</main></div>'
            self.send_html(body)
    s=ThreadingHTTPServer(('127.0.0.1',8790),H)
    threading.Thread(target=s.serve_forever,daemon=True).start()
    try: subprocess.Popen(['google-chrome','http://127.0.0.1:8790'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception: pass
    print('GUI: http://127.0.0.1:8790')
    while True: time.sleep(1)

while True:
    print('\n=== COMMAND CENTER ===')
    print('Utente:',os.environ.get('TOOL_AUTH_USER','utente'),'· accesso automatico OK')
    print('ToolShare: hub locale su 127.0.0.1:8799')
    for i,(n,_,m) in enumerate(T,1):
        print(f'[{"ON" if status(n) else "OFF"}] [{i}] {n} [{m}]')
    print('[e] Eventi condivisi  [b] Broadcast  [g] GUI web  [0] Esci')
    c=input('> ').strip()
    if c=='0': break
    if c.lower()=='g': gui()
    elif c.lower()=='e':
        for e in event_rows(50):
            print(f'[{fmt_time(e.get("ts"))}] {e.get("tool")} -> {e.get("event")}: {e.get("data")}')
    elif c.lower()=='b':
        msg=input('Messaggio: ').strip()
        if msg: publish(NAME,'broadcast',{'message':msg}); print('[OK] Broadcast inviato.')
    elif c.isdigit() and 1<=int(c)<=len(T):
        launch(int(c)-1)
