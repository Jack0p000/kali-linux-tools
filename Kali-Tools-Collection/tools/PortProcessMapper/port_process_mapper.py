
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'Port Process Mapper'
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
import os,html
def f():
 r=[]
 try:
  for ln in open("/proc/net/tcp"):
   p=ln.split()
   if len(p)>3 and p[3]=="0A": r.append(f"porta {int(p[1].split(':')[1],16)} inode {p[9]}")
 except Exception as e:return str(e)
 return "\n".join(r) or "Nessuna porta LISTEN."
while True:
 c=menu("Port Process Mapper")
 if c=="1":
  result=f(); print(result)
  _ts_publish(_TS_NAME,'ports_snapshot',{'result':result})
  input("\nPremi INVIO per continuare...")
 elif c=="2":
  gui("Port Process Mapper",8784,lambda q:page("Port Process Mapper","<pre>"+html.escape(f())+"</pre><meta http-equiv=refresh content=5>"))
 elif c=="3":
  break
