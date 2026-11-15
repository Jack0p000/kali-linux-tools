
# --- ToolShare integration ---
import sys as _toolshare_sys
if '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:
    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')
from toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context
_TS_NAME = 'OSINT Self-Audit'
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

import argparse
import getpass
import json
import os
import subprocess
import re
import socket
import ssl
import urllib.parse
import urllib.request
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

REPORT_DIR = "/home/jack0p000/Scaricati/reports"
REPORT_MANAGER = "/home/jack0p000/Scaricati/report_manager.py"


def run_report_manager():
    try:
        subprocess.run(["python3", REPORT_MANAGER], check=False, timeout=30)
    except Exception as exc:
        print(f"[!] Gestore report non eseguito: {exc}")


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

COMMON_EMAIL_PROVIDERS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com",
    "live.com", "yahoo.com", "icloud.com", "proton.me", "protonmail.com"
}


def http_get(url, timeout=12, headers=None):
    base_headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 Chrome/131 Safari/537.36"
        )
    }
    if headers:
        base_headers.update(headers)

    request = urllib.request.Request(url, headers=base_headers)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="ignore"), dict(response.headers)
    except Exception:
        return None, None, {}


def dns_lookup(domain):
    domain = domain.strip().lower()
    result = {
        "domain": domain,
        "A": [],
        "AAAA": [],
        "MX": [],
        "NS": [],
    }

    try:
        import dns.resolver
    except ImportError:
        result["error"] = "dnspython non installato"
        return result

    for record_type in ("A", "AAAA", "MX", "NS"):
        try:
            answers = dns.resolver.resolve(domain, record_type, lifetime=5)

            for answer in answers:
                if record_type == "MX":
                    result[record_type].append(str(answer.exchange).rstrip("."))
                else:
                    result[record_type].append(str(answer).rstrip("."))

        except Exception:
            pass

    return result


def rdap_lookup(domain):
    domain = domain.strip().lower()
    url = f"https://rdap.org/domain/{urllib.parse.quote(domain)}"

    status, body, _ = http_get(url)

    if status != 200 or not body:
        return {
            "domain": domain,
            "status": status,
            "url": url,
        }

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {
            "domain": domain,
            "status": status,
            "url": url,
        }

    entities = []

    for entity in data.get("entities", []):
        roles = entity.get("roles", [])

        vcard = entity.get("vcardArray")
        name = None

        if isinstance(vcard, list) and len(vcard) > 1:
            for field in vcard[1]:
                if isinstance(field, list) and len(field) >= 4:
                    if field[0] == "fn":
                        name = field[3]
                        break

        if roles:
            entities.append({
                "roles": roles,
                "name": name,
            })

    return {
        "domain": domain,
        "status": status,
        "url": url,
        "ldhName": data.get("ldhName"),
        "status_flags": data.get("status", []),
        "entities": entities,
    }


def tls_certificate(domain):
    result = {
        "domain": domain,
        "port": 443,
        "subject": None,
        "issuer": None,
        "san": [],
        "error": None,
    }

    context = ssl.create_default_context()

    try:
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

                subject = dict(x[0] for x in cert.get("subject", []))
                issuer = dict(x[0] for x in cert.get("issuer", []))

                result["subject"] = subject
                result["issuer"] = issuer
                result["san"] = [
                    value
                    for kind, value in cert.get("subjectAltName", [])
                    if kind == "DNS"
                ]

    except Exception as exc:
        result["error"] = str(exc)

    return result


def resolve_domain(domain):
    result = {
        "domain": domain,
        "addresses": [],
        "errors": [],
    }

    try:
        infos = socket.getaddrinfo(domain, None)

        for info in infos:
            address = info[4][0]

            if address not in result["addresses"]:
                result["addresses"].append(address)

    except Exception as exc:
        result["errors"].append(str(exc))

    return result


def check_username(username):
    results = []

    print("\n[*] Ricerca username...\n")

    for platform, template in SOCIAL_PLATFORMS.items():
        url = template.format(urllib.parse.quote(username))
        status, _, _ = http_get(url)

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


