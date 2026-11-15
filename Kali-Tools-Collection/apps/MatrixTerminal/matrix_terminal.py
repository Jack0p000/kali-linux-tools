
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'Matrix Terminal'
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
# MATRIX TERMINAL — animazione decorativa continua
# Avvio: python3 matrix_terminal.py
# Uscita: CTRL+C

import random
import shutil
import sys
import time

GREEN = "\033[38;5;46m"
BRIGHT_GREEN = "\033[1;38;5;82m"
DIM_GREEN = "\033[38;5;28m"
RESET = "\033[0m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

COMMANDS = [
    "sudo systemctl status network.service",
    "ip addr show dev wlan0",
    "ping -c 4 127.0.0.1",
    "python3 main.py --verbose",
    "grep -R 'access' ./logs/",
    "find /var/log -type f",
    "journalctl -n 20 --no-pager",
    "ps aux | grep python",
    "git status --short",
    "ls -lah /home/user/",
    "echo 'initializing sequence...'",
    "loading modules .......... [ OK ]",
    "checking system .......... [ OK ]",
    "establishing connection .. [ OK ]",
    "decrypting buffer ........ [ OK ]",
    "scanning data stream ..... [ OK ]",
    "ACCESS NODE: 127.0.0.1",
    "STATUS: RUNNING",
]

PREFIXES = ("root@matrix:~# ", "system@node:~$ ", "operator@mainframe:~# ", "")

def type_fast(text, color):
    """Scrive a blocchi rapidi, lasciando tutte le righe nel normale scroll del terminale."""
    pos = 0
    while pos < len(text):
        amount = random.randint(2, 8)
        sys.stdout.write(color + text[pos:pos + amount] + RESET)
        sys.stdout.flush()
        pos += amount
        time.sleep(random.uniform(0.0005, 0.0025))

def main():
    sys.stdout.write(HIDE_CURSOR + BRIGHT_GREEN + "MATRIX STREAM // INITIALIZED\n" + RESET)
    sys.stdout.flush()

    try:
        while True:
            prefix = random.choice(PREFIXES)
            command = random.choice(COMMANDS)
            type_fast(prefix, DIM_GREEN)
            type_fast(command, random.choice((GREEN, GREEN, BRIGHT_GREEN)))
            sys.stdout.write("\n")
            sys.stdout.flush()

            if random.random() < 0.32:
                result = random.choice((
                    "[ OK ]  MODULE LOADED",
                    "[ 200 ] CONNECTION ESTABLISHED",
                    "0x" + "".join(random.choice("0123456789ABCDEF") for _ in range(12)),
                    "PROCESS COMPLETE",
                    "BUFFER READY",
                    ">> EXECUTED",
                    "DATA STREAM ACTIVE",
                ))
                type_fast("    " + result, DIM_GREEN)
                sys.stdout.write("\n")
                sys.stdout.flush()

            # Pausa minima tra una riga e l'altra: il flusso resta molto rapido.
            time.sleep(random.uniform(0.001, 0.008))

    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + SHOW_CURSOR + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
