#!/usr/bin/env python3
import sys, os, socket, html, subprocess, threading, time, urllib.parse
sys.path.insert(0,'/home/jack0p000/ToolShareHub')
from toolshare import register, publish
sys.path.insert(0,'/home/jack0p000/ToolAuth')
from auth import login

NAME='DNS Inspector'
login(NAME)
register(NAME)
publish(NAME,'startup',{'pid':os.getpid()})

def page(title,body):
    from ui_theme import render_tool_page
    return render_tool_page(title,body)

def resolve(host):
    host=host.strip()
    if not host:
        return "Inserisci un dominio."
    try:
        addresses=sorted({x[4][0] for x in socket.getaddrinfo(host,None)})
        publish(NAME,'resolved',{'domain':host,'addresses':addresses,'count':len(addresses)})
        return "\n".join(addresses) if addresses else "Nessun indirizzo trovato."
    except Exception as e:
        publish(NAME,'resolve_error',{'domain':host,'error':str(e)})
        return "ERRORE: "+str(e)

def gui(title,port):
    class H(__import__('http.server',fromlist=['BaseHTTPRequestHandler']).BaseHTTPRequestHandler):
        def log_message(self,*a): pass
        def do_GET(self):
            q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get('h'):
                result=resolve(q['h'][0])
                body='<pre>'+html.escape(result)+'</pre><p><a href="/">Nuova ricerca</a></p>'
            else:
                body='<form><input name=h placeholder="example.com" autofocus><button>Risolvi</button></form>'
            out=page(title,body).encode()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(out))); self.end_headers(); self.wfile.write(out)
    from http.server import ThreadingHTTPServer
    server=ThreadingHTTPServer(("127.0.0.1",port),H)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        subprocess.Popen(["google-chrome",f"http://127.0.0.1:{port}"],
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception:
        pass
    print(f"GUI: http://127.0.0.1:{port}")
    while True:
        time.sleep(1)

def terminal():
    while True:
        print("\n=== DNS Inspector ===")
        print("[1] Risolvi dominio")
        print("[2] GUI web")
        print("[3] Esci")
        c=input("> ").strip()
        if c=="1":
            host=input("Dominio: ").strip()
            print("\n"+resolve(host))
            input("\nPremi INVIO per continuare...")
        elif c=="2":
            gui("DNS Inspector",8782)
        elif c=="3":
            break

if __name__=="__main__":
    terminal()
