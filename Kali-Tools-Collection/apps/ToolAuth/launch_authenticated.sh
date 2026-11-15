#!/bin/bash
set -u

TOOL="$1"
TARGET="$2"
MODE="${3:-terminal}"
AUTH="/home/jack0p000/ToolAuth/auth.py"

if [ ! -f "$AUTH" ]; then
  echo "[AUTH] modulo mancante: $AUTH"
  read -r -p "Premi INVIO per chiudere..."
  exit 1
fi

export TOOL_NAME="$TOOL"

eval "$(python3 - <<'PY'
import os,sys
sys.path.insert(0,'/home/jack0p000/ToolAuth')
from auth import login
tool=os.environ.get('TOOL_NAME','Tool')
login(tool)
for k in ('TOOL_AUTH_USER','TOOL_AUTH_PASS','TOOL_AUTH_TOKEN','TOOL_AUTH_TOOL'):
    v=os.environ.get(k,'').replace('\\','\\\\').replace('"','\\"')
    print(f'export {k}="{v}"')
PY
)"

echo
echo "=== $TOOL ==="
echo "[AUTH_OK] login automatico: $TOOL_AUTH_USER"
echo "[START] avvio $TARGET"
echo

if [ "$MODE" = "gui" ]; then
  bash "$TARGET"
else
  bash "$TARGET"
fi

STATUS=$?
echo
echo "=== $TOOL terminato (codice $STATUS) ==="
echo "Il terminale resta aperto."
read -r -p "Premi INVIO per chiudere questa finestra..."
exit "$STATUS"
