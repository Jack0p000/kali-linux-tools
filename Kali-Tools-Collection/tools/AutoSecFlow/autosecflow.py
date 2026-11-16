#!/usr/bin/env python3
import os,sys,json,time,ssl,socket,hashlib,platform,shutil,threading,datetime,urllib.parse
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
NAME="AutoSecFlow"
HERE=Path(__file__).resolve().parent
COLLECTION=HERE.parents[1]
AUTH_DIRS=[COLLECTION/"apps"/"ToolAuth",Path.home()/"ToolAuth"]
SHARE_DIRS=[COLLECTION/"apps"/"ToolShareHub",Path.home()/"ToolShareHub"]
for directory in AUTH_DIRS:
 if directory.is_dir():sys.path.insert(0,str(directory));break
try:
 from auth import login
 login(NAME)
except ImportError as exc:
 raise RuntimeError("ToolAuth non trovato: configura apps/ToolAuth oppure ~/ToolAuth") from exc
try:
 for directory in SHARE_DIRS:
  if directory.is_dir():sys.path.insert(0,str(directory));break
 from toolshare import register,publish
 register(NAME);publish(NAME,"startup",{"pid":os.getpid()})
except ImportError:
 publish=None

BASE=Path.home()/".local"/"share"/"autosecflow";BASE.mkdir(parents=True,exist_ok=True)
STORE=BASE/"workflows.json";LOG=BASE/"activity.jsonl";LOCK=threading.Lock()
DEFAULT={"name":"Routine di controllo locale","trigger":"manual","nodes":[{"id":"n1","type":"system_snapshot","label":"Rileva stato sistema","value":""},{"id":"n2","type":"hash_directory","label":"Verifica integrità cartella","value":str(Path.home()/"Tools")},{"id":"n3","type":"log","label":"Registra completamento","value":"Controllo completato"}]}
def load():
 try:
  d=json.loads(STORE.read_text());return d if isinstance(d,list) else [DEFAULT]
 except:return [DEFAULT]
def record(level,msg,detail=""):
 row={"time":datetime.datetime.now().astimezone().isoformat(timespec="seconds"),"level":level,"message":msg,"detail":detail}
 with LOCK:
  with LOG.open("a") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
 try:
  if publish:publish(NAME,"workflow_event",row)
 except Exception:pass
 return row
def action(n):
 k=n["type"];v=n.get("value","").strip()
 if k=="log":return {"status":"ok","message":v or n["label"]}
 if k=="system_snapshot":
  d=shutil.disk_usage("/")
  return {"status":"ok","message":f"{platform.node()} · {platform.system()} {platform.release()} · Python {platform.python_version()} · Disco libero {d.free//(1024**3)} GB"}
 if k=="hash_directory":
  p=Path(v).expanduser()
  if not p.is_dir():return {"status":"error","message":"Directory non valida o non accessibile"}
  h=hashlib.sha256();count=total=0
  for f in sorted(p.rglob("*")):
   if f.is_file() and not f.is_symlink():
    try:
     if f.stat().st_size>20*1024*1024:continue
     h.update(str(f.relative_to(p)).encode())
     with f.open("rb") as stream:
      for chunk in iter(lambda:stream.read(65536),b""):h.update(chunk);total+=len(chunk)
     count+=1
     if count>=500:break
    except OSError:continue
  return {"status":"ok","message":f"{count} file · {total//1024} KB · SHA-256 {h.hexdigest()[:24]}…"}
 if k=="tls_check":
  host=v.replace("https://","").replace("http://","").split("/")[0].split(":")[0]
  if not host or len(host)>253 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for c in host):return {"status":"error","message":"Hostname non valido"}
  try:
   with socket.create_connection((host,443),timeout=5) as raw:
    with ssl.create_default_context().wrap_socket(raw,server_hostname=host) as conn:
     cert=conn.getpeercert();exp=datetime.datetime.strptime(cert["notAfter"],"%b %d %H:%M:%S %Y %Z").replace(tzinfo=datetime.timezone.utc);days=(exp-datetime.datetime.now(datetime.timezone.utc)).days
     return {"status":"ok","message":f"{host} · {conn.version()} · scadenza {exp:%d/%m/%Y} · {days} giorni"}
  except Exception as e:return {"status":"error","message":str(e)[:150]}
 return {"status":"error","message":"Azione non consentita"}
