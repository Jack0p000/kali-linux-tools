#!/usr/bin/env python3
import json, sqlite3, time, threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from pathlib import Path
BASE=Path('/home/jack0p000/ToolShareHub'); DB=BASE/'toolshare.sqlite3'; HOST='127.0.0.1'; PORT=8799

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('CREATE TABLE IF NOT EXISTS tools(name TEXT PRIMARY KEY,version TEXT,pid INTEGER,last_seen REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,tool TEXT,event TEXT,data TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,src TEXT,target TEXT,message TEXT,data TEXT)')
    c.commit(); return c

def j(s):
    try:return json.loads(s)
    except:return {}

def out(h,code,p):
    raw=json.dumps(p,ensure_ascii=False).encode(); h.send_response(code)
    h.send_header('Content-Type','application/json; charset=utf-8'); h.send_header('Content-Length',str(len(raw)))
    h.end_headers(); h.wfile.write(raw)

class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        p=urlparse(self.path); q=parse_qs(p.query)
        if p.path=='/api/health':
            c=db(); n=c.execute('SELECT COUNT(*) FROM tools').fetchone()[0]; c.close()
            out(self,200,{'ok':True,'service':'ToolShareHub','tools':n}); return
        if p.path=='/api/tools':
            c=db(); rows=c.execute('SELECT name,version,pid,last_seen FROM tools ORDER BY name').fetchall(); c.close()
            out(self,200,{'tools':[dict(r) for r in rows]}); return
        if p.path=='/api/events':
            lim=min(max(int(q.get('limit',['20'])[0]),1),200); tool=q.get('tool',[None])[0]
            c=db()
            if tool: rows=c.execute('SELECT id,ts,tool,event,data FROM events WHERE tool=? ORDER BY id DESC LIMIT ?',(tool,lim)).fetchall()
            else: rows=c.execute('SELECT id,ts,tool,event,data FROM events ORDER BY id DESC LIMIT ?',(lim,)).fetchall()
            c.close()
            out(self,200,{'events':[{'id':r['id'],'ts':r['ts'],'tool':r['tool'],'event':r['event'],'data':j(r['data'])} for r in rows]}); return
        if p.path=='/api/messages':
            lim=min(max(int(q.get('limit',['20'])[0]),1),200); target=q.get('target',[None])[0]
            c=db()
            if target: rows=c.execute('SELECT id,ts,src,target,message,data FROM messages WHERE target=? OR target=? ORDER BY id DESC LIMIT ?',(target,'*',lim)).fetchall()
            else: rows=c.execute('SELECT id,ts,src,target,message,data FROM messages ORDER BY id DESC LIMIT ?',(lim,)).fetchall()
            c.close()
            out(self,200,{'messages':[{'id':r['id'],'ts':r['ts'],'from':r['src'],'to':r['target'],'message':r['message'],'data':j(r['data'])} for r in rows]}); return
        out(self,404,{'ok':False,'error':'not_found'})
    def do_POST(self):
        try:
            n=int(self.headers.get('Content-Length','0')); p=j(self.rfile.read(n).decode())
        except Exception:
            out(self,400,{'ok':False,'error':'invalid_json'}); return
        c=db()
        if self.path=='/api/register':
            c.execute('INSERT OR REPLACE INTO tools(name,version,pid,last_seen) VALUES(?,?,?,?)',(p.get('name','unknown'),p.get('version','1.0'),int(p.get('pid',0)),time.time())); c.commit(); c.close(); out(self,200,{'ok':True}); return
        if self.path=='/api/event':
            c.execute('INSERT INTO events(ts,tool,event,data) VALUES(?,?,?,?)',(time.time(),p.get('tool','unknown'),p.get('event','event'),json.dumps(p.get('data',{}),ensure_ascii=False))); c.commit(); c.close(); out(self,200,{'ok':True}); return
        if self.path=='/api/message':
            c.execute('INSERT INTO messages(ts,src,target,message,data) VALUES(?,?,?,?,?)',(time.time(),p.get('from','unknown'),p.get('to','*'),p.get('message',''),json.dumps(p.get('data',{}),ensure_ascii=False))); c.commit(); c.close(); out(self,200,{'ok':True}); return
        out(self,404,{'ok':False,'error':'not_found'})

def main():
    db().close(); print(f'ToolShareHub listening on http://{HOST}:{PORT}'); ThreadingHTTPServer((HOST,PORT),H).serve_forever()

if __name__=='__main__': main()
