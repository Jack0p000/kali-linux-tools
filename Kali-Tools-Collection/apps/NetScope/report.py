import sqlite3,os,html,sys
BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.path.join(BASE,"database","netscope.sqlite"); OUT=os.path.join(BASE,"reports"); os.makedirs(OUT,exist_ok=True)
c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
row=c.execute("SELECT id FROM scans ORDER BY id DESC LIMIT 1").fetchone() if len(sys.argv)<2 else (int(sys.argv[1]),)
sid=row[0]; s=c.execute("SELECT * FROM scans WHERE id=?",(sid,)).fetchone(); hs=c.execute("SELECT * FROM hosts WHERE scan_id=?",(sid,)).fetchall()
trs=[]
for h in hs:
 ps=c.execute("SELECT * FROM ports WHERE host_id=?",(h["id"],)).fetchall(); ports=", ".join(f'{p["port"]}/{p["protocol"]} {p["service"]}' for p in ps) or "-"
 trs.append(f'<tr><td>{html.escape(h["ip"])}</td><td>{html.escape(h["mac"] or "-")}</td><td>{html.escape(ports)}</td></tr>')
out=os.path.join(OUT,f"scan_{sid}.html")
open(out,"w").write(f'<!doctype html><html><head><meta charset="utf-8"><title>NetScope report</title><style>body{{font:14px system-ui;max-width:1000px;margin:40px auto}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}</style></head><body><h1>NetScope Report #{sid}</h1><p>Target: {html.escape(s["target"])}<br>Host: {s["host_count"]}<br>Durata: {s["duration"]:.1f}s</p><table><tr><th>IP</th><th>MAC</th><th>Porte/servizi</th></tr>{"".join(trs)}</table></body></html>')
print(out)
