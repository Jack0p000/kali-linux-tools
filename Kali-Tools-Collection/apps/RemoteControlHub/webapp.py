
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'RemoteControlHub Web'
_ts_register(_TS_NAME)
_ts_publish(_TS_NAME, 'startup', {'pid': __import__('os').getpid()})
# --- ToolAuth integration ---
if '/home/jack0p000/ToolAuth' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolAuth')
from auth import login as _ta_login
_ta_login(_TS_NAME)
# --- end ToolAuth integration ---
# --- end ToolShare integration ---
from flask import Flask, render_template, request, jsonify
from remotehub import scan, connection_command, log
from pathlib import Path
import subprocess, shlex, os, socket
from tvremote import TVRemoteManager

app = Flask(__name__)
BASE = Path(__file__).resolve().parent
tv = TVRemoteManager()

def start_scrcpy(serial, tv_mode=False):
    """Avvia scrcpy in modo ottimizzato per il dispositivo autorizzato."""
    cmd = [
        "scrcpy",
        "--serial", serial,
        "--mouse=sdk",
        "--keyboard=sdk",
    ]

    if tv_mode:
        cmd += [
            "--video-codec=h264",
            "--video-bit-rate=4M",
            "--max-size=1280",
            "--max-fps=60",
            "--no-audio",
            "--stay-awake",
        ]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "host": socket.gethostname(),
        "port": int(os.getenv("RCH_PORT", "8080")),
        "bind": "0.0.0.0"
    })

@app.post("/api/scan")
def api_scan():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    try:
        result = scan(target)
        result["android_tv"] = any(
            p["port"] == 6466 and p["state"] == "open" for p in result["ports"]
        ) or any(
            p["port"] == 8008 and p["state"] == "open" for p in result["ports"]
        )
        return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Scansione scaduta"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.post("/api/command")
def api_command():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    method = str(data.get("method", "")).lower()

    if method not in {"ssh", "rdp", "vnc", "adb", "winrm"}:
        return jsonify({"error": "Metodo non supportato"}), 400

    cmd = connection_command(target, method)
    return jsonify({
        "command": cmd,
        "note": "Il client viene eseguito su Kali. Inserisci le credenziali del dispositivo quando richiesto; nessuna credenziale viene salvata."
    })

@app.post("/api/adb/connect")
def api_adb_connect():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()

    if not target:
        return jsonify({"error": "Target mancante"}), 400

    try:
        r = subprocess.run(
            ["adb", "connect", f"{target}:5555"],
            capture_output=True,
            text=True,
            timeout=10
        )
        msg = r.stdout.strip() or r.stderr.strip() or "Nessuna risposta da ADB"
        ok = r.returncode == 0 and (
            "connected to" in msg.lower() or
            "already connected" in msg.lower()
        )

        return jsonify({"ok": ok, "message": msg}), (200 if ok else 502)

    except FileNotFoundError:
        return jsonify({"error": "ADB non installato su Kali"}), 404
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout durante adb connect"}), 504

