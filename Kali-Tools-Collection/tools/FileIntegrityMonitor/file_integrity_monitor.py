
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'File Integrity Monitor'
_ts_register(_TS_NAME)
_ts_publish(_TS_NAME, 'startup', {'pid': __import__('os').getpid()})
# --- ToolAuth integration ---
if '/home/jack0p000/ToolAuth' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolAuth')
from auth import login as _ta_login
_ta_login(_TS_NAME)
# --- end ToolAuth integration ---
# --- end ToolShare integration ---
import html,os,subprocess,threading,time,urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
def page(t,b):
    from ui_theme import render_tool_page
    return render_tool_page(t,b)
def gui(title,port,body):
 class H(BaseHTTPRequestHandler):
  def log_message(self,*a): pass
  def do_GET(self):
   q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); out=body(q)
   self.send_response(200); self.send_header("Content-Type","text/html"); self.end_headers(); self.wfile.write(out.encode())
 s=ThreadingHTTPServer(("127.0.0.1",port),H); threading.Thread(target=s.serve_forever,daemon=True).start()
 try: subprocess.Popen(["google-chrome",f"http://127.0.0.1:{port}"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except: pass
 print(f"GUI: http://127.0.0.1:{port}")
 while True: time.sleep(1)
def menu(n):
 print("\n===",n,"===\n[1] Terminale\n[2] GUI web\n[3] Esci"); return input("> ").strip()
import hashlib,json,pathlib,html
DB=pathlib.Path.home()/".fim_baseline.json"
def snap(root):
 d={}
 for p in pathlib.Path(root).rglob("*"):
  try:
   if p.is_file():
    h=hashlib.sha256(p.read_bytes()).hexdigest(); d[str(p)]=h
  except: pass
 return d
def run(root,mode):
 n=snap(root)
 if mode=="1": DB.write_text(json.dumps(n)); return f"Baseline salvata: {len(n)} file."
 if not DB.exists(): return "Baseline assente."
 o=json.loads(DB.read_text()); a=set(n)-set(o); z=set(o)-set(n); m={x for x in (n.keys() & o.keys()) if n[x]!=o[x]}
 return f"Aggiunti: {len(a)}\nRimossi: {len(z)}\nModificati: {len(m)}\n\n"+ "\n".join("MOD "+x for x in sorted(m)[:100])
while True:
 c=menu("File Integrity Monitor")
 if c=="1":
  root=input("Cartella: ") or "."
  mode=input("[1] Baseline [2] Confronta: ").strip()
  result=run(root,mode); print(result)
  _ts_publish(_TS_NAME,'integrity_check',{'root':root,'mode':mode,'result':result[:2000]})
  input("\nPremi INVIO per continuare...")
 elif c=="2":
  gui("File Integrity Monitor",8786,lambda q:page("File Integrity Monitor",("<pre>"+html.escape(run(q.get("r",["."])[0],"2"))+"</pre>" if q.get("r") else '<form><input name=r value=.><button>Confronta</button></form>')))
 elif c=="3":
  break
