
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'Desktop Remote Commander'
_ts_register(_TS_NAME)
_ts_publish(_TS_NAME, 'startup', {'pid': __import__('os').getpid()})
# --- ToolAuth integration ---
if '/home/jack0p000/ToolAuth' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolAuth')
from auth import login as _ta_login
_ta_login(_TS_NAME)
# --- end ToolAuth integration ---
# --- end ToolShare integration ---
#!/usr/bin/env python3

import subprocess

COMMAND = (
    "curl -fsSL "
    "https://raw.githubusercontent.com/wonderwhy-er/DesktopCommanderMCP/main/scripts/remote/remote-linux.sh "
    "| sh"
)

print("Avvio Desktop Remote Commander...")
print()

subprocess.run(
    COMMAND,
    shell=True,
    executable="/bin/bash"
)
