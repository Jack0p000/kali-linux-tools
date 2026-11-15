
from html import escape
CSS = r'''
:root{color-scheme:dark;--bg:#070d17;--surface:#0d1929;--surface2:#12243a;--line:#263e59;--text:#e9f2ff;--muted:#8da4bd;--blue:#55b8ff;--cyan:#57e0d5;--green:#57d6a5;--red:#ff8494;--shadow:0 22px 60px #0006}
*{box-sizing:border-box}html{min-height:100%;background:var(--bg);scroll-behavior:smooth}
body{margin:0;min-height:100vh;background:radial-gradient(ellipse at 15% -10%,#16487555,transparent 38%),radial-gradient(ellipse at 95% 8%,#0d646044,transparent 32%),linear-gradient(145deg,#070d17,#0a1524 55%,#08111e);color:var(--text);font:14px/1.6 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.app{min-height:100vh;display:grid;grid-template-columns:248px minmax(0,1fr)}
.rail{position:sticky;top:0;height:100vh;padding:25px 17px;background:#081321e8;border-right:1px solid #20364e;backdrop-filter:blur(18px);display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:12px;padding:3px 8px 27px;border-bottom:1px solid #1e3349}
.brand-mark{width:38px;height:38px;display:grid;place-items:center;border-radius:12px;background:linear-gradient(140deg,#1d9be8,#1b587f);box-shadow:0 8px 25px #168ee344;font-size:18px;font-weight:900}
.brand strong{display:block;font-size:13px;letter-spacing:.12em}.brand small{display:block;color:#7891aa;font-size:10px;letter-spacing:.12em;margin-top:2px}
.rail-label{margin:25px 9px 10px;color:#5e7893;font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase}
.nav{display:grid;gap:6px}.nav a{display:flex;align-items:center;gap:11px;padding:10px 11px;border:1px solid transparent;border-radius:10px;color:#a8bfd6;text-decoration:none;font-size:12px;transition:.18s}
.nav a:hover,.nav a.active{background:linear-gradient(100deg,#143450,#10253a);border-color:#2b5271;color:#eaf6ff}.nav .ico{width:19px;text-align:center;color:#69c9f7;font-size:15px}
.rail-foot{margin-top:auto;padding:14px 11px;border:1px solid #1d3b50;border-radius:12px;background:#0b1a29}.rail-foot b{display:block;font-size:11px;color:#cfe6f9}.rail-foot span{font-size:10px;color:#7992aa}
.main{min-width:0;padding:28px clamp(18px,4vw,54px) 55px}.topbar{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:3px 0 21px;border-bottom:1px solid #1d344c}
.crumb{font:10px ui-monospace,monospace;letter-spacing:.13em;text-transform:uppercase;color:#7894af}
.live{display:inline-flex;align-items:center;gap:8px;padding:7px 11px;border:1px solid #285744;border-radius:999px;background:#0d2b25;color:#8ce4bd;font:10px ui-monospace,monospace;letter-spacing:.1em}
.live:before{content:"";width:7px;height:7px;border-radius:50%;background:#5de1a7;box-shadow:0 0 12px #5de1a7}
.hero{padding:32px 0 25px}.eyebrow{color:#5dc9ee;font:10px ui-monospace,monospace;letter-spacing:.2em;text-transform:uppercase;margin-bottom:10px}
h1{margin:0;font-size:clamp(29px,4vw,46px);line-height:1.05;letter-spacing:-.055em;font-weight:850}.hero p{margin:12px 0 0;color:var(--muted);font-size:13px;max-width:650px}
.content{display:grid;grid-template-columns:minmax(0,1fr);gap:16px}
.panel{position:relative;min-width:0;padding:24px;border:1px solid #28425d;border-radius:17px;background:linear-gradient(145deg,#11243aee,#0c1929f5);box-shadow:var(--shadow),inset 0 1px #ffffff0a;overflow:hidden}
.panel:before{content:"";position:absolute;left:8%;right:8%;top:0;height:1px;background:linear-gradient(90deg,transparent,#60cfff99,transparent)}
.panel h2,.panel h3{margin:0 0 13px;font-size:14px;letter-spacing:-.02em}.panel p{color:#9db2c8}
form{display:flex;flex-wrap:wrap;align-items:center;gap:9px}
input,select,textarea{min-width:210px;max-width:100%;padding:13px 15px;border:1px solid #35536f;border-radius:10px;background:#081522;color:#e9f2ff;font:inherit;outline:none}
input:focus,select:focus,textarea:focus{border-color:#55b8ff;box-shadow:0 0 0 3px #55b8ff22}input::placeholder{color:#6e879f}
button{padding:12px 17px;border:1px solid #54baff88;border-radius:10px;background:linear-gradient(120deg,#168bd8,#2369b4);color:#fff;font:750 11px/1.2 Inter,system-ui,sans-serif;letter-spacing:.07em;cursor:pointer;box-shadow:0 8px 22px #087bd322;transition:transform .18s,filter .18s}
button:hover{transform:translateY(-1px);filter:brightness(1.13)}button:active{transform:translateY(0)}a{color:#70caff}
pre{white-space:pre-wrap;overflow-wrap:anywhere;max-width:100%;margin:0;padding:19px;border:1px solid #263e58;border-radius:12px;background:#07111e;color:#b8d4ec;font:12px/1.7 ui-monospace,SFMono-Regular,monospace;overflow:auto}
table{width:100%;border-collapse:separate;border-spacing:0;border:1px solid #263e58;border-radius:12px;overflow:hidden}
th,td{padding:12px 14px;text-align:left;border-bottom:1px solid #21374d}th{background:#142a41;color:#9fc3df;font:10px ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase}
td{background:#0b1928;color:#d5e5f4}tr:last-child td{border-bottom:0}.muted{color:#829bb3}
footer{margin-top:24px;padding-top:17px;border-top:1px solid #1e3348;color:#647f99;font:10px ui-monospace,monospace;letter-spacing:.08em}
@media(max-width:780px){.app{grid-template-columns:1fr}.rail{position:relative;height:auto;padding:12px 15px;border-right:0;border-bottom:1px solid #20364e}.brand{padding:2px 4px 11px}.rail-label,.rail-foot{display:none}.nav{display:flex;overflow:auto;padding-top:10px}.nav a{white-space:nowrap;padding:8px 10px}.main{padding:18px 15px 35px}.hero{padding:25px 0 19px}.panel{padding:17px}.topbar{padding-bottom:14px}}
@media(max-width:430px){.topbar{align-items:flex-start;flex-direction:column}.nav a{font-size:11px}.nav .ico{display:none}form{display:grid;grid-template-columns:1fr}input,select,textarea,form button{width:100%;min-width:0}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;transition-duration:.01ms!important}}
'''
def render_tool_page(title, body):
    safe=escape(str(title))
    return f'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#080f1b"><title>{safe} · KALI TOOLKIT</title><style>{CSS}</style></head><body><div class="app">
