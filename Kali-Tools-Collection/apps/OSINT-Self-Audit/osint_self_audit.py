#!/usr/bin/env python3

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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

    for platform, template in SOCIAL_PLATFORMS.items():
        url = template.format(urllib.parse.quote(username))
        status, _ = http_get(url)

        results.append({
            "platform": platform,
            "status": "FOUND" if status == 200 else "NOT FOUND",
            "url": url,
        })

    return results


def validate_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return {
        "email": email,
        "format_valid": bool(re.match(pattern, email)),
    }


def check_domain(domain):
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.split("/")[0]

    results = []

    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        status, _ = http_get(url)

        if status:
            results.append({
                "url": url,
                "status": status,
            })

    return {
        "domain": domain,
        "websites": results,
    }


def build_report(args):
    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target": {},
        "username_results": [],
        "email_results": [],
        "domain_results": [],
    }

    if args.username:
        data["target"]["username"] = args.username
        data["username_results"] = check_username(args.username)

    if args.email:
        data["target"]["email"] = args.email
        data["email_results"].append(validate_email(args.email))

    for domain in args.domain or []:
        data["domain_results"].append(check_domain(domain))

    return data


def save_json(data):
    os.makedirs(REPORT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(
        REPORT_DIR,
        f"osint_{timestamp}.json",
    )

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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
        "TitleCustom",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=20,
    )

    heading = ParagraphStyle(
        "HeadingCustom",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=8,
    )

    normal = ParagraphStyle(
        "NormalCustom",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
    )

    story = [
        Paragraph("OSINT SELF-AUDIT REPORT", title),
        Paragraph(f"Generato: {data['generated_at']}", normal),
        Spacer(1, 15),
    ]

    story.append(Paragraph("TARGET", heading))

    target_rows = [["Campo", "Valore"]]

    for key, value in data["target"].items():
        target_rows.append([key, str(value)])

    if len(target_rows) > 1:
        table = Table(target_rows, colWidths=[120, 350])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)

    story.append(Paragraph("SOCIAL / USERNAME", heading))

    if data["username_results"]:
        rows = [["Platform", "Status", "URL"]]

        for result in data["username_results"]:
            rows.append([
                result["platform"],
                result["status"],
                result["url"],
            ])

        table = Table(rows, colWidths=[90, 80, 300])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
    else:
        story.append(Paragraph(
            "Nessun username analizzato.",
            normal,
        ))

    story.append(Paragraph("EMAIL", heading))

    if data["email_results"]:
        for result in data["email_results"]:
            status = (
                "Formato valido"
                if result["format_valid"]
                else "Formato non valido"
            )

            story.append(Paragraph(
                f"- {result['email']} → {status}",
                normal,
            ))
    else:
        story.append(Paragraph(
            "Nessuna email analizzata.",
            normal,
        ))

    story.append(Paragraph("DOMAINS", heading))

    if data["domain_results"]:
        for result in data["domain_results"]:
            story.append(Paragraph(
                f"<b>Dominio:</b> {result['domain']}",
                normal,
            ))

            if result["websites"]:
                for website in result["websites"]:
                    story.append(Paragraph(
                        f"- {website['url']} → HTTP {website['status']}",
                        normal,
                    ))
            else:
                story.append(Paragraph(
                    "- Nessuna risposta HTTP.",
                    normal,
                ))
    else:
        story.append(Paragraph(
            "Nessun dominio analizzato.",
            normal,
        ))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Report generato automaticamente. "
        "I risultati rappresentano esclusivamente informazioni "
        "pubblicamente verificabili dalle sorgenti interrogate.",
        normal,
    ))

    doc.build(story)
    return filename


def main():
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
        help="Dominio da analizzare (ripetibile)",
    )

    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Non creare il PDF",
    )

    args = parser.parse_args()

    if not any([
        args.username,
        args.email,
        args.domain,
    ]):
        parser.error(
            "Specifica almeno --username, --email oppure --domain"
        )

    print()
    print("================================")
    print("       OSINT SELF-AUDIT")
    print("================================")
    print()

    data = build_report(args)

    json_file = save_json(data)
    print(f"[+] JSON salvato: {json_file}")

    if not args.no_pdf:
        pdf_file = create_pdf(data)
        print(f"[+] PDF salvato:  {pdf_file}")

    print()
    print("[+] Analisi completata.")


if __name__ == "__main__":
    main()
