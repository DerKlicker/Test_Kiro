"""Kleine Weboberfläche, um markierte Zutaten aus einer Notion-Datenbank
nach Bring! zu übertragen.

Start:
    python app.py
Danach im Browser öffnen:  http://127.0.0.1:5000

Zugangsdaten können zentral als Umgebungsvariablen hinterlegt werden
(NOTION_TOKEN, NOTION_DATABASE_ID, BRING_EMAIL, BRING_PASSWORD, BRING_LIST,
CA_CERT_PATH, DISABLE_SSL_VERIFY). Sind sie gesetzt, überträgt die Seite beim
Aufruf automatisch. Fehlende Werte können über das Formular ergänzt werden.
"""

from __future__ import annotations

import os

from flask import Flask, render_template, request

from bring_helper import send_items
from notion_helper import NotionHelper

app = Flask(__name__)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


def _env_prefill() -> dict:
    """Vorbelegung der Formularfelder aus den Umgebungsvariablen.
    Das Passwort wird NICHT an das Formular zurückgegeben (nur Platzhalter),
    ist aber serverseitig über BRING_PASSWORD verfügbar."""
    return {
        "notion_token": _env("NOTION_TOKEN"),
        "database_id": _env("NOTION_DATABASE_ID"),
        "bring_email": _env("BRING_EMAIL"),
        "bring_list": _env("BRING_LIST"),
        "ca_cert_path": _env("CA_CERT_PATH"),
        "disable_ssl": _env_bool("DISABLE_SSL_VERIFY"),
        # Nur ein Hinweis, ob zentral ein Passwort hinterlegt ist:
        "has_env_password": bool(_env("BRING_PASSWORD")),
    }


def _credentials_complete(creds: dict) -> bool:
    """Prüft, ob alle Pflichtfelder vorhanden sind (für den Auto-/Button-Lauf)."""
    return all(
        creds.get(k)
        for k in ("notion_token", "database_id", "bring_email", "bring_password")
    )


def _do_transfer(creds: dict) -> tuple[dict | None, str | None]:
    """Führt die eigentliche Übertragung aus.

    Gibt (result, error) zurück – genau eines ist gesetzt.
    `creds` enthält: notion_token, database_id, bring_email, bring_password,
    bring_list, ca_cert_path, verify_ssl.
    """
    try:
        notion = NotionHelper(
            creds["notion_token"],
            creds["database_id"],
            ca_cert_path=creds.get("ca_cert_path") or None,
            verify_ssl=creds.get("verify_ssl", True),
        )
        items = notion.fetch_checked_items()

        if not items:
            return (
                {
                    "added": [],
                    "skipped": [],
                    "reset": [],
                    "list_name": "",
                    "message": "Es sind keine Zutaten mit gesetzter Checkbox vorhanden.",
                },
                None,
            )

        payload = [(it.name, it.specification) for it in items]

        bring_result = send_items(
            email=creds["bring_email"],
            password=creds["bring_password"],
            items=payload,
            list_name=creds.get("bring_list") or None,
            ca_cert_path=creds.get("ca_cert_path") or None,
            verify_ssl=creds.get("verify_ssl", True),
        )

        # Checkboxen für alle verarbeiteten Artikel (neu ODER schon vorhanden)
        # zurücksetzen.
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
        return result, None

    except Exception as exc:  # noqa: BLE001 - Fehler soll in der UI sichtbar sein
        return None, f"Fehler bei der Übertragung: {exc}"


@app.route("/", methods=["GET"])
def index():
    """Startseite.

    Sind alle Zugangsdaten zentral als Umgebungsvariablen hinterlegt, wird
    standardmäßig direkt übertragen (gewünschtes Verhalten für den
    Notion-Button bzw. den Aufruf per URL). Das lässt sich mit ?noauto=1
    unterdrücken, um nur das Formular zu sehen."""
    prefill = _env_prefill()
    suppress_auto = request.args.get("noauto") in ("1", "true", "yes")

    env_creds = {
        "notion_token": _env("NOTION_TOKEN"),
        "database_id": _env("NOTION_DATABASE_ID"),
        "bring_email": _env("BRING_EMAIL"),
        "bring_password": _env("BRING_PASSWORD"),
        "bring_list": _env("BRING_LIST"),
        "ca_cert_path": _env("CA_CERT_PATH"),
        "verify_ssl": not _env_bool("DISABLE_SSL_VERIFY"),
    }

    if not suppress_auto and _credentials_complete(env_creds):
        result, error = _do_transfer(env_creds)
        return render_template(
            "index.html", prefill=prefill, result=result, error=error, auto_ran=True
        )

    # Sonst nur die Seite mit (teilweise) vorausgefüllten Feldern anzeigen.
    return render_template(
        "index.html", prefill=prefill, result=None, error=None, auto_ran=False
    )