def public_web_search(query, max_results=5):
    """Cerca esclusivamente risultati web pubblici.
    Non effettua login e non tenta di recuperare dati privati di registrazione.
    """
    encoded = urllib.parse.quote_plus(query)
    engines = [
        f"https://www.bing.com/search?q={encoded}&count={max_results}",
        f"https://www.google.com/search?q={encoded}&num={max_results}",
    ]

    for url in engines:
        status, body, _ = http_get(
            url,
            timeout=12,
            headers={"Accept-Language": "it-IT,it;q=0.9,en;q=0.8"},
        )

        if not body:
            continue

        results = []
        page_public_emails = extract_public_emails(body)

        # Bing: risultati organici tipicamente dentro h2 > a.
        for match in re.finditer(
            r'<h2[^>]*>\s*<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            body,
            re.I | re.S,
        ):
            href = match.group(1).replace("&amp;", "&")
            title = re.sub(r"<[^>]+>", " ", match.group(2))
            title = re.sub(r"\s+", " ", title).strip()
            host = urllib.parse.urlparse(href).netloc.lower()

            if host and "bing.com" not in host and "google.com" not in host:
                item = {"title": title[:200], "url": href, "public_emails": page_public_emails}
                if item not in results:
                    results.append(item)

            if len(results) >= max_results:
                return results

        # Fallback generico per motori che cambiano il markup.
        for href in re.findall(r'https?://[^"\s<>]+', body):
            href = href.replace("&amp;", "&")
            host = urllib.parse.urlparse(href).netloc.lower()
            if (
                not host
                or "bing.com" in host
                or "google.com" in host
                or host.endswith("w3.org")
                or host.endswith("live.com")
                or "schemas." in host
            ):
                continue

            item = {"title": "", "url": href, "public_emails": page_public_emails}
            if item not in results:
                results.append(item)

            if len(results) >= max_results:
                return results

        if results:
            return results

    return []


def extract_public_emails(text):
    """Estrae email presenti nel contenuto pubblico già ricevuto."""
    if not text:
        return []

    found = set(re.findall(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text,
        re.I,
    ))
    return sorted(found, key=str.lower)


def extract_domains_from_urls(urls):
    domains = set()

    for url in urls:
        try:
            host = urllib.parse.urlparse(url).hostname
            if not host:
                continue

            host = host.lower().lstrip("www.")
            if "." in host and not re.fullmatch(r"\d+(?:\.\d+){3}", host):
                domains.add(host)
        except Exception:
            pass

    return sorted(domains)


def analyze_public_correlations(username=None, seed_email=None):
    """Correla username/email con sole fonti web pubbliche.
    Non prova a ricavare l'email privata usata per registrare un account.
    """
    queries = []

    if username:
        q = username.strip()
        queries.extend([
            f'"{q}" email',
            f'"{q}" contact',
            f'"{q}" official',
        ])

    if seed_email:
        queries.append(f'"{seed_email.strip().lower()}"')

    all_results = []
    public_emails = set()
    domains = set()

    for query in queries:
        for item in public_web_search(query, max_results=5):
            item["query"] = query

            if item not in all_results:
                all_results.append(item)

            # Cerca email anche nel contenuto pubblico del motore di ricerca.
            public_emails.update(item.get("public_emails", []))
            public_emails.update(extract_public_emails(
                item.get("title", "") + " " + item.get("url", "")
            ))
            candidate_domains = extract_domains_from_urls([item["url"]])
            token = (username or "").strip().lower().lstrip("@")
            for candidate in candidate_domains:
                if not token or token in candidate:
                    domains.add(candidate)

    # Controllo diretto di pochi domini pertinenti già scoperti.
    # Questo serve a trovare eventuali email pubblicate sulle pagine ufficiali.
    for candidate in list(domains)[:5]:
        page_status, page_body, _ = http_get(
            f"https://{candidate}",
            timeout=5,
        )
        if page_status and page_body:
            public_emails.update(extract_public_emails(page_body))

    for email in public_emails:
        domains.add(email.rsplit("@", 1)[-1].lower())

    # I provider comuni non vengono trattati come dominio dell'organizzazione
    # se non compaiono come dominio di un'email pubblica.
    public_email_domains = {
        e.rsplit("@", 1)[-1].lower() for e in public_emails
    }
    for provider in COMMON_EMAIL_PROVIDERS:
        if provider in domains and provider not in public_email_domains:
            domains.discard(provider)

    return {
        "queries": queries,
        "results": all_results,
        "public_emails_found": sorted(public_emails, key=str.lower),
        "public_domains_found": sorted(domains),
    }


