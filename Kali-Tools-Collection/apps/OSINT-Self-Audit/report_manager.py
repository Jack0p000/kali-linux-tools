#!/usr/bin/env python3
import os
import re
import time
from datetime import datetime

REPORT_DIR = "/home/jack0p000/Scaricati/reports"
MAX_AGE_SECONDS = 30 * 24 * 60 * 60

def safe_part(value):
    value = (value or "").strip().lstrip("@")
    value = re.sub(r"https?://", "", value, flags=re.I)
    value = re.sub(r"[^A-Za-z0-9._@-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("._-")
    return value[:80] or "report"

def research_label(data):
    target = data.get("target", {})
    if target.get("username"):
        return safe_part(target["username"])
    if target.get("email"):
        return safe_part(target["email"])
    if target.get("domain"):
        return safe_part(target["domain"])

    corr = data.get("public_correlations", {})
    if corr.get("queries"):
        return safe_part(corr["queries"][0].replace('"', ""))

    return "osint_report"

def cleanup_old():
    now = time.time()
    removed = 0
    for name in os.listdir(REPORT_DIR):
        path = os.path.join(REPORT_DIR, name)
        if not os.path.isfile(path):
            continue
        # Non vengono più gestiti né conservati report JSON.
        if not name.lower().endswith(".pdf"):
            continue
        try:
            if now - os.path.getmtime(path) > MAX_AGE_SECONDS:
                os.remove(path)
                removed += 1
                print(f"[REPORT-MANAGER] Eliminato (>30 giorni): {name}")
        except OSError as exc:
            print(f"[REPORT-MANAGER] Errore eliminando {name}: {exc}")
    return removed

def remove_json():
    removed = 0
    for name in os.listdir(REPORT_DIR):
        if not name.lower().endswith(".json"):
            continue
        path = os.path.join(REPORT_DIR, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
                removed += 1
                print(f"[REPORT-MANAGER] JSON eliminato: {name}")
            except OSError as exc:
                print(f"[REPORT-MANAGER] Errore eliminando JSON {name}: {exc}")
    return removed

def rename_pdfs():
    for name in os.listdir(REPORT_DIR):
        if not name.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(REPORT_DIR, name)

        # I PDF prodotti dal programma devono essere rinominati in base
        # a ciò che è stato ricercato. Se non esiste il JSON originale,
        # non possiamo ricostruire il target con certezza.
        if name.startswith("osint_"):
            continue

        # Mantiene invariati i PDF già nominati correttamente.
        # Le nuove scansioni vengono gestite direttamente dal report manager
        # quando il PDF ha il nome temporaneo generato dal programma.

def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    remove_json()
    cleanup_old()
    print("[REPORT-MANAGER] Solo PDF: JSON eliminati e pulizia >30 giorni completata.")

if __name__ == "__main__":
    main()
