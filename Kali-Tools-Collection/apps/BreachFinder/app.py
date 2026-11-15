
# Shared integrations are resolved relative to this collection, not a user-specific home path.
import os as _integration_os
import sys as _integration_sys
_APPS_DIR = _integration_os.path.dirname(_integration_os.path.dirname(_integration_os.path.abspath(__file__)))
for _shared_dir in ("ToolShareHub", "ToolAuth"):
    _shared_path = _integration_os.path.join(_APPS_DIR, _shared_dir)
    if _integration_os.path.isdir(_shared_path) and _shared_path not in _integration_sys.path:
        _integration_sys.path.insert(0, _shared_path)
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = "BreachFinder"
_ts_register(_TS_NAME)
_ts_publish(_TS_NAME, "startup", {"pid": _integration_os.getpid()})
from auth import login as _ta_login
_ta_login(_TS_NAME)
#!/usr/bin/env python3
import json
import os
import re
import threading
import uuid
import secrets
import hashlib
import hmac
import sqlite3
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.getenv("BREACH_HOST", "127.0.0.1")
PORT = int(os.getenv("BREACH_PORT", "3010"))
BREACH_PROVIDER = "XposedOrNot"
UA = "Jack0p000-DataBreachScanner/1.0"

JOBS = {}
SESSIONS = {}
LOCK = threading.Lock()
LOGIN_USER = os.getenv("TOOL_AUTH_USER", "")
LOGIN_PASSWORD = os.getenv("TOOL_AUTH_PASS", "")
LOGIN_SALT = bytes.fromhex("724e042423c68f357d59ecedb4f1a4cc")
LOGIN_HASH = ""
SESSION_COOKIE = "breach_session"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE_DIR, "reports")
DB_PATH = os.path.join(BASE_DIR, "breach_tracker.sqlite3")
os.makedirs(REPORT_DIR, exist_ok=True)

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db_connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS reports (
            job_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, target TEXT NOT NULL,
            status TEXT NOT NULL, inputs_json TEXT NOT NULL, results_json TEXT NOT NULL,
            logs_json TEXT NOT NULL, pdf_path TEXT NOT NULL)""")

init_db()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def add_log(job_id, level, message):
    with LOCK:
        JOBS[job_id]["logs"].append({
            "time": utc_now(),
            "level": level,
            "message": message
        })


def get_json(url, headers=None, timeout=15):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
            return r.status, (json.loads(raw) if raw else None), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else None
        except Exception:
            data = {"error": raw[:1000]}
        return e.code, data, dict(e.headers)
    except Exception as e:
        return None, {"error": str(e)}, {}


def search_email(job_id, email):
    url = "https://api.xposedornot.com/v1/check-email/" + urllib.parse.quote(email, safe="")
    url += "?details=true"
    add_log(job_id, "info", "Verifica email tramite XposedOrNot (API gratuita, senza chiave).")
    status, data, headers = get_json(url)

    if status == 200 and isinstance(data, dict):
        if data.get("status") == "success":
            raw_details = data.get("breach_details") or []
            if isinstance(raw_details, dict):
                raw_details = list(raw_details.values())
            details_by_name = {
                str(item.get("name", "")).casefold(): item
                for item in raw_details if isinstance(item, dict)
            }
            names = []
            for group in data.get("breaches", []):
                if isinstance(group, list):
                    names.extend(str(name) for name in group if name)
                elif isinstance(group, str):
                    names.append(group)
            breaches = []
            seen = set()
            for name in names:
                if name.casefold() in seen:
                    continue
                seen.add(name.casefold())
                detail = details_by_name.get(name.casefold(), {})
                company = detail.get("company") or {}
                security = detail.get("security") or {}
                breaches.append({
                    "name": name,
                    "title": name,
                    "domain": company.get("name"),
                    "breach_date": detail.get("breach_date"),
                    "pwn_count": detail.get("records_exposed"),
                    "data_classes": detail.get("exposed_data") or [],
                    "verified": security.get("is_verified"),
                    "description": detail.get("description")
                })
            add_log(job_id, "success", f"XposedOrNot ha restituito {len(breaches)} violazioni associate all'indirizzo.")
            return {
                "source": "XposedOrNot",
                "status": "found" if breaches else "clear",
                "count": len(breaches),
                "breaches": breaches,
                "source_url": "https://xposedornot.com/"
            }
        if data.get("Error") == "Not found" or data.get("email") is None:
            add_log(job_id, "success", "XposedOrNot non ha restituito violazioni note per questa email.")
            return {"source": "XposedOrNot", "status": "clear", "count": 0, "breaches": [], "source_url": "https://xposedornot.com/"}

    if status == 404:
        add_log(job_id, "success", "XposedOrNot non ha restituito violazioni note per questa email.")
        return {"source": "XposedOrNot", "status": "clear", "count": 0, "breaches": [], "source_url": "https://xposedornot.com/"}
    if status == 429:
        retry_after = headers.get("retry-after", "attendi il ripristino del limite")
        message = f"Limite gratuito XposedOrNot raggiunto (HTTP 429). Riprova tra {retry_after}."
    elif status is None:
        message = "XposedOrNot non raggiungibile: controlla la connessione Internet."
    else:
        message = f"XposedOrNot ha risposto con HTTP {status}; verifica non completata."
    add_log(job_id, "warning", message)
    return {"source": "XposedOrNot", "status": "error", "http_status": status, "details": data}


def breach_catalog(job_id):
    add_log(job_id, "info", "Recupero catalogo pubblico XposedOrNot.")
    status, data, _ = get_json("https://api.xposedornot.com/v1/breaches")
    if status != 200 or not isinstance(data, dict):
        add_log(job_id, "warning", f"Catalogo XposedOrNot non disponibile: HTTP {status}.")
        return {"source": "XposedOrNot", "status": "error"}
    entries = data.get("exposedBreaches") or data.get("breaches") or []
    add_log(job_id, "success", f"Catalogo XposedOrNot ricevuto: {len(entries)} voci.")
    return {"source": "XposedOrNot", "status": "ok", "count": len(entries), "breaches": entries, "source_url": "https://xposedornot.com/"}


def run_job(job_id, inputs):
    add_log(job_id, "info", "Scansione avviata.")
    results = {"sources": [], "input_capabilities": {}, "summary": {}}
    email = str(inputs.get("email", "")).strip().lower()
    domain = str(inputs.get("domain", "")).strip().lower()
    username = str(inputs.get("username", "")).strip()
    phone = str(inputs.get("phone", "")).strip()
    name = str(inputs.get("name", "")).strip()

    email_status = "not_provided"
    if email:
        if EMAIL_RE.fullmatch(email):
            source_result = search_email(job_id, email)
            results["sources"].append(source_result)
            email_status = source_result.get("status", "error")
        else:
            add_log(job_id, "warning", "Formato email non valido: verifica email non eseguita.")
            results["input_capabilities"]["email"] = "invalid"
            email_status = "invalid"
    else:
        results["input_capabilities"]["email"] = "not_provided"
        add_log(job_id, "info", "Nessuna email fornita: verifica individuale non eseguita.")

    if domain:
        results["input_capabilities"]["domain"] = {
            "status": "not_directly_enumerated",
            "message": "La ricerca di account compromessi per dominio richiede autorizzazione/verifica del dominio."
        }
    if username:
        results["input_capabilities"]["username"] = {
            "status": "accepted",
            "message": "Input acquisito; non vengono interrogati database trafugati."
        }
    if phone:
        results["input_capabilities"]["phone"] = {
            "status": "accepted",
            "message": "Input acquisito; non vengono interrogati database trafugati."
        }
    if name:
        results["input_capabilities"]["name"] = {
            "status": "accepted",
            "message": "Input acquisito; nessun risultato viene dichiarato senza una fonte verificabile."
        }

    # Non scaricare il catalogo generale a ogni ricerca: non dimostra che
    # uno specifico account sia presente in una violazione.
    found = []
    for source in results["sources"]:
        if source.get("status") == "found":
            found.extend(source.get("breaches", []))

    if email_status in ("found", "clear"):
        overall = "completed"
        message = "Verifica email completata tramite XposedOrNot."
        add_log(job_id, "success", "Verifica email completata.")
    elif email_status == "not_configured":
        overall = "partial"
        message = "Verifica email non eseguita: il servizio gratuito XposedOrNot non è raggiungibile o non ha completato la richiesta."
        add_log(job_id, "warning", "Nessuna email inserita: la verifica individuale non è stata eseguita.")
    elif email_status == "not_provided":
        overall = "partial"
        message = "Verifica individuale non eseguita: non è stata fornita un'email. Gli altri campi inseriti non sono stati verificati da una fonte di breach."
        add_log(job_id, "warning", "Nessuna verifica effettuata per username, telefono o nome: questa versione non dispone di una fonte attendibile per controllarli.")
    elif email_status == "invalid":
        overall = "partial"
        message = "Verifica email non eseguita: formato non valido."
    else:
        overall = "partial"
        message = "Verifica email non completata correttamente; consulta i log e riprova."

    results["summary"] = {
        "email_breach_count": len(found),
        "sources": len(results["sources"]),
        "status": overall,
        "message": message,
        "completed_at": utc_now()
    }
    with LOCK:
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["results"] = results
        JOBS[job_id]["finished_at"] = utc_now()
    add_log(job_id, "success" if overall == "completed" else "warning",
            "Scansione completata." if overall == "completed" else "Elaborazione terminata con verifica parziale.")
    try:
        save_report(job_id)
        add_log(job_id, "success", "Report PDF generato e archiviato.")
    except Exception as exc:
        add_log(job_id, "error", "Generazione PDF non riuscita: " + str(exc)[:180])


def save_report(job_id):
    with LOCK:
        job = dict(JOBS[job_id])
        job["logs"] = list(JOBS[job_id]["logs"])
    inputs = job.get("inputs", {})
    results = job.get("results") or {}
    summary = results.get("summary") or {}
    target = next((str(inputs.get(k, "")).strip() for k in ("email", "domain", "username", "phone", "name") if str(inputs.get(k, "")).strip()), "—")
    pdf_path = os.path.join(REPORT_DIR, f"report_{job_id}.pdf")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BTTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, textColor=colors.HexColor("#123b5a"), spaceAfter=5))
    styles.add(ParagraphStyle(name="BTSub", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#587086"), leading=13))
    styles.add(ParagraphStyle(name="BTHead", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#176da5"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="BTBody", parent=styles["BodyText"], fontSize=8.5, leading=12))
    story = [
        Paragraph("BREACH TRACKER", styles["BTTitle"]),
        Paragraph("PUBLIC BREACH INTELLIGENCE REPORT", styles["BTSub"]),
        Spacer(1, 8*mm),
        Paragraph("Report overview", styles["BTHead"])
    ]
    status_label = "COMPLETED" if summary.get("status") == "completed" else "PARTIAL — VERIFICATION INCOMPLETE"
    meta = [
        ["Target", target],
        ["Generated (UTC)", job.get("finished_at") or utc_now()],
        ["Scan status", status_label],
        ["Email breach matches", str(summary.get("email_breach_count", 0))],
        ["API key required", "No — free email endpoint"]
    ]
    table = Table(meta, colWidths=[48*mm, 118*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#eaf2f8")),
        ("TEXTCOLOR",(0,0),(0,-1),colors.HexColor("#23435d")),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#cbd8e3")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)
    ]))
    story += [table, Paragraph("Assessment", styles["BTHead"]),
              Paragraph(escape(str(summary.get("message", "No assessment available."))), styles["BTBody"])]
    story.append(Paragraph("Source results", styles["BTHead"]))
    for source in results.get("sources", []):
        title = escape(str(source.get("source", "Source")))
        state = escape(str(source.get("status", "unknown")))
        story.append(Paragraph(f"<b>{title}</b> — status: {state}", styles["BTBody"]))
        for breach in source.get("breaches", [])[:100]:
            label = escape(str(breach.get("title") or breach.get("name") or "Breach"))
            domain_value = escape(str(breach.get("domain") or "—"))
            date_value = escape(str(breach.get("breach_date") or "—"))
            count = escape(str(breach.get("pwn_count") or "—"))
            classes = escape(", ".join(breach.get("data_classes") or []))
            story.append(Paragraph(f"• <b>{label}</b> · {domain_value} · {date_value} · records: {count}<br/>Data classes: {classes}", styles["BTBody"]))
    story.append(Paragraph("Scan log", styles["BTHead"]))
    for entry in job.get("logs", []):
        line = f"[{entry.get('level','INFO').upper()}] {entry.get('time','')} — {entry.get('message','')}"
        story.append(Paragraph(escape(line), styles["BTBody"]))
    story += [Spacer(1, 8*mm), Paragraph("This report contains public breach metadata only. It does not contain passwords, stolen credential dumps, or private account data.", styles["BTSub"])]

    # Plain-language conclusion for readers without technical background.
    story.append(Paragraph("IN BREVE — COSA SIGNIFICA", styles["BTHead"]))
    breach_count = int(summary.get("email_breach_count", 0) or 0)
    email = str(inputs.get("email", "")).strip()
    if summary.get("status") == "completed" and email:
        if breach_count:
            plain_summary = (
                f"La verifica dell'indirizzo email ha trovato {breach_count} "
                "corrispondenze in violazioni di dati conosciute. Questo indica che "
                "l'indirizzo compare nelle informazioni pubbliche relative a queste "
                "violazioni; non dimostra da solo che l'account sia attualmente accessibile "
                "a terzi. È consigliabile cambiare le password interessate, usarne una "
                "diversa per ogni servizio e attivare l'autenticazione a due fattori."
            )
        else:
            plain_summary = (
                "La fonte consultata non ha restituito violazioni note associate "
                "all'indirizzo email. È un risultato positivo, ma non garantisce che "
                "l'indirizzo non sia mai comparso in incidenti non presenti nella fonte."
            )
    else:
        reason = summary.get("message") or "La verifica individuale non è stata completata."
        plain_summary = (
            "La scansione non ha potuto confermare se l'indirizzo o l'account compaia "
            "in una violazione. " + str(reason) +
            " Quindi questo report non deve essere interpretato come prova che l'account "
            "sia al sicuro o che sia stato compromesso."
        )
    story.append(Paragraph(escape(plain_summary), styles["BTBody"]))
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=17*mm, bottomMargin=17*mm, title="Breach Tracker Report")
    doc.build(story)
    with db_connect() as conn:
        conn.execute("INSERT OR REPLACE INTO reports(job_id,created_at,target,status,inputs_json,results_json,logs_json,pdf_path) VALUES(?,?,?,?,?,?,?,?)",
            (job_id, job.get("finished_at") or utc_now(), target, summary.get("status","partial"),
             json.dumps(inputs, ensure_ascii=False), json.dumps(results, ensure_ascii=False),
             json.dumps(job.get("logs",[]), ensure_ascii=False), pdf_path))

def create_job(inputs):
    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "status": "running",
            "started_at": utc_now(),
            "finished_at": None,
            "inputs": {
                "email": inputs.get("email", ""),
                "domain": inputs.get("domain", ""),
                "username": inputs.get("username", ""),
                "phone": inputs.get("phone", ""),
                "name": inputs.get("name", "")
            },
            "logs": [],
            "results": None
        }
    threading.Thread(target=run_job, args=(job_id, inputs), daemon=True).start()
    return job_id


class APIHandler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_json(204, {})

    def do_POST(self):
        if self.path == "/api/login":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self.send_json(400, {"ok": False, "error": "invalid_json"})
                return
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", ""))
            if not LOGIN_USER or not LOGIN_PASSWORD:
                self.send_json(503, {"ok": False, "error": "auth_not_configured"})
                return
            if not hmac.compare_digest(username.lower(), LOGIN_USER.lower()) or not hmac.compare_digest(password, LOGIN_PASSWORD):
                self.send_json(401, {"ok": False, "error": "invalid_credentials"})
                return
            sid = secrets.token_urlsafe(32)
            with LOCK:
                SESSIONS[sid] = {"user": "Analyst", "created": utc_now()}
            raw = json.dumps({"ok": True, "user": "Analyst"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=14400")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if self.path == "/api/logout":
            sid = self.get_session_id()
            with LOCK:
                SESSIONS.pop(sid, None)
            self.send_response(200)
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if self.path != "/api/search":
            self.send_json(404, {"error": "not_found"})
            return
        if not self.require_session():
            self.send_json(401, {"error": "authentication_required"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            self.send_json(400, {"error": "invalid_json", "message": str(e)})
            return

        if not isinstance(payload, dict):
            self.send_json(400, {"error": "object_required"})
            return

        fields = ("email", "domain", "username", "phone", "name")
        if not any(str(payload.get(k, "")).strip() for k in fields):
            self.send_json(400, {"error": "empty_input"})
            return

        job_id = create_job(payload)
        self.send_json(202, {
            "job_id": job_id,
            "status": "running",
            "result_url": "/api/search/" + job_id,
            "logs_url": "/api/logs/" + job_id
        })

    def send_file(self, filename, content_type):
        base = os.path.dirname(os.path.abspath(__file__))
        safe = {"index.html": "index.html", "style.css": "style.css", "app.js": "app.js"}
        if filename not in safe:
            self.send_json(404, {"error": "not_found"})
            return
        path = os.path.join(base, safe[filename])
        try:
            with open(path, "rb") as f:
                raw = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except OSError:
            self.send_json(404, {"error": "file_not_found"})

    def send_asset(self, path, content_type):
        try:
            with open(path, "rb") as f:
                raw = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except OSError:
            self.send_json(404, {"error": "asset_not_found"})

    def get_session_id(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            key, _, value = part.strip().partition("=")
            if key == SESSION_COOKIE:
                return value
        return ""

    def require_session(self):
        sid = self.get_session_id()
        with LOCK:
            session = SESSIONS.get(sid)
        return session

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/dashboard":
            session = self.require_session()
            if not session:
                self.send_json(401, {"error": "authentication_required"})
                return
            with LOCK:
                jobs = sorted(JOBS.values(), key=lambda j: j.get("started_at", ""), reverse=True)
                active = sum(1 for j in jobs if j.get("status") == "running")
                activity = []
                for job in jobs[:5]:
                    inp = job.get("inputs", {})
                    target = inp.get("email") or inp.get("domain") or inp.get("username") or inp.get("phone") or inp.get("name") or "—"
                    results = job.get("results") or {}
                    leaks = (results.get("summary") or {}).get("email_breach_count", 0)
                    activity.append({"target": target, "type": "Email / OSINT scan", "status": "Running" if job.get("status") == "running" else "Completed", "leaks": leaks, "date": job.get("started_at", "")[:10]})
            self.send_json(200, {"user": session["user"], "db_status": "XposedOrNot free API available", "active_scans": active, "activity": activity, "sources": []})
            return

        if path == "/api/settings":
            if not self.require_session():
                self.send_json(401, {"error": "authentication_required"})
                return
            self.send_json(200, {"provider": "XposedOrNot", "configured": True, "api_key_required": False, "daily_limit": 100, "hourly_limit": 25})
            return

        if path == "/api/session":
            session = self.require_session()
            if not session:
                self.send_json(401, {"authenticated": False})
            else:
                self.send_json(200, {"authenticated": True, "user": session["user"]})
            return

        if path == "/api/reports":
            session = self.require_session()
            if not session:
                self.send_json(401, {"error": "authentication_required"})
                return
            with db_connect() as conn:
                rows = conn.execute("SELECT job_id,created_at,target,status FROM reports ORDER BY created_at DESC").fetchall()
            self.send_json(200, {"reports": [{
                "id": row["job_id"], "created_at": row["created_at"], "target": row["target"],
                "status": row["status"], "pdf_url": f"/api/reports/{row['job_id']}/pdf"
            } for row in rows]})
            return

        m = re.fullmatch(r"/api/reports/([a-f0-9]{32})/pdf", path)
        if m:
            if not self.require_session():
                self.send_json(401, {"error": "authentication_required"})
                return
            with db_connect() as conn:
                row = conn.execute("SELECT pdf_path FROM reports WHERE job_id=?", (m.group(1),)).fetchone()
            if not row or not os.path.isfile(row["pdf_path"]):
                self.send_json(404, {"error": "report_not_found"})
                return
            with open(row["pdf_path"], "rb") as f:
                raw = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="breach_report_{m.group(1)[:8]}.pdf"')
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/assets/login.jpg":
            self.send_asset(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "login.jpg"), "image/jpeg")
            return

        if path == "/assets/dashboard.jpg":
            self.send_asset(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "dashboard.jpg"), "image/jpeg")
            return

        if path == "/":
            self.send_file("index.html", "text/html; charset=utf-8")
            return

        if path == "/static/style.css":
            self.send_file("style.css", "text/css; charset=utf-8")
            return

        if path == "/static/app.js":
            self.send_file("app.js", "application/javascript; charset=utf-8")
            return

        if path == "/api/health":
            self.send_json(200, {
                "status": "online",
                "service": "data-breach-scanner",
                "provider": "XposedOrNot",
                "api_key_required": False,
                "time": utc_now()
            })
            return

        m = re.fullmatch(r"/api/search/([a-f0-9]{32})", path)
        if m:
            if not self.require_session():
                self.send_json(401, {"error": "authentication_required"})
                return
            with LOCK:
                job = JOBS.get(m.group(1))
            if not job:
                self.send_json(404, {"error": "job_not_found"})
            else:
                self.send_json(200, job)
            return

        m = re.fullmatch(r"/api/logs/([a-f0-9]{32})", path)
        if m:
            if not self.require_session():
                self.send_json(401, {"error": "authentication_required"})
                return
            with LOCK:
                job = JOBS.get(m.group(1))
            if not job:
                self.send_json(404, {"error": "job_not_found"})
            else:
                self.send_json(200, {
                    "job_id": m.group(1),
                    "logs": job["logs"]
                })
            return

        self.send_json(404, {"error": "not_found"})

    def log_message(self, fmt, *args):
        return


def main():
    print("[+] Data Breach Scanner")
    print(f"[+] API: http://{HOST}:{PORT}")
    print("[+] Provider: XposedOrNot (free email endpoint, no API key)")
    server = ThreadingHTTPServer((HOST, PORT), APIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()