def analyze_phone(phone):
    """Analizza un numero di telefono limitandosi a informazioni pubblicamente indicizzate.
    Non effettua reverse lookup privati e non attribuisce il numero a una persona.
    """
    raw = phone.strip()
    compact = re.sub(r"[^0-9+]", "", raw)
    digits = re.sub(r"\\D", "", compact)
    valid_format = bool(re.fullmatch(r"\\+?[0-9]{7,15}", compact))

    normalized = compact
    if compact.startswith("00"):
        normalized = "+" + compact[2:]
    elif compact.startswith("+"):
        normalized = compact

    queries = []
    if valid_format:
        queries = [f'"{normalized}"']
        if digits and digits != normalized.lstrip("+"):
            queries.append(f'"{digits}"')

    public_results = []
    for query in queries:
        for item in public_web_search(query, max_results=5):
            item["query"] = query
            if item not in public_results:
                public_results.append(item)

    return {
        "phone": raw,
        "normalized": normalized,
        "digits": digits,
        "format_valid": valid_format,
        "public_search_links": [
            {
                "source": "Google",
                "url": f"https://www.google.com/search?q=%22{urllib.parse.quote(normalized)}%22",
            },
            {
                "source": "Bing",
                "url": f"https://www.bing.com/search?q=%22{urllib.parse.quote(normalized)}%22",
            },
        ] if valid_format else [],
        "public_results": public_results,
    }


def analyze_email(email):
    email = email.strip().lower()

    result = {
        "email": email,
        "format_valid": bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)),
        "domain": None,
        "provider_hint": None,
        "public_search_links": [],
    }

    if "@" not in email:
        return result

    local, domain = email.rsplit("@", 1)
    result["domain"] = domain

    if domain in COMMON_EMAIL_PROVIDERS:
        result["provider_hint"] = domain

    encoded = urllib.parse.quote(email)

    # These are search destinations/queries, not claims that the email exists there.
    result["public_search_links"] = [
        {
            "source": "Google",
            "url": f"https://www.google.com/search?q=%22{encoded}%22",
        },
        {
            "source": "Bing",
            "url": f"https://www.bing.com/search?q=%22{encoded}%22",
        },
    ]

    return result


def check_domain(domain):
    domain = domain.strip()
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.split("/")[0].lower()

    print(f"\n[*] Analisi dominio: {domain}")

    web = []

    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        status, _, headers = http_get(url)

        if status:
            print(f"[+] {url} -> HTTP {status}")
            web.append({
                "url": url,
                "status": status,
                "server": headers.get("Server"),
                "content_type": headers.get("Content-Type"),
            })
        else:
            print(f"[-] {url} -> nessuna risposta")

    dns = dns_lookup(domain)
    resolved = resolve_domain(domain)
    rdap = rdap_lookup(domain)
    tls = tls_certificate(domain)

    if resolved["addresses"]:
        print("[+] IP pubblici risolti: " + ", ".join(resolved["addresses"]))
    else:
        print("[-] Nessun IP risolto")

    return {
        "domain": domain,
        "web": web,
        "dns": dns,
        "resolved_addresses": resolved["addresses"],
        "resolution_errors": resolved["errors"],
        "rdap": rdap,
        "tls_certificate": tls,
    }


def build_report(username=None, email=None, phone=None, domains=None):
    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target": {},
        "username_results": [],
        "email_results": [],
        "phone_results": [],
        "public_correlations": {},
        "domain_results": [],
        "limitations": [
            "Gli IP riportati sono quelli pubblicamente risolti da DNS.",
            "Un'email non permette di ricavare automaticamente l'IP privato o il nome del dispositivo del proprietario.",
            "Eventuali dati dispositivo vengono riportati solo se una fonte pubblica analizzata li espone esplicitamente.",
        ],
    }

    if username:
        data["target"]["username"] = username
        data["username_results"] = check_username(username)

    if email:
        data["target"]["email"] = email
        email_result = analyze_email(email)
        data["email_results"].append(email_result)

        if email_result["domain"] and email_result["domain"] not in (domains or []):
            domains = list(domains or [])
            domains.append(email_result["domain"])

    if phone:
        data["target"]["phone"] = phone
        data["phone_results"].append(analyze_phone(phone))

    # Correlazione aggiuntiva: solo informazioni realmente pubbliche.
    if username or email:
        correlation = analyze_public_correlations(
            username=username,
            seed_email=email,
        )
        data["public_correlations"] = correlation

        discovered_emails = correlation.get("public_emails_found", [])
        discovered_domains = correlation.get("public_domains_found", [])

        for found_email in discovered_emails:
            if not any(x.get("email") == found_email for x in data["email_results"]):
                data["email_results"].append(analyze_email(found_email))

        domains = list(domains or [])
        for discovered_domain in discovered_domains:
            if discovered_domain not in domains:
                domains.append(discovered_domain)

    for domain in domains or []:
        data["domain_results"].append(check_domain(domain))

    return data


def create_pdf(data):
    os.makedirs(REPORT_DIR, exist_ok=True)

    target = data.get("target", {})
    search_value = (
        target.get("username")
        or target.get("email")
        or target.get("domain")
        or "osint_report"
    )

    search_value = str(search_value).strip().lstrip("@")
    search_value = re.sub(r"https?://", "", search_value, flags=re.I)
    search_value = re.sub(r"[^A-Za-z0-9._@-]+", "_", search_value)
    search_value = re.sub(r"_+", "_", search_value).strip("._-")
    search_value = search_value[:80] or "osint_report"

    base = f"{datetime.now().strftime('%Y-%m-%d')}_{search_value}"
    filename = os.path.join(REPORT_DIR, f"{base}.pdf")

    index = 2
    while os.path.exists(filename):
        filename = os.path.join(REPORT_DIR, f"{base}_{index}.pdf")
        index += 1

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=38,
        leftMargin=38,
        topMargin=38,
        bottomMargin=38,
    )

    styles = getSampleStyleSheet()

    title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=19,
        spaceAfter=18,
    )

    heading = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=13,
        spaceAfter=7,
    )

    normal = ParagraphStyle(
        "ReportNormal",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=12,
    )

    small = ParagraphStyle(
        "ReportSmall",
        parent=normal,
        fontSize=7.5,
        leading=10,
    )

    story = [
        Paragraph("OSINT SELF-AUDIT REPORT", title),
        Paragraph(
            f"Generato: {data['generated_at']}",
            normal,
        ),
        Spacer(1, 12),
    ]

    story.append(Paragraph("TARGET", heading))

    rows = [["Campo", "Valore"]]

    for key, value in data["target"].items():
        rows.append([key, str(value)])

    if len(rows) > 1:
        table = Table(rows, colWidths=[110, 360])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)

    story.append(Paragraph("USERNAME / SOCIAL", heading))

    if data["username_results"]:
        rows = [["Piattaforma", "Stato", "URL"]]

        for item in data["username_results"]:
            rows.append([
                item["platform"],
                item["status"],
                item["url"],
            ])

        table = Table(rows, colWidths=[85, 80, 305])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("Nessuno username analizzato.", normal))

    story.append(Paragraph("EMAIL", heading))

    if data["email_results"]:
        for item in data["email_results"]:
            story.append(Paragraph(
                f"<b>Email:</b> {item['email']}",
                normal,
            ))
            story.append(Paragraph(
                f"<b>Formato:</b> {'valido' if item['format_valid'] else 'non valido'}",
                normal,
            ))
            story.append(Paragraph(
                f"<b>Dominio:</b> {item.get('domain') or 'n/d'}",
                normal,
            ))
            story.append(Paragraph(
                f"<b>Provider:</b> {item.get('provider_hint') or 'non determinato'}",
                normal,
            ))

            story.append(Paragraph(
                "<b>Ricerche pubbliche:</b>",
                normal,
            ))

            for link in item.get("public_search_links", []):
                story.append(Paragraph(
                    f"- {link['source']}: {link['url']}",
                    small,
                ))
    else:
        story.append(Paragraph("Nessuna email analizzata.", normal))

    correlation = data.get("public_correlations", {})
    if correlation:
        story.append(Paragraph("TELEFONO", heading))

    if data.get("phone_results"):
        for item in data["phone_results"]:
            story.append(Paragraph(f"<b>Numero:</b> {item['phone']}", normal))
            story.append(Paragraph(f"<b>Normalizzato:</b> {item['normalized']}", normal))
            story.append(Paragraph(
                f"<b>Formato:</b> {'valido' if item['format_valid'] else 'non valido'}",
                normal,
            ))
            story.append(Paragraph(
                "<b>Nota:</b> vengono riportate solo occorrenze pubblicamente indicizzate; "
                "il report non attribuisce il numero a una persona e non effettua reverse lookup privati.",
                small,
            ))
            if item.get("public_results"):
                story.append(Paragraph("<b>Risultati web pubblici:</b>", normal))
                for result in item["public_results"][:15]:
                    story.append(Paragraph(
                        f"- {result.get('title') or result.get('url')} → {result.get('url')}",
                        small,
                    ))
            else:
                story.append(Paragraph("Nessuna occorrenza pubblica rilevata.", normal))
    else:
        story.append(Paragraph("Nessun numero di telefono analizzato.", normal))

    story.append(Paragraph("CORRELAZIONI WEB PUBBLICHE", heading))

    emails = correlation.get("public_emails_found", [])
    domains = correlation.get("public_domains_found", [])
    queries = correlation.get("queries", [])
    results = correlation.get("results", [])

    story.append(Paragraph(
        f"<b>Email pubbliche trovate:</b> {', '.join(emails) if emails else 'nessuna'}",
        normal,
    ))
    story.append(Paragraph(
        f"<b>Domini pubblicamente rilevati:</b> {', '.join(domains) if domains else 'nessuno'}",
        normal,
    ))

    if results:
        story.append(Paragraph("<b>Fonti web analizzate:</b>", normal))
        for item in results[:15]:
            story.append(Paragraph(
                f"- {item.get('title') or item.get('url')} → {item.get('url')}",
                small,
            ))

    story.append(Paragraph("DOMINI / DNS / RETE", heading))

    if data["domain_results"]:
        for item in data["domain_results"]:
            story.append(Paragraph(
                f"<b>Dominio:</b> {item['domain']}",
                normal,
            ))

            for web in item["web"]:
                story.append(Paragraph(
                    f"- {web['url']} → HTTP {web['status']} "
                    f"(Server: {web.get('server') or 'n/d'})",
                    small,
                ))

            dns = item["dns"]

            for record_type in ("A", "AAAA", "MX", "NS"):
                values = dns.get(record_type, [])
                if values:
                    story.append(Paragraph(
                        f"<b>{record_type}:</b> {', '.join(values)}",
                        small,
                    ))

            ips = item.get("resolved_addresses", [])
            story.append(Paragraph(
                f"<b>IP pubblicamente risolti:</b> "
                f"{', '.join(ips) if ips else 'nessuno'}",
                small,
            ))

            rdap = item.get("rdap", {})
            if rdap.get("ldhName"):
                story.append(Paragraph(
                    f"<b>RDAP:</b> {rdap.get('ldhName')} "
                    f"(HTTP {rdap.get('status')})",
                    small,
                ))

            tls = item.get("tls_certificate", {})
            if tls.get("subject"):
                story.append(Paragraph(
                    f"<b>TLS subject:</b> {tls['subject']}",
                    small,
                ))

            if tls.get("issuer"):
                story.append(Paragraph(
                    f"<b>TLS issuer:</b> {tls['issuer']}",
                    small,
                ))

            sans = tls.get("san", [])
            if sans:
                story.append(Paragraph(
                    f"<b>TLS SAN:</b> {', '.join(sans)}",
                    small,
                ))

            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("Nessun dominio analizzato.", normal))

    story.append(Paragraph("LIMITAZIONI", heading))

    for limitation in data["limitations"]:
        story.append(Paragraph(
            f"- {limitation}",
            normal,
        ))

    story.append(Spacer(1, 15))

    story.append(Paragraph(
        "Il report contiene risultati ottenuti da sorgenti pubbliche "
        "o da risoluzioni DNS/TLS eseguite dal programma. "
        "La presenza di un dominio o di un IP non identifica "
        "necessariamente una persona o un dispositivo specifico.",
        small,
    ))

    # Sintesi conclusiva in linguaggio semplice, senza trasformare
    # risposte HTTP o link di ricerca in conferme non dimostrate.
    story.append(Spacer(1, 12))
    story.append(Paragraph("IN BREVE — COSA SIGNIFICA", heading))

    username_items = data.get("username_results", [])
    username_found = sum(1 for item in username_items if item.get("status") == "FOUND")
    username_total = len(username_items)

    email_items = data.get("email_results", [])
    valid_emails = sum(1 for item in email_items if item.get("format_valid"))
    phone_items = data.get("phone_results", [])
    valid_phones = sum(1 for item in phone_items if item.get("format_valid"))
    phone_public_hits = sum(len(item.get("public_results", [])) for item in phone_items)
    domain_items = data.get("domain_results", [])
    responsive_domains = sum(1 for item in domain_items if item.get("web"))
    resolved_ips = sum(len(item.get("resolved_addresses", [])) for item in domain_items)
    public_emails = len(correlation.get("public_emails_found", []))
    public_domains = len(correlation.get("public_domains_found", []))

    plain_lines = []
    if username_total:
        plain_lines.append(
            f"Username: il programma ha rilevato risposte compatibili su "
            f"{username_found} piattaforme su {username_total}. Sono indizi da "
            "controllare manualmente: una risposta del sito non conferma da sola "
            "che il profilo appartenga alla persona cercata."
        )
    if email_items:
        plain_lines.append(
            f"Email: sono state analizzate {len(email_items)} email; "
            f"{valid_emails} hanno un formato valido. I collegamenti di ricerca "
            "indicano dove fare controlli pubblici, non dimostrano che l'email "
            "sia stata trovata online o coinvolta in una violazione."
        )
    if phone_items:
        plain_lines.append(
            f"Telefono: {valid_phones} numeri su {len(phone_items)} hanno un formato "
            f"valido e sono stati raccolti {phone_public_hits} risultati web pubblici. "
            "Questi risultati non provano a chi appartenga il numero."
        )
    if domain_items:
        plain_lines.append(
            f"Domini: sono stati esaminati {len(domain_items)} domini; "
            f"{responsive_domains} hanno risposto via HTTP/HTTPS e sono stati "
            f"risolti {resolved_ips} indirizzi IP pubblici. Sono informazioni tecniche "
            "sul dominio, non l'identificazione di una persona."
        )
    if public_emails or public_domains:
        plain_lines.append(
            f"Correlazioni pubbliche: sono stati individuati {public_emails} "
            f"indirizzi email e {public_domains} domini nei risultati web analizzati. "
            "La loro pertinenza va verificata prima di considerarli collegati al target."
        )
    if not plain_lines:
        plain_lines.append(
            "Non sono stati forniti elementi sufficienti per effettuare controlli. "
            "Il report non permette quindi di trarre conclusioni sul target."
        )
    plain_lines.append(
        "In sintesi: il documento raccoglie tracce e informazioni tecniche pubbliche. "
        "Non è una prova certa dell'identità di una persona, né garantisce che "
        "l'assenza di risultati significhi assenza di informazioni online."
    )
    for line in plain_lines:
        story.append(Paragraph("• " + line, normal))

    doc.build(story)

    return filename