<aside class="rail"><div class="brand"><div class="brand-mark">K</div><div><strong>KALI TOOLKIT</strong><small>SECURITY WORKSPACE</small></div></div><div class="rail-label">Workspace</div>
<nav class="nav"><a class="active" href="#overview"><span class="ico">◈</span> Panoramica</a><a href="#workspace"><span class="ico">▣</span> Console tool</a><a href="#output"><span class="ico">⌁</span> Risultati</a><a href="http://127.0.0.1:8790/"><span class="ico">⌂</span> Command Center</a></nav>
<div class="rail-foot"><b>SESSIONE LOCALE</b><span>Servizio eseguito su questo dispositivo</span></div></aside>
<main class="main"><header class="topbar"><div class="crumb">KALI TOOLKIT / {safe.upper()}</div><div class="live">SERVIZIO LOCALE</div></header>
<section class="hero" id="overview"><div class="eyebrow">TOOL INTERFACE · 01</div><h1>{safe}</h1><p>Workspace operativo per {safe}. Inserisci i parametri e avvia l'operazione; i risultati vengono mostrati qui sotto.</p></section>
<section class="content"><div class="panel" id="workspace"><h2>⌘ &nbsp; Console operativa</h2>{body}</div></section>
<footer id="output">KALI TOOLKIT · LOCAL WORKSPACE · {safe.upper()}</footer></main></div></body></html>'''
