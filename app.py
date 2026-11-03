"""Kleine Weboberfläche, um markierte Zutaten aus einer Notion-Datenbank
nach Bring! zu übertragen.

Start:
    python app.py
Danach im Browser öffnen:  http://127.0.0.1:5000
"""

from __future__ import annotations

import os

from flask import Flask, render_template, request

from bring_helper import send_items
from notion_helper import NotionHelper

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    # Vorbelegung aus Umgebungsvariablen (optional / bequem beim Testen).
    prefill = {
        "notion_token": os.environ.get("NOTION_TOKEN", ""),
        "database_id": os.environ.get("NOTION_DATABASE_ID", ""),
        "bring_email": os.environ.get("BRING_EMAIL", ""),
        "bring_list": os.environ.get("BRING_LIST", ""),
        "ca_cert_path": os.environ.get("CA_CERT_PATH", ""),
        "disable_ssl": os.environ.get("DISABLE_SSL_VERIFY", "").lower() in ("1", "true", "yes"),
    }
    return render_template("index.html", prefill=prefill, result=None, error=None)


@app.route("/transfer", methods=["POST"])
def transfer():
    notion_token = request.form.get("notion_token", "").strip()
    database_id = request.form.get("database_id", "").strip()
    bring_email = request.form.get("bring_email", "").strip()
    bring_password = request.form.get("bring_password", "")
    bring_list = request.form.get("bring_list", "").strip() or None
    ca_cert_path = request.form.get("ca_cert_path", "").strip() or None
    disable_ssl = request.form.get("disable_ssl") == "on"
    verify_ssl = not disable_ssl

    prefill = {
        "notion_token": notion_token,
        "database_id": database_id,
        "bring_email": bring_email,
        "bring_list": bring_list or "",
        "ca_cert_path": ca_cert_path or "",
        "disable_ssl": disable_ssl,
    }

    # Pflichtfelder prüfen.
    missing = [
        label
        for label, value in [
            ("Notion-Token", notion_token),
            ("Notion-Datenbank-ID", database_id),
            ("Bring!-E-Mail", bring_email),
            ("Bring!-Passwort", bring_password),
        ]
        if not value
    ]
    if missing:
        error = "Bitte fülle alle Pflichtfelder aus: " + ", ".join(missing)
        return render_template("index.html", prefill=prefill, result=None, error=error)

    try:
        notion = NotionHelper(
            notion_token,
            database_id,
            ca_cert_path=ca_cert_path,
            verify_ssl=verify_ssl,
        )
        items = notion.fetch_checked_items()

        if not items:
            result = {
                "added": [],
                "skipped": [],
                "reset": [],
                "list_name": "",
                "message": "Es sind keine Zutaten mit gesetzter Checkbox vorhanden.",
            }
            return render_template("index.html", prefill=prefill, result=result, error=None)

        # (name, specification)-Tupel für Bring! aufbereiten.
        payload = [(it.name, it.specification) for it in items]

        bring_result = send_items(
            email=bring_email,
            password=bring_password,
            items=payload,
            list_name=bring_list,
            ca_cert_path=ca_cert_path,
            verify_ssl=verify_ssl,
        )

        # Checkboxen nur für tatsächlich verarbeitete Artikel zurücksetzen
        # (hinzugefügt ODER bereits vorhanden/übersprungen -> beides ist "erledigt").
        processed_names = set(bring_result.added) | set(bring_result.skipped)
        reset: list[str] = []
        for it in items:
            if it.name in processed_names:
                notion.reset_checkbox(it.page_id)
                reset.append(it.name)

        result = {
            "added": [i.display for i in items if i.name in set(bring_result.added)],
            "skipped": [i.display for i in items if i.name in set(bring_result.skipped)],
            "reset": reset,
            "list_name": bring_result.list_name,
            "message": None,
        }
        return render_template("index.html", prefill=prefill, result=result, error=None)

    except Exception as exc:  # noqa: BLE001 - Fehler soll in der UI sichtbar sein
        error = f"Fehler bei der Übertragung: {exc}"
        return render_template("index.html", prefill=prefill, result=None, error=error)


if __name__ == "__main__":
    # Lokaler Entwicklungsstart (nicht für den Dauerbetrieb).
    # Im Container/Produktion wird stattdessen Gunicorn verwendet (siehe Dockerfile).
    # HOST/PORT sind per Umgebungsvariable überschreibbar.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