@app.post("/api/adb/mirror")
def api_adb_mirror():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()

    if not target:
        return jsonify({"error": "Target mancante"}), 400

    serial = f"{target}:5555"

    try:
        connect = subprocess.run(
            ["adb", "connect", serial],
            capture_output=True,
            text=True,
            timeout=10
        )

        connect_msg = (
            connect.stdout.strip() or
            connect.stderr.strip() or
            "Nessuna risposta da ADB"
        )

        if connect.returncode != 0 or not (
            "connected to" in connect_msg.lower() or
            "already connected" in connect_msg.lower()
        ):
            return jsonify({
                "ok": False,
                "message": f"Connessione ADB fallita: {connect_msg}"
            }), 502

        check = subprocess.run(
            ["adb", "-s", serial, "get-state"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if check.returncode != 0 or check.stdout.strip() != "device":
            return jsonify({
                "ok": False,
                "message": f"ADB connesso ma dispositivo non pronto: {check.stdout.strip() or check.stderr.strip()}"
            }), 502

        log(f"adb mirror {serial}")
        start_scrcpy(serial, tv_mode=False)

        return jsonify({
            "ok": True,
            "message": f"ADB connesso a {serial}. Mirroring avviato.",
            "target": serial
        })

    except FileNotFoundError as e:
        missing = e.filename or "comando"
        return jsonify({"error": f"{missing} non installato su Kali"}), 404
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout durante la connessione ADB"}), 504
    except Exception as e:
        return jsonify({"error": f"Avvio mirroring fallito: {e}"}), 500

@app.post("/api/tv/mirror")
def api_tv_mirror():
    """Mirror TV Android autorizzate via ADB wireless + scrcpy."""
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()

    if not target:
        return jsonify({"error": "Target mancante"}), 400

    serial = f"{target}:5555"

    try:
        connect = subprocess.run(
            ["adb", "connect", serial],
            capture_output=True,
            text=True,
            timeout=10
        )
        msg = connect.stdout.strip() or connect.stderr.strip() or "Nessuna risposta da ADB"

        if connect.returncode != 0 or not (
            "connected to" in msg.lower() or
            "already connected" in msg.lower()
        ):
            return jsonify({
                "ok": False,
                "message": f"ADB non disponibile sulla TV: {msg}"
            }), 502

        check = subprocess.run(
            ["adb", "-s", serial, "get-state"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if check.returncode != 0 or check.stdout.strip() != "device":
            detail = check.stdout.strip() or check.stderr.strip() or "stato ADB non pronto"
            return jsonify({
                "ok": False,
                "message": f"TV raggiunta ma ADB non autorizzato: {detail}"
            }), 502

        log(f"android tv mirror {serial}")

        start_scrcpy(serial, tv_mode=True)

        return jsonify({
            "ok": True,
            "target": serial,
            "message": "Mirroring TV avviato con profilo a bassa latenza.",
            "profile": {
                "codec": "h264",
                "bitrate": "4M",
                "max_size": 1280,
                "max_fps": 60,
                "audio": False
            }
        })

    except FileNotFoundError as e:
        missing = e.filename or "comando"
        return jsonify({"error": f"{missing} non installato su Kali"}), 404
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout durante ADB/scrcpy"}), 504
    except Exception as e:
        return jsonify({"error": f"Mirroring TV fallito: {type(e).__name__}: {e}"}), 500

@app.post("/api/tv/pair/start")
def tv_pair_start():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    if not target:
        return jsonify({"error": "Target mancante"}), 400
    try:
        token = tv.start_pairing(target)
        log(f"android tv pairing start {target}")
        return jsonify({
            "ok": True,
            "token": token,
            "message": "Pairing avviato. Guarda la TV: dovrebbe mostrare un codice di 6 caratteri."
        })
    except Exception as e:
        return jsonify({"ok": False, "error": f"Avvio pairing TV fallito: {type(e).__name__}: {e}"}), 502

@app.post("/api/tv/pair/finish")
def tv_pair_finish():
    data = request.get_json(silent=True) or {}
    token = str(data.get("token", "")).strip()
    code = str(data.get("code", "")).strip().upper()
    if not token or not code:
        return jsonify({"error": "Token o codice mancanti"}), 400
    try:
        tv.finish_pairing(token, code)
        log("android tv pairing completed")
        return jsonify({"ok": True, "message": "TV associata a RemoteControlHub."})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Pairing fallito: {type(e).__name__}: {e}"}), 502

@app.post("/api/tv/mirror/check")
def tv_mirror_check():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    if not target:
        return jsonify({"error": "Target mancante"}), 400

    result = {
        "ok": True,
        "target": target,
        "adb": {"available": False, "detail": "Porta 5555 non disponibile"},
        "cast": {"available": False, "detail": "Google Cast/DIAL non rilevato"},
        "capture": {"available": False, "detail": "Nessun protocollo di cattura TV -> PC rilevato"}
    }

    try:
        with socket.create_connection((target, 5555), timeout=1.5):
            result["adb"] = {
                "available": True,
                "detail": "ADB TCP disponibile: il mirroring può usare scrcpy con autorizzazione ADB."
            }
            result["capture"] = {
                "available": True,
                "detail": "ADB TCP disponibile: scrcpy può tentare la cattura autorizzata dello schermo."
            }
    except Exception:
        pass

    try:
        import urllib.request
        url = f"http://{target}:8008/ssdp/device-desc.xml"
        with urllib.request.urlopen(url, timeout=2) as r:
            xml = r.read(5000).decode("utf-8", "replace")
        if "dial-multiscreen-org" in xml.lower() or "android tv" in xml.lower():
            result["cast"] = {
                "available": True,
                "detail": "Google Cast/DIAL disponibile: casting verso la TV; non è il canale usato per TV -> PC."
            }
    except Exception:
        pass

    log(f"tv mirror check {target} adb={result['adb']['available']} cast={result['cast']['available']}")
    return jsonify(result)

@app.post("/api/tv/key")
def tv_key():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    key = str(data.get("key", "")).strip().upper()
    allowed = {
        "POWER","HOME","BACK","DPAD_UP","DPAD_DOWN","DPAD_LEFT","DPAD_RIGHT",
        "DPAD_CENTER","VOLUME_UP","VOLUME_DOWN","VOLUME_MUTE","MUTE",
        "MEDIA_PLAY_PAUSE","TV_INPUT","MENU","INFO"
    }
    if key not in allowed:
        return jsonify({"error": "Tasto non supportato"}), 400
    try:
        tv.send_key(target, "KEYCODE_" + key)
        return jsonify({"ok": True, "message": f"Tasto {key} inviato"})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Comando TV fallito: {type(e).__name__}: {e}"}), 502

@app.post("/api/launch")
def api_launch():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    method = str(data.get("method", "")).lower()

    cmd = connection_command(target, method)
    if not cmd:
        return jsonify({"error": "Metodo non supportato"}), 400

    log(f"launch {method} {target}")

    clients = {
        "ssh": ["ssh", target],
        "rdp": ["xfreerdp3", f"/v:{target}"],
        "vnc": ["vncviewer", f"{target}:5900"],
        "adb": ["adb", "connect", f"{target}:5555"]
    }

    argv = clients.get(method)
    if not argv:
        return jsonify({"error": "Avvio automatico non disponibile per questo metodo"}), 400

    try:
        subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return jsonify({"ok": True, "message": f"Client {method.upper()} avviato"})
    except FileNotFoundError:
        return jsonify({"error": f"Client {method.upper()} non installato su Kali"}), 404

def _is_remotecontrolhub_running(port):
    """Evita di avviare una seconda istanza di RemoteControlHub sulla stessa porta."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            pass
    except OSError:
        return False

    current_dir = str(BASE)
    proc_root = Path("/proc")

    try:
        for entry in proc_root.iterdir():
            if not entry.name.isdigit():
                continue

            pid = entry.name
            try:
                cwd = os.readlink(entry / "cwd")
                cmdline = (entry / "cmdline").read_text(errors="replace").replace("\\x00", " ")
            except (OSError, PermissionError):
                continue

            if cwd == current_dir and "webapp.py" in cmdline and int(pid) != os.getpid():
                return True
    except Exception:
        pass

    return False


if __name__ == "__main__":
    port = int(os.getenv("RCH_PORT", "8080"))

    if _is_remotecontrolhub_running(port):
        print(f"RemoteControlHub è già attivo sulla porta {port}. Nessuna seconda istanza avviata.")
        raise SystemExit(0)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
