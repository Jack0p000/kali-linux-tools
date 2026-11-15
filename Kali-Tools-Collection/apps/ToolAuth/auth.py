#!/usr/bin/env python3
import os, json, secrets, getpass, hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parent; CREDS=BASE/'credentials.json'
BASE.mkdir(parents=True,exist_ok=True)
try: os.chmod(BASE,0o700)
except: pass
def _hash(v): return hashlib.sha256(v.encode()).hexdigest()
def ensure_credentials():
    if CREDS.exists():
        try:
            d=json.loads(CREDS.read_text())
            if d.get('username') and d.get('password_hash') and d.get('password'): return d
        except Exception: pass
    print('\n=== TOOL AUTH — prima configurazione ===')
    username=input('Username comune: ').strip()
    while not username: username=input('Username comune: ').strip()
    password=getpass.getpass('Password comune: ')
    while not password: password=getpass.getpass('Password comune: ')
    d={'username':username,'password':password,'password_hash':_hash(password),'version':1}
    CREDS.write_text(json.dumps(d,ensure_ascii=False,indent=2))
    try: os.chmod(CREDS,0o600)
    except: pass
    print('[OK] Credenziali comuni salvate.\n')
    return d
def login(tool):
    d=ensure_credentials(); os.environ['TOOL_AUTH_USER']=d['username']; os.environ['TOOL_AUTH_PASS']=d['password']; os.environ['TOOL_AUTH_TOKEN']=secrets.token_hex(16); os.environ['TOOL_AUTH_TOOL']=tool; return True
if __name__=='__main__': login(os.environ.get('TOOL_NAME','Tool')); print('[AUTH_OK] login automatico per',os.environ.get('TOOL_NAME','Tool'))