def run(flow):
 out=[]
 record("INFO","Avvio workflow",flow["name"])
 for i,n in enumerate(flow["nodes"],1):
  r=action(n);out.append({"step":i,"label":n["label"],**r});record("INFO" if r["status"]=="ok" else "WARN",n["label"],r["message"])
  if r["status"]!="ok":break
 record("INFO","Workflow terminato",str(len(out))+" passaggi")
 return out
def page():
 return r'''<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AutoSecFlow</title><style>
:root{--bg:#090e0d;--panel:#111b18;--line:#2b4038;--mint:#9be4c3;--lime:#c7ef83;--muted:#81938a;--text:#e8f1ec}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px Inter,system-ui}header{height:68px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 28px;background:#0c1411}.brand{display:flex;gap:13px;align-items:center;font-size:12px;font-weight:900;letter-spacing:.13em}.mark{width:38px;height:38px;border:1px solid var(--mint);color:var(--mint);display:grid;place-items:center;transform:rotate(45deg);font-size:22px}.brand small{display:block;color:var(--muted);font:9px ui-monospace;margin-top:4px}.live{font:9px ui-monospace;color:var(--lime)}.layout{display:grid;grid-template-columns:245px 1fr;min-height:calc(100vh - 68px)}aside{border-right:1px solid var(--line);padding:26px 18px;background:#0c1411}.eyebrow,.crumb{font:9px ui-monospace;color:var(--mint);letter-spacing:.2em}.side-title{font:28px Georgia;margin:10px 0 25px}.nav{display:grid;gap:7px}.nav button{background:transparent;text-align:left;border-color:transparent;color:#9aada5}.nav button.active,.nav button:hover{background:#17251f;border-color:#365044;color:var(--mint)}.note{margin-top:35px;border-top:1px solid var(--line);padding-top:17px;color:#71837a;font:10px/1.8 ui-monospace}main{padding:34px clamp(18px,4vw,54px)}h1{font:clamp(36px,5vw,58px)/.98 Georgia;margin:17px 0 8px}h1 span{color:var(--mint);font-style:italic}.intro{color:var(--muted);max-width:700px;line-height:1.6}.toolbar{display:flex;flex-wrap:wrap;gap:8px;margin:23px 0}button,input,select{font:inherit;color:var(--text);background:#121e19;border:1px solid #344b40;border-radius:4px;padding:10px 13px}button{cursor:pointer;font-size:10px;letter-spacing:.1em;font-weight:800}button:hover{border-color:var(--mint);color:var(--mint)}button.primary{background:var(--mint);border-color:var(--mint);color:#07120d}.grid{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(240px,.8fr);gap:16px;align-items:start}.panel{border:1px solid var(--line);background:linear-gradient(145deg,#121d19,#0c1411);padding:18px;margin-bottom:14px}.panelhead{display:flex;justify-content:space-between;gap:10px;margin-bottom:15px}.panelhead b{font:10px ui-monospace;letter-spacing:.12em}.panelhead span{font:9px ui-monospace;color:var(--muted)}.formrow{display:grid;gap:6px;margin:10px 0}.formrow label,.nodegrid label{font:9px ui-monospace;color:var(--muted);letter-spacing:.1em}.formrow input,.formrow select{width:100%}.node{position:relative;border:1px solid #344c40;background:#111c18;padding:14px;margin:0 0 23px 27px}.node:before{content:"";position:absolute;left:-28px;top:24px;width:27px;border-top:1px solid #638b77}.node:after{content:"";position:absolute;left:-15px;top:100%;height:24px;border-left:1px dashed #638b77}.node:last-child:after{display:none}.nodehead{display:flex;justify-content:space-between;align-items:center}.nodeid{font:9px ui-monospace;color:var(--mint)}.node-title{font:14px Georgia;margin-top:6px}.nodegrid{display:grid;grid-template-columns:1fr 1.3fr;gap:9px;margin-top:12px}.nodegrid label{display:grid;gap:5px}.nodegrid input,.nodegrid select{width:100%;font-size:11px;padding:9px}.remove{padding:5px 8px;color:#d09a82}.connector{position:absolute;left:-34px;top:18px;width:12px;height:12px;border:2px solid var(--mint);border-radius:50%;background:#0b1411}.stat{padding:15px;border:1px solid var(--line);margin:8px 0;background:#0b1411}.stat strong{display:block;font:26px Georgia;color:var(--mint)}.stat small{color:var(--muted);font:9px ui-monospace}.output,.logrow{font:10px/1.7 ui-monospace;color:#a8b9b0;white-space:pre-wrap}.output{max-height:260px;overflow:auto}.logrow{padding:10px 0;border-bottom:1px solid #263831}.logrow time{color:#71877c;margin-right:9px}.ok{color:var(--lime)}.error{color:#e99c84}.hidden{display:none!important}@media(max-width:850px){.layout{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid var(--line);padding:14px}.side-title,.note{display:none}.nav{display:flex;overflow:auto}.nav button{white-space:nowrap}.grid{grid-template-columns:1fr}}@media(max-width:520px){header{padding:0 14px}main{padding:22px 14px}.nodegrid{grid-template-columns:1fr}}
</style><body><header><div class="brand"><div class="mark">⌁</div><div>AUTOSECFLOW<small>LOCAL WORKFLOW ENGINE / DEFENSIVE OPS</small></div></div><div class="live">● ENGINE READY</div></header><div class="layout"><aside><div class="eyebrow">WORKSPACE / 01</div><div class="side-title">Flow<br>control.</div><nav class="nav"><button class="active" data-view="builder">01 · Workflow builder</button><button data-view="activity">02 · Activity stream</button><button data-view="library">03 · Action library</button></nav><div class="note">LOCAL-FIRST<br>READ-ONLY ACTIONS<br>NO ARBITRARY SHELL<br><br>ENGINE // ASF-01</div></aside><main><div class="crumb">AUTOMATION / VISUAL ORCHESTRATION</div><section id="builder"><h1>Build a <span>sequence.</span></h1><p class="intro">Collega controlli locali in un flusso ripetibile. Ogni nodo esegue un'azione difensiva in sola lettura; nessun comando shell arbitrario.</p><div class="toolbar"><button class="primary" id="run">▶ RUN WORKFLOW</button><button id="save">SAVE FLOW</button><button id="add">＋ ADD NODE</button><button id="reset">RESET</button></div><div class="grid"><div><div class="panel"><div class="panelhead"><b>01 / FLOW CONFIGURATION</b><span>SEQUENTIAL EXECUTION</span></div><div class="formrow"><label>WORKFLOW NAME</label><input id="flowname" value="Routine di controllo locale"></div><div class="formrow"><label>TRIGGER</label><select id="trigger"><option value="manual">Manuale · avvio su richiesta</option><option value="manual_confirm">Manuale · conferma prima dell'esecuzione</option></select></div></div><div class="panel"><div class="panelhead"><b>02 / NODE CANVAS</b><span id="nodecount">03 NODES</span></div><div id="nodes"></div></div></div><div><div class="panel"><div class="panelhead"><b>RUN OUTPUT</b><span id="runstate">STANDBY</span></div><div id="output" class="output">Nessuna esecuzione. Premi RUN WORKFLOW.</div></div><div class="stat"><strong id="savedcount">01</strong><small>SAVED WORKFLOW</small></div><div class="stat"><strong id="stepcount">03</strong><small>CONFIGURED NODES</small></div></div></div></section><section id="activity" class="hidden"><h1>Activity <span>stream.</span></h1><p class="intro">Registro locale delle esecuzioni e degli esiti dei singoli nodi.</p><div class="panel"><div class="panelhead"><b>EVENT JOURNAL</b><button id="refreshlogs">REFRESH</button></div><div id="logs"></div></div></section><section id="library" class="hidden"><h1>Action <span>library.</span></h1><p class="intro">Azioni disponibili nel motore locale. Le operazioni non modificano i file analizzati.</p><div class="panel"><b>SYSTEM SNAPSHOT</b><p class="intro">Hostname, sistema operativo, versione Python e spazio disco libero.</p></div><div class="panel"><b>DIRECTORY HASH</b><p class="intro">Impronta SHA-256 aggregata dei file leggibili. Limite 500 file e 20 MB per file.</p></div><div class="panel"><b>TLS CERTIFICATE CHECK</b><p class="intro">Controllo del certificato HTTPS di un hostname.</p></div><div class="panel"><b>LOG ENTRY</b><p class="intro">Aggiunge una nota al registro locale.</p></div></section></main></div>
<script>
var types={system_snapshot:"System snapshot",hash_directory:"Directory hash",tls_check:"TLS certificate check",log:"Log entry"};
var nodes=[{id:"n1",type:"system_snapshot",label:"Rileva stato sistema",value:""},{id:"n2",type:"hash_directory",label:"Verifica integrità cartella",value:"/home/jack0p000/Tools"},{id:"n3",type:"log",label:"Registra completamento",value:"Controllo completato"}];
function $(id){return document.getElementById(id)}function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function render(){var out="";nodes.forEach(function(n,i){out+='<div class="node"><i class="connector"></i><div class="nodehead"><span class="nodeid">NODE '+("0"+(i+1)).slice(-2)+' / '+esc(n.id)+'</span><button class="remove" data-remove="'+i+'">REMOVE</button></div><div class="node-title">'+esc(types[n.type])+'</div><div class="nodegrid"><label>NODE TYPE<select data-field="type" data-i="'+i+'">';Object.keys(types).forEach(function(k){out+='<option value="'+k+'" '+(n.type===k?"selected":"")+'>'+types[k]+'</option>'});out+='</select></label><label>DISPLAY NAME<input data-field="label" data-i="'+i+'" value="'+esc(n.label)+'"></label><label style="grid-column:1/-1">PARAMETER<input data-field="value" data-i="'+i+'" value="'+esc(n.value)+'" placeholder="Parametro opzionale"></label></div></div>'});$("nodes").innerHTML=out;$("nodecount").textContent=("0"+nodes.length).slice(-2)+" NODES";$("stepcount").textContent=nodes.length}
$("nodes").addEventListener("input",function(e){var i=+e.target.dataset.i;if(nodes[i])nodes[i][e.target.dataset.field]=e.target.value});
$("nodes").addEventListener("change",function(e){var i=+e.target.dataset.i;if(nodes[i]){nodes[i][e.target.dataset.field]=e.target.value;if(e.target.dataset.field==="type")render()}});
$("nodes").addEventListener("click",function(e){var i=+e.target.dataset.remove;if(Number.isInteger(i)&&nodes[i]){nodes.splice(i,1);render()}});
$("add").onclick=function(){if(nodes.length>=20)return alert("Massimo 20 nodi.");nodes.push({id:"n"+Date.now(),type:"log",label:"Nuova azione",value:""});render()};
$("reset").onclick=function(){if(confirm("Ripristinare il workflow di esempio?")){nodes=[{id:"n1",type:"system_snapshot",label:"Rileva stato sistema",value:""},{id:"n2",type:"hash_directory",label:"Verifica integrità cartella",value:"/home/jack0p000/Tools"},{id:"n3",type:"log",label:"Registra completamento",value:"Controllo completato"}];$("flowname").value="Routine di controllo locale";render()}};
function payload(){return {name:$("flowname").value.trim()||"Workflow senza nome",trigger:$("trigger").value,nodes:nodes}}
async function api(path,data){var r=await fetch(path,{method:data?"POST":"GET",headers:{"Content-Type":"application/json"},body:data?JSON.stringify(data):undefined});var j=await r.json();if(!r.ok)throw Error(j.error||"Errore richiesta");return j}
$("save").onclick=async function(){try{var r=await api("/api/save",payload());$("savedcount").textContent=r.count;$("runstate").textContent="SAVED"}catch(e){alert(e.message)}};
$("run").onclick=async function(){try{if(!confirm("Avviare il workflow? Le azioni sono in sola lettura."))return;$("runstate").textContent="RUNNING";$("output").textContent="Esecuzione in corso…";var r=await api("/api/run",payload());$("runstate").textContent=r.ok?"COMPLETE":"STOPPED";$("output").innerHTML=r.results.map(function(x){return '<div class="'+(x.status==="ok"?"ok":"error")+'">['+x.status.toUpperCase()+'] '+esc(x.step)+' · '+esc(x.label)+'<br>'+esc(x.message)+'</div>'}).join("")}catch(e){$("runstate").textContent="ERROR";$("output").textContent=e.message}};
async function logs(){try{var r=await api("/api/logs");$("logs").innerHTML=r.logs.map(function(x){return '<div class="logrow"><time>'+esc(x.time)+'</time><b class="'+(x.level==="WARN"?"error":"ok")+'">'+esc(x.level)+'</b> · '+esc(x.message)+'<br>'+esc(x.detail)+'</div>'}).join("")||"Nessun evento."}catch(e){$("logs").textContent=e.message}}
document.querySelectorAll(".nav button").forEach(function(b){b.onclick=function(){document.querySelectorAll(".nav button").forEach(function(x){x.classList.toggle("active",x===b)});["builder","activity","library"].forEach(function(v){$(v).classList.toggle("hidden",v!==b.dataset.view)});if(b.dataset.view==="activity")logs()}});
$("refreshlogs").onclick=logs;
async function init(){try{var r=await api("/api/state");if(r.workflow){$("flowname").value=r.workflow.name;$("trigger").value=r.workflow.trigger;nodes=r.workflow.nodes}$("savedcount").textContent=r.count}catch(e){}render()}init();
</script></body></html>'''
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def sendj(self,data,status=200):
  raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  p=urllib.parse.urlparse(self.path).path
  if p=="/":
   raw=page().encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw);return
  if p=="/api/state":
   a=load();self.sendj({"workflow":a[0] if a else DEFAULT,"count":len(a)});return
  if p=="/api/logs":
   try:a=[json.loads(x) for x in LOG.read_text().splitlines()[-80:]]
   except:a=[]
   self.sendj({"logs":list(reversed(a))});return
  self.sendj({"error":"Not found"},404)
 def do_POST(self):
  p=urllib.parse.urlparse(self.path).path
  if p not in ("/api/save","/api/run"):self.sendj({"error":"Not found"},404);return
  try:
   length=int(self.headers.get("Content-Length","0"))
   if length>100000:raise ValueError("Richiesta troppo grande")
   d=json.loads(self.rfile.read(length) or b"{}");name=str(d.get("name","Workflow"))[:100];nodes=d.get("nodes",[])
   if not isinstance(nodes,list) or not 1<=len(nodes)<=20:raise ValueError("Servono da 1 a 20 nodi")
   allowed={"system_snapshot","hash_directory","tls_check","log"};clean=[]
   for i,n in enumerate(nodes):
    if not isinstance(n,dict) or n.get("type") not in allowed:raise ValueError("Tipo nodo non consentito")
    clean.append({"id":str(n.get("id",i+1))[:30],"type":n["type"],"label":str(n.get("label",n["type"]))[:100],"value":str(n.get("value",""))[:500]})
   flow={"name":name,"trigger":"manual","nodes":clean}
   if p=="/api/save":
    with LOCK:
     a=load()
     if a:a[0]=flow
     else:a=[flow]
     tmp=STORE.with_suffix(".tmp");tmp.write_text(json.dumps(a,ensure_ascii=False,indent=2));tmp.replace(STORE)
    record("INFO","Workflow salvato",name);self.sendj({"ok":True,"count":len(a)});return
   if d.get("trigger") not in ("manual","manual_confirm"):raise ValueError("Trigger non supportato")
   out=run(flow);self.sendj({"ok":all(x["status"]=="ok" for x in out),"results":out});return
  except Exception as e:self.sendj({"error":str(e)[:220]},400)
def main():
 s=ThreadingHTTPServer(("127.0.0.1",8796),Handler);threading.Thread(target=s.serve_forever,daemon=True).start()
 try:
  import webbrowser;webbrowser.open("http://127.0.0.1:8796")
 except:pass
 print("AutoSecFlow GUI: http://127.0.0.1:8796")
 while True:time.sleep(1)
if __name__=="__main__":main()