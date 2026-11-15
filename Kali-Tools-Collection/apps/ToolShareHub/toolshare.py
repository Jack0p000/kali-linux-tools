#!/usr/bin/env python3
import json, os, urllib.parse, urllib.request, subprocess, sys
from pathlib import Path
BASE=Path('/home/jack0p000/ToolShareHub'); URL='http://127.0.0.1:8799'
BASE.mkdir(parents=True,exist_ok=True)
def _post(path,payload):
    try:
        raw=json.dumps(payload,ensure_ascii=False).encode(); req=urllib.request.Request(URL+path,data=raw,headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=1.2) as r:return json.loads(r.read().decode())
    except Exception:return {'ok':False}
def _get(path):
    try:
        with urllib.request.urlopen(URL+path,timeout=1.2) as r:return json.loads(r.read().decode())
    except Exception:return {'ok':False}
def start_hub():
    try:urllib.request.urlopen(URL+'/api/health',timeout=.25).close();return True
    except Exception:pass
    try:
        subprocess.Popen([sys.executable,str(BASE/'hub.py')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        return True
    except Exception:return False
def register(name,version='1.0'):
    os.environ['TOOLSHARE_TOOL']=name; start_hub(); return _post('/api/register',{'name':name,'version':version,'pid':os.getpid()})
def publish(tool,event,data=None):return _post('/api/event',{'tool':tool,'event':event,'data':data or {}})
def recent(limit=20,tool=None):
    q=f'/api/events?limit={int(limit)}'; q += ('&tool='+urllib.parse.quote(tool)) if tool else ''; return _get(q)
def context(limit=20):return recent(limit)
def send(target,message,data=None):return _post('/api/message',{'from':os.getenv('TOOLSHARE_TOOL','unknown'),'to':target,'message':message,'data':data or {}})
