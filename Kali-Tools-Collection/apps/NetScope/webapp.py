
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'NetScope Web'
_ts_register(_TS_NAME)
_ts_publish(_TS_NAME, 'startup', {'pid': __import__('os').getpid()})
# --- ToolAuth integration ---
if '/home/jack0p000/ToolAuth' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolAuth')
from auth import login as _ta_login
_ta_login(_TS_NAME)
# --- end ToolAuth integration ---
# --- end ToolShare integration ---
from flask import Flask,render_template,jsonify
import sqlite3,os,subprocess,threading
BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.path.join(BASE,"database","netscope.sqlite")
app=Flask(__name__)
def q(sql,args=()):
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    rows=[dict(x) for x in c.execute(sql,args)]; c.close(); return rows
@app.get("/")
def index(): return render_template("index.html")
@app.get("/api/scans")
def scans(): return jsonify(q("SELECT * FROM scans ORDER BY id DESC LIMIT 20"))
@app.get("/api/scan/<int:sid>")
def scan(sid):
    hosts=q("SELECT * FROM hosts WHERE scan_id=?",(sid,))
    for h in hosts:
        # Il nome mostrato è il hostname/NetBIOS del dispositivo, non il vendor.
        h["device_name"] = h.get("hostname") or "Nome dispositivo non rilevato"
        h["device"] = h.get("device") or "Tipo non rilevato"
        h["vendor"] = h.get("vendor") or "Vendor non rilevato"
    for h in hosts: h["ports"]=q("SELECT port,protocol,state,service FROM ports WHERE host_id=?",(h["id"],))
    return jsonify({"scan":q("SELECT * FROM scans WHERE id=?",(sid,))[0],"hosts":hosts})
@app.post("/api/scan")
def start():
    threading.Thread(target=lambda: subprocess.run(["python3",os.path.join(BASE,"netscope.py")],cwd=BASE),daemon=True).start()
    return jsonify({"started":True})
if __name__=="__main__": app.run(host="0.0.0.0",port=5050,debug=False)
