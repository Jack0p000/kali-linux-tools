#!/usr/bin/env python3

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors


REPORT_DIR = "reports"

SOCIAL_PLATFORMS = {
    "Instagram": "https://www.instagram.com/{}/",
    "TikTok": "https://www.tiktok.com/@{}",
    "GitHub": "https://github.com/{}",
    "Reddit": "https://www.reddit.com/user/{}/",
    "X": "https://x.com/{}",
    "Pinterest": "https://www.pinterest.com/{}/",
    "Twitch": "https://www.twitch.tv/{}",
    "Telegram": "https://t.me/{}",
}


def http_get(url, timeout=10):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 Chrome/131 Safari/537.36"
        )
    }

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode(
                "utf-8", errors="ignore"
            )
    except Exception:
        return None, None


def check_username(username):
    results = []

    print("\n[*] Ricerca username...\n")

    for platform, template in SOCIAL_PLATFORMS.items():
        url = template.format(urllib.parse.quote(username))
        status, _ = http_get(url)

        found = status == 200

        results.append({
            "platform": platform,
            "status": "FOUND" if found else "NOT FOUND",
            "url": url,
        })

        if found:
            print(f"[+] {platform}: trovato")
        else:
            print(f"[-] {platform}: non trovato")

    return results


def validate_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    valid = bool(re.match(pattern, email))

    return {
        "email": email,
        "format_valid": valid,
    }


def check_domain(domain):
    domain = domain.strip()
    domain = domain.replace("https://", "")
    domain = domain.replace("http://", "")
    domain = domain.split("/")[0]

    results = []

    print(f"\n[*] Controllo dominio: {domain}")

    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        status, _ = http_get(url)

        if status:
            print(f"[+] {url} -> HTTP {status}")

            results.append({
                "url": url,
                "status": status,
            })
        else:
            print(f"[-] {url} -> nessuna risposta")

    return {
        "domain": domain,
        "websites": results,
    }


def save_json(data):
    os.makedirs(REPORT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = os.path.join(
        REPORT_DIR,
        f"osint_{timestamp}.json",
    )

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False,
        )

    return filename


def create_pdf(data):
    os.makedirs(REPORT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = os.path.join(
        REPORT_DIR,
        f"osint_{timestamp}.pdf",
    )

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=20,
    )

    heading = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=8,
    )

    normal = ParagraphStyle(
        "ReportNormal",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
    )

    story = []

    story.append(
        Paragraph("OSINT SELF-AUDIT REPORT", title)
    )

    story.append(
        Paragraph(
            f"Generato: {data['generated_at']}",
            normal,
        )
    )

    story.append(Spacer(1, 15))

    # TARGET
    story.append(Paragraph("TARGET", heading))

    target_rows = [["Campo", "Valore"]]

    for key, value in data["target"].items():
        target_rows.append([
            key,
            str(value),
        ])

    if len(target_rows) > 1:
        table = Table(
            target_rows,
            colWidths=[120, 350],
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        story.append(table)

    # USERNAME
    story.append(
        Paragraph("SOCIAL / USERNAME", heading)
    )

    if data["username_results"]:
        rows = [["Platform", "Status", "URL"]]

        for result in data["username_results"]:
            rows.append([
                result["platform"],
                result["status"],
                result["url"],
            ])

        table = Table(
            rows,
            colWidths=[85, 85, 300],
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        story.append(table)

    # EMAIL
    story.append(
        Paragraph("EMAIL", heading)
    )

    if data["email_results"]:
        for result in data["email_results"]:
            status = (
                "Formato valido"
                if result["format_valid"]
                else "Formato non valido"
            )

            story.append(
                Paragraph(
                    f"- {result['email']} → {status}",
                    normal,
                )
            )
    else:
        story.append(
            Paragraph(
                "Nessuna email analizzata.",
                normal,
            )
        )

    # DOMAINS
    story.append(
        Paragraph("DOMAINS", heading)
    )

    if data["domain_results"]:
        for result in data["domain_results"]:
            story.append(
                Paragraph(
                    f"<b>Dominio:</b> {result['domain']}",
                    normal,
                )
            )

            for website in result["websites"]:
                story.append(
                    Paragraph(
                        f"- {website['url']} → HTTP {website['status']}",
                        normal,
                    )
                )

    else:
        story.append(
            Paragraph(
                "Nessun dominio analizzato.",
                normal,
            )
        )

    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            "Report generato automaticamente. "
            "I risultati riguardano informazioni pubblicamente "
            "verificabili dalle sorgenti interrogate.",
            normal,
        )
    )

    doc.build(story)

    return filename


def run_scan(username=None, email=None, domains=None):
    data = {
        "generated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "target": {},
        "username_results": [],
        "email_results": [],
        "domain_results": [],
    }

    if username:
        data["target"]["username"] = username
        data["username_results"] = check_username(username)

    if email:
        data["target"]["email"] = email
        data["email_results"].append(
            validate_email(email)
        )

    for domain in domains or []:
        data["domain_results"].append(
            check_domain(domain)
        )

    print("\n[*] Generazione report...")

    json_file = save_json(data)
    pdf_file = create_pdf(data)

    print("\n================================")
    print("       SCANSIONE COMPLETATA")
    print("================================")
    print(f"[+] JSON: {json_file}")
    print(f"[+] PDF:  {pdf_file}")
    print()


def interactive_mode():
    while True:
        print("\n================================")
        print("       OSINT SELF-AUDIT")
        print("================================")
        print("1. Cerca username")
        print("2. Verifica email")
        print("3. Controlla dominio")
        print("4. Username + email")
        print("5. Username + email + dominio")
        print("6. Esci")
        print()

        choice = input("Scelta: ").strip()

        if choice == "1":
            username = input("Inserisci username: ").strip()

            if username:
                run_scan(username=username)
            else:
                print("[!] Username vuoto.")

        elif choice == "2":
            email = input("Inserisci email: ").strip()

            if email:
                run_scan(email=email)
            else:
                print("[!] Email vuota.")

        elif choice == "3":
            domain = input("Inserisci dominio: ").strip()

            if domain:
                run_scan(domains=[domain])
            else:
                print("[!] Dominio vuoto.")

        elif choice == "4":
            username = input("Inserisci username: ").strip()
            email = input("Inserisci email: ").strip()

            if username or email:
                run_scan(
                    username=username or None,
                    email=email or None,
                )
            else:
                print("[!] Devi inserire almeno un dato.")

        elif choice == "5":
            username = input("Inserisci username: ").strip()
            email = input("Inserisci email: ").strip()
            domain = input("Inserisci dominio: ").strip()

            if username or email or domain:
                run_scan(
                    username=username or None,
                    email=email or None,
                    domains=[domain] if domain else [],
                )
            else:
                print("[!] Devi inserire almeno un dato.")

        elif choice == "6":
            print("[+] Uscita.")
            break

        else:
            print("[!] Scelta non valida.")


def cli_mode():
    import argparse

    parser = argparse.ArgumentParser(
        description="OSINT Self-Audit Tool"
    )

    parser.add_argument(
        "--username",
        help="Username da analizzare",
    )

    parser.add_argument(
        "--email",
        help="Email da verificare",
    )

    parser.add_argument(
        "--domain",
        action="append",
        help="Dominio da analizzare",
    )

    args = parser.parse_args()

    if not any([
        args.username,
        args.email,
        args.domain,
    ]):
        interactive_mode()
        return

    run_scan(
        username=args.username,
        email=args.email,
        domains=args.domain,
    )


if __name__ == "__main__":
    cli_mode()
