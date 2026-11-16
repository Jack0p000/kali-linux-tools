#!/usr/bin/env python3
import json, math, os, subprocess, threading, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOOL = "SatelliteIntel"
PORT = 8791
Celestrak = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
Copernicus = "https://catalogue.dataspace.copernicus.eu/odata/v1.0/Products"

# --- ToolShare integration ---
try:
    import sys
    if "/home/jack0p000/ToolShareHub" not in sys.path:
        sys.path.insert(0, "/home/jack0p000/ToolShareHub")
    from toolshare import register as _ts_register, publish as _ts_publish
    _ts_register(TOOL)
    _ts_publish(TOOL, "startup", {"pid": os.getpid()})
except Exception:
    _ts_publish = lambda *a, **k: None

# --- ToolAuth integration ---
try:
    import sys
    if "/home/jack0p000/ToolAuth" not in sys.path:
        sys.path.insert(0, "/home/jack0p000/ToolAuth")
    from auth import login as _ta_login
    _ta_login(TOOL)
except Exception:
    pass

try:
    from sgp4.api import Satrec, jday
    SGP4_OK = True
except Exception:
    SGP4_OK = False

_CACHE = {"tle": None, "tle_ts": 0}

def http_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "SatelliteIntel/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def http_text(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "SatelliteIntel/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def tle_catalog():
    if _CACHE["tle"] and time.time() - _CACHE["tle_ts"] < 1800:
        return _CACHE["tle"]
    raw = http_text(Celestrak)
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    out = []
    for i in range(0, len(lines) - 2, 3):
        if lines[i+1].startswith("1 ") and lines[i+2].startswith("2 "):
            out.append({"name": lines[i], "l1": lines[i+1], "l2": lines[i+2]})
    _CACHE["tle"], _CACHE["tle_ts"] = out, time.time()
    return out

def orbital_position(item, when):
    if not SGP4_OK:
        return None
    sat = Satrec.twoline2rv(item["l1"], item["l2"])
    jd, fr = jday(when.year, when.month, when.day, when.hour,
                  when.minute, when.second + when.microsecond/1e6)
    e, r, v = sat.sgp4(jd, fr)
    if e != 0:
        return None
    x, y, z = r
    # ECI km -> geocentric lon/lat approximation, suitable for visualization.
    lon = math.degrees(math.atan2(y, x))
    lat = math.degrees(math.atan2(z, math.sqrt(x*x + y*y)))
    alt = math.sqrt(x*x + y*y + z*z) - 6378.137
    return {"lat": round(lat, 4), "lon": round(lon, 4), "alt_km": round(alt, 1)}

def passes_for(item, lat0, lon0, start, hours=12, step_seconds=60):
    if not SGP4_OK:
        return []
    hits = []
    last = None
    t = start
    end = start + timedelta(hours=hours)
    while t <= end:
        p = orbital_position(item, t)
        if p:
            # Great-circle angular separation of subsatellite point.
            a = math.radians(lat0); b = math.radians(p["lat"])
            dlon = math.radians(p["lon"] - lon0)
            c = math.sin(a)*math.sin(b) + math.cos(a)*math.cos(b)*math.cos(dlon)
            c = max(-1, min(1, c))
            distance_deg = math.degrees(math.acos(c))
            if distance_deg <= 5.0 and (last is None or last > 5.0):
                hits.append({"utc": t.isoformat().replace("+00:00","Z"),
                             "satellite": item["name"], "distance_deg": round(distance_deg,2)})
            last = distance_deg
        t += timedelta(seconds=step_seconds)
    return hits

def sentinel_search(lat, lon, days=30, cloud=None, limit=20):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(1, min(days, 365)))
    params = {
        "$filter": (
            "Collection/Name eq 'SENTINEL-2' and "
            "ContentDate/Start ge " + start.isoformat() + " and "
            "ContentDate/Start le " + end.isoformat()
        ),
        "$top": str(limit),
        "$orderby": "ContentDate/Start desc"
    }
    # Copernicus OData exposes metadata; cloud filtering varies by product.
    url = Copernicus + "?" + urllib.parse.urlencode(params)
    try:
        data = http_json(url)
        results = []
        for p in data.get("value", []):
            results.append({
                "name": p.get("Name"),
                "id": p.get("Id"),
                "start": p.get("ContentDate", {}).get("Start"),
                "orbit": p.get("S3Path", ""),
                "url": p.get("Online", False)
            })
        return results
    except Exception as e:
        return [{"error": "Copernicus query failed", "detail": str(e)}]