@app.route("/run", methods=["GET", "POST"])
def run():
    """Direkter Auslöser (z.B. per Notion-Button als "Open link").

    Verwendet die zentral hinterlegten Zugangsdaten und überträgt sofort.
    Zeigt anschließend die Ergebnisseite an."""
    prefill = _env_prefill()
    env_creds = {
        "notion_token": _env("NOTION_TOKEN"),
        "database_id": _env("NOTION_DATABASE_ID"),
        "bring_email": _env("BRING_EMAIL"),
        "bring_password": _env("BRING_PASSWORD"),
        "bring_list": _env("BRING_LIST"),
        "ca_cert_path": _env("CA_CERT_PATH"),
        "verify_ssl": not _env_bool("DISABLE_SSL_VERIFY"),
    }

    if not _credentials_complete(env_creds):
        error = (
            "Keine (vollständigen) Zugangsdaten hinterlegt. Bitte trage sie als "
            "Umgebungsvariablen ein (NOTION_TOKEN, NOTION_DATABASE_ID, "
            "BRING_EMAIL, BRING_PASSWORD) oder nutze das Formular auf der Startseite."
        )
        return render_template(
            "index.html", prefill=prefill, result=None, error=error, auto_ran=False
        )

    result, error = _do_transfer(env_creds)
    return render_template(
        "index.html", prefill=prefill, result=result, error=error, auto_ran=True
    )


@app.route("/transfer", methods=["POST"])
def transfer():
    """Übertragung über das Formular (manuelle Eingabe / Überschreiben)."""
    bring_password = request.form.get("bring_password", "")
    # Ist im Formular kein Passwort eingetragen, auf das zentrale (ENV) zurückfallen.
    if not bring_password:
        bring_password = _env("BRING_PASSWORD")

    creds = {
        "notion_token": request.form.get("notion_token", "").strip(),
        "database_id": request.form.get("database_id", "").strip(),
        "bring_email": request.form.get("bring_email", "").strip(),
        "bring_password": bring_password,
        "bring_list": request.form.get("bring_list", "").strip(),
        "ca_cert_path": request.form.get("ca_cert_path", "").strip(),
        "verify_ssl": request.form.get("disable_ssl") != "on",
    }

    prefill = {
        "notion_token": creds["notion_token"],
        "database_id": creds["database_id"],
        "bring_email": creds["bring_email"],
        "bring_list": creds["bring_list"],
        "ca_cert_path": creds["ca_cert_path"],
        "disable_ssl": not creds["verify_ssl"],
        "has_env_password": bool(_env("BRING_PASSWORD")),
    }

    missing = [
        label
        for label, value in [
            ("Notion-Token", creds["notion_token"]),
            ("Notion-Datenbank-ID", creds["database_id"]),
            ("Bring!-E-Mail", creds["bring_email"]),
            ("Bring!-Passwort", creds["bring_password"]),
        ]
        if not value
    ]
    if missing:
        error = "Bitte fülle alle Pflichtfelder aus: " + ", ".join(missing)
        return render_template(
            "index.html", prefill=prefill, result=None, error=error, auto_ran=False
        )

    result, error = _do_transfer(creds)
    return render_template(
        "index.html", prefill=prefill, result=result, error=error, auto_ran=False
    )


if __name__ == "__main__":
    # Lokaler Entwicklungsstart (nicht für den Dauerbetrieb).
    # Im Container/Produktion wird stattdessen Gunicorn verwendet (siehe Dockerfile).
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