def run_scan(username=None, email=None, phone=None, domains=None):
    print("\n[*] Avvio analisi...\n")

    data = build_report(
        username=username,
        email=email,
        phone=phone,
        domains=domains,
    )

    pdf_file = create_pdf(data)

    # Ordina i report appena creati e rimuove quelli con piu di 30 giorni.
    run_report_manager()

    print("\n================================")
    print("       SCANSIONE COMPLETATA")
    print("================================")
    print(f"[+] PDF:  {pdf_file}")
    print()


def terminal_style(text, color):
    palette = {
        "cyan": "\033[96m", "blue": "\033[94m",
        "green": "\033[92m", "green_bold": "\033[1;92m", "yellow": "\033[93m",
        "red": "\033[91m", "red_bold": "\033[1;91m", "white_bold": "\033[1;97m", "muted": "\033[1;97m",
        "bold": "\033[1m", "reset": "\033[0m",
    }
    if not os.getenv("NO_COLOR") and os.getenv("TERM") != "dumb":
        return f"{palette.get(color, '')}{text}{palette['reset']}"
    return text


def print_banner(section="MAIN MENU"):
    # Banner FIGlet grande, con timestamp in stile console professionale.
    stamp = datetime.now().strftime("%H:%M:%S")
    try:
        art = subprocess.check_output(
            ["figlet", "-f", "banner", "OSINT SELF-AUDIT"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).rstrip("\n")
        lines = art.splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        lines = ["  ____  _____ _____ _   _ _____", " OSINT SELF-AUDIT"]

    print()
    for line in lines:
        print(terminal_style(f"[{stamp}] {line}", "green_bold"))
    print(terminal_style(f"[{stamp}]  {section}  |  PUBLIC-SOURCE RESEARCH", "red_bold"))
    print()


def print_menu(items):
    print(terminal_style("  ┌────────────────────────────────────────────────────────┐", "red_bold"))
    for key, label, detail in items:
        row = f"  [{key}]  {label:<35}{detail:>14}"
        print(terminal_style("  │ ", "red_bold") + terminal_style(row[:57].ljust(57), "white_bold") + terminal_style(" │", "red_bold"))
    print(terminal_style("  └────────────────────────────────────────────────────────┘", "red_bold"))
    print()


def interactive_mode():
    while True:
        print_banner("ANALYSIS CONSOLE")
        print_menu([
            ("1", "Cerca username", "SOCIAL"),
            ("2", "Analizza email", "EMAIL"),
            ("3", "Analizza dominio", "DOMAIN"),
            ("4", "Analizza numero di telefono", "PHONE"),
            ("5", "Username + email", "COMBO"),
            ("6", "Username + email + dominio", "FULL"),
            ("7", "Esci", "QUIT"),
        ])

        choice = input(terminal_style("Scelta: ", "white_bold")).strip()

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
            phone = input("Inserisci numero di telefono: ").strip()
            if phone:
                run_scan(phone=phone)
            else:
                print("[!] Numero di telefono vuoto.")

        elif choice == "5":
            username = input("Inserisci username: ").strip()
            email = input("Inserisci email: ").strip()

            if username or email:
                run_scan(
                    username=username or None,
                    email=email or None,
                )
            else:
                print("[!] Devi inserire almeno un dato.")

        elif choice == "6":
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

        elif choice == "7":
            print("[+] Uscita.")
            break

        else:
            print("[!] Scelta non valida.")


def terminal_login():
    """Accesso locale del terminale con le stesse credenziali della GUI web."""
    user = os.getenv("TOOL_AUTH_USER", os.getenv("OSINT_GUI_USER", "Admin"))
    password = os.getenv("TOOL_AUTH_PASS", os.getenv("OSINT_GUI_PASSWORD", ""))

    while True:
        print(terminal_style("ACCESSO TERMINALE", "green_bold"))
        print()
        entered_user = input(terminal_style("Username: ", "white_bold")).strip()
        entered_password = getpass.getpass(terminal_style("Password: ", "white_bold"))

        if entered_user == user and entered_password == password:
            print(terminal_style("[+] Accesso autorizzato.", "green_bold"))
            return

        print(terminal_style("[!] Username o password errati.", "red_bold"))
        print()


def cli_mode():
    parser = argparse.ArgumentParser(
        description="OSINT Self-Audit Tool"
    )

    parser.add_argument(
        "--username",
        help="Username da analizzare",
    )

    parser.add_argument(
        "--email",
        help="Email da analizzare",
    )

    parser.add_argument(
        "--domain",
        action="append",
        help="Dominio da analizzare (ripetibile)",
    )

    parser.add_argument(
        "--phone",
        help="Numero di telefono da analizzare", 
    )

    args = parser.parse_args()

    if not any([
        args.username,
        args.email,
        args.domain,
        args.phone,
    ]):
        print("\033[2J\033[H", end="", flush=True)
        print_banner("STARTUP")
        print_menu([
            ("1", "Versione terminale", "CLI"),
            ("2", "Versione GUI web", "WEB"),
            ("3", "Esci", "QUIT"),
        ])

        while True:
            choice = input(terminal_style("Scelta: ", "white_bold")).strip()

            if choice == "1":
                print("\033[2J\033[H", end="", flush=True)
                terminal_login()
                print("\033[2J\033[H", end="", flush=True)
                interactive_mode()
                return

            if choice == "2":
                try:
                    from osint_gui import start
                    start()
                except Exception as exc:
                    print(f"[!] Impossibile avviare la GUI: {exc}")
                return

            if choice == "3":
                print("[+] Uscita.")
                return

            print("[!] Scelta non valida.")

    run_scan(
        username=args.username,
        email=args.email,
        phone=args.phone,
        domains=args.domain,
    )


if __name__ == "__main__":
    cli_mode()