def make_page():
    return r"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SatelliteIntel</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#070b12;color:#d9e2ef;font:14px Inter,system-ui,sans-serif}
.top{height:64px;border-bottom:1px solid #1b2636;display:flex;align-items:center;padding:0 22px;background:#0b111b}
.logo{font-weight:800;letter-spacing:2px;color:#8ed0ff}.sub{margin-left:14px;color:#607089;font-size:11px;letter-spacing:1px}
main{display:grid;grid-template-columns:340px 1fr;min-height:calc(100vh - 64px)}
.side{border-right:1px solid #1b2636;padding:20px;background:#09101a}.panel{border:1px solid #1c2b3d;background:#0d1622;padding:15px;margin-bottom:14px}
h3{margin:0 0 12px;font-size:12px;letter-spacing:1.5px;color:#86a8c8}
label{display:block;color:#71849b;font-size:11px;margin:10px 0 5px}
input,select{width:100%;background:#080e16;border:1px solid #25364c;color:#d9e2ef;padding:9px;border-radius:4px}
button{width:100%;margin-top:12px;padding:10px;background:#102c43;color:#9bd7ff;border:1px solid #2a6a92;border-radius:4px;font-weight:700;cursor:pointer}
button:hover{background:#153d59}.status{font-size:11px;color:#71849b;margin-top:10px;min-height:16px}
.content{padding:20px;display:grid;grid-template-rows:auto 1fr;gap:14px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.card{border:1px solid #1b2a3c;background:#0c1520;padding:14px}.n{font-size:22px;color:#b9e2ff;font-weight:700}.k{font-size:10px;color:#647992;letter-spacing:1px;margin-top:3px}
.map{position:relative;min-height:560px;border:1px solid #1b2a3c;background:#05090e;overflow:hidden}
#map{width:100%;height:100%;min-height:560px}.results{position:absolute;right:12px;top:12px;width:350px;max-height:calc(100% - 24px);overflow:auto;background:rgba(7,12,19,.93);border:1px solid #24374e;padding:12px;z-index:5}
.item{border-bottom:1px solid #1b2636;padding:9px 0}.item:last-child{border:0}.title{color:#a8d9ff;font-weight:700;font-size:12px}.meta{color:#71849b;font-size:10px;margin-top:4px}
.dot{position:absolute;width:8px;height:8px;border-radius:50%;background:#6ed6ff;box-shadow:0 0 14px #6ed6ff;transform:translate(-50%,-50%);z-index:3}
.notice{font-size:11px;color:#6f8299;line-height:1.5}
@media(max-width:900px){main{grid-template-columns:1fr}.side{border-right:0;border-bottom:1px solid #1b2636}.cards{grid-template-columns:repeat(2,1fr)}}
</style>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
</head>
<body>
<div class="top"><div class="logo">SATELLITEINTEL</div><div class="sub">EARTH OBSERVATION / ORBITAL DATA</div></div>
<main>
<section class="side">
<div class="panel">
<h3>OBSERVATION TARGET</h3>
<label>LATITUDE</label><input id="lat" type="number" step="0.0001" value="45.55">
<label>LONGITUDE</label><input id="lon" type="number" step="0.0001" value="11.88">
<label>TIME WINDOW</label><select id="hours"><option value="6">6 HOURS</option><option value="12" selected>12 HOURS</option><option value="24">24 HOURS</option></select>
<button onclick="runOrbit()">ANALYZE ORBITS</button>
<div id="orbitStatus" class="status"></div>
</div>
<div class="panel">
<h3>SENTINEL CATALOG</h3>
<label>LOOKBACK DAYS</label><input id="days" type="number" min="1" max="365" value="30">
<button onclick="runSentinel()">SEARCH SENTINEL-2</button>
<div id="sentinelStatus" class="status"></div>
</div>
<div class="panel">
<h3>DATA SOURCES</h3>
<div class="notice">CelesTrak · public orbital elements<br>Copernicus Data Space · Sentinel metadata<br>Local SGP4 propagation · no person tracking</div>
</div>
</section>
<section class="content">
<div class="cards">
<div class="card"><div class="n" id="satCount">—</div><div class="k">ACTIVE TLE OBJECTS</div></div>
<div class="card"><div class="n" id="passCount">—</div><div class="k">NEAR PASSES</div></div>
<div class="card"><div class="n" id="sceneCount">—</div><div class="k">SENTINEL SCENES</div></div>
<div class="card"><div class="n">SGP4</div><div class="k">ORBIT ENGINE</div></div>
</div>
<div class="map"><div id="map"></div><div class="results" id="results"><div class="notice">Imposta coordinate e avvia un'analisi.</div></div></div>
</section>
</main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map=L.map('map').setView([45.55,11.88],7);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:18}).addTo(map);
let layer=L.layerGroup().addTo(map);
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function runOrbit(){
 const lat=+document.getElementById('lat').value,lon=+document.getElementById('lon').value,hours=+document.getElementById('hours').value;
 const st=document.getElementById('orbitStatus');st.textContent='Scaricamento TLE e propagazione...';
 const r=await fetch('/api/orbits?lat='+encodeURIComponent(lat)+'&lon='+encodeURIComponent(lon)+'&hours='+hours);const d=await r.json();
 document.getElementById('satCount').textContent=d.satellites;
 document.getElementById('passCount').textContent=d.passes.length;
 layer.clearLayers();L.marker([lat,lon]).addTo(layer).bindPopup('Target');
 const rows=d.passes.map(x=>'<div class="item"><div class="title">'+esc(x.satellite)+'</div><div class="meta">'+esc(x.utc)+' · '+x.distance_deg+'° dal target</div></div>').join('');
 document.getElementById('results').innerHTML=rows||'<div class="notice">Nessun passaggio entro 5° nel periodo selezionato.</div>';
 d.positions.slice(0,60).forEach(p=>L.circleMarker([p.lat,p.lon],{radius:3,weight:1,fillOpacity:.7}).bindTooltip(esc(p.name)).addTo(layer));
 st.textContent='Analisi completata · '+d.satellites+' oggetti';
}
async function runSentinel(){
 const days=+document.getElementById('days').value,st=document.getElementById('sentinelStatus');st.textContent='Interrogazione catalogo Copernicus...';
 const r=await fetch('/api/sentinel?days='+days);const d=await r.json();
 document.getElementById('sceneCount').textContent=d.results.filter(x=>!x.error).length;
 const rows=d.results.map(x=>x.error?'<div class="item"><div class="title">Errore Copernicus</div><div class="meta">'+esc(x.detail)+'</div></div>':'<div class="item"><div class="title">'+esc(x.name)+'</div><div class="meta">'+esc(x.start||'data n/d')+'</div></div>').join('');
 document.getElementById('results').innerHTML=rows||'<div class="notice">Nessun prodotto trovato.</div>';
 st.textContent='Catalogo aggiornato';
}
</script>
</body></html>"""

def json_response(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_GET(self):
        u=urllib.parse.urlparse(self.path)
        try:
            if u.path == "/":
                body=make_page(); ctype="text/html; charset=utf-8"
            elif u.path == "/api/orbits":
                q=urllib.parse.parse_qs(u.query)
                lat=float(q.get("lat",["45.55"])[0]); lon=float(q.get("lon",["11.88"])[0])
                hours=min(24,max(1,int(q.get("hours",["12"])[0])))
                cat=tle_catalog()
                now=datetime.now(timezone.utc)
                positions=[]
                for item in cat[:300]:
                    p=orbital_position(item,now)
                    if p: positions.append({"name":item["name"],**p})
                passes=[]
                for item in cat[:120]:
                    passes.extend(passes_for(item,lat,lon,now,hours,120))
                    if len(passes)>=30: break
                passes.sort(key=lambda x:x["utc"])
                body=json_response({"satellites":len(cat),"positions":positions,"passes":passes});ctype="application/json"
            elif u.path == "/api/sentinel":
                q=urllib.parse.parse_qs(u.query); days=int(q.get("days",["30"])[0])
                body=json_response({"results":sentinel_search(45.55,11.88,days)});ctype="application/json"
            else:
                self.send_response(404);self.end_headers();return
            self.send_response(200);self.send_header("Content-Type",ctype);self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(body)
        except Exception as e:
            body=json_response({"error":str(e)});self.send_response(500);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(body)

def main():
    srv=ThreadingHTTPServer(("127.0.0.1",PORT),Handler)
    try:
        subprocess.Popen(["google-chrome",f"http://127.0.0.1:{PORT}"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception:
        pass
    print(f"SatelliteIntel GUI: http://127.0.0.1:{PORT}")
    _ts_publish(TOOL,"ready",{"port":PORT,"sgp4":SGP4_OK})
    srv.serve_forever()

if __name__=="__main__":
    main()
