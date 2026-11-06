# Notion → Bring! Übertragung

Ein kleines Python-Tool mit Weboberfläche, das markierte Zutaten aus einer
Notion-Datenbank automatisch auf eine **Bring!**-Einkaufsliste überträgt.

## Funktionsweise

1. In der Notion-Datenbank **„Gesamt Event Ablaufplan“** werden die gewünschten
   Zutaten über die Checkbox **„An bring senden“** markiert.
2. Du startest das Tool und öffnest die Weboberfläche im Browser.
3. Du gibst deine Zugangsdaten ein (Notion & Bring!) und klickst auf
   **„An Bring! übertragen“**.
4. Das Tool
   - liest alle Einträge mit gesetzter Checkbox, deren Name mit `Z-` beginnt (Zutaten),
   - entfernt das `Z-`-Präfix für den Bring!-Artikelnamen (`Z-Milch` → `Milch`),
   - setzt die Menge aus **Gesamtmenge** + Einheit aus **Menge pro Gericht** zusammen
     (z.B. Gesamtmenge `5750` + `250 ml` → Spezifikation **`5750 ml`**),
   - überträgt die Artikel nach Bring! (bereits vorhandene werden übersprungen),
   - **setzt danach die Checkbox automatisch wieder zurück.**

> **Hinweis:** Rezepte (Einträge mit `R-`) werden ignoriert – nur Zutaten (`Z-`)
> werden übertragen.

## Voraussetzungen

- Python 3.10 oder neuer
- Ein Notion-Account mit der Datenbank „Gesamt Event Ablaufplan“
- Ein Bring!-Account

## Installation

```bash
# (empfohlen) virtuelle Umgebung anlegen
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

## Notion vorbereiten

1. Eine Notion-Integration erstellen: <https://www.notion.so/my-integrations>
   → **„New integration“** → Token kopieren (beginnt mit `ntn_` bzw. `secret_`).
2. Die Datenbank mit der Integration teilen:
   In Notion die Datenbank öffnen → **„•••“** (oben rechts) → **„Connections“ /
   „Verbindungen hinzufügen“** → deine Integration auswählen.
3. Die **Datenbank-ID** aus der URL der Datenbank entnehmen:
   `https://www.notion.so/<WORKSPACE>/<DATENBANK-ID>?v=...`
   → die 32-stellige ID (mit oder ohne Bindestriche) ist die `NOTION_DATABASE_ID`.

Stelle sicher, dass die Datenbank folgende Spalten besitzt (Namen müssen exakt passen –
andernfalls in `notion_helper.py` oben anpassen):

| Spalte             | Typ                      | Zweck                                   |
|--------------------|--------------------------|-----------------------------------------|
| `Name`             | Titel                    | Artikelname mit `Z-`/`R-`-Präfix        |
| `Gesamtmenge`      | Zahl / Formel            | Menge ohne Einheit                      |
| `Menge pro Gericht`| Auswahl (Select) / Text  | Einheit wird hieraus gelesen (z.B. `g`) |
| `An bring senden`  | Checkbox                 | löst die Übertragung aus                |

## Starten

```bash
python app.py
```

Danach im Browser öffnen: **<http://127.0.0.1:5000>**

Zugangsdaten eingeben und auf **„An Bring! übertragen“** klicken. Fertig!

### Optional: Felder vorbelegen

Damit du die Felder nicht jedes Mal eintippen musst, kannst du `.env.example`
nach `.env` kopieren und Werte eintragen (Passwort wird aus Sicherheitsgründen
**nicht** vorbelegt). Die `.env` wird nicht ins Git eingecheckt.

## Firmennetzwerk / SSL-Zertifikatsfehler

Im Firmennetz (oder bei Antivirus mit HTTPS-Scan) kann folgender Fehler auftreten:

```
[SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate in certificate chain
```

Ursache: Eine Firewall/ein Proxy bricht den HTTPS-Verkehr auf und präsentiert
ein eigenes Zertifikat, das Python nicht kennt. Es gibt zwei Lösungen (beide
sind in der Weboberfläche unter **„🔒 Netzwerk / SSL-Einstellungen“** verfügbar):

### Lösung A (empfohlen, sicher): Firmen-Zertifikat angeben

1. Das Root-Zertifikat deiner Firma als `.pem`- oder `.crt`-Datei besorgen
   (frag ggf. deine IT, oder exportiere es über den Browser aus der
   Zertifikatskette beim Aufruf von `https://api.getbring.com`).
2. Den vollständigen Pfad zur Datei im Feld **„Pfad zum Firmen-Zertifikat“**
   eintragen, z.B. `C:\Zertifikate\firma-root.pem`.

### Lösung B (schnell, unsicher): SSL-Prüfung deaktivieren

Die Checkbox **„SSL-Prüfung deaktivieren“** anhaken. Damit akzeptiert das Tool
jedes Zertifikat.

> ⚠️ **Sicherheitshinweis:** Bei deaktivierter Prüfung wird die Echtheit der
> Verbindung nicht mehr überprüft. Nutze das nur in einem vertrauenswürdigen
> Firmennetz und niemals in einem öffentlichen/fremden Netzwerk.

### Zusätzlich hilfreich (Windows)

Stelle sicher, dass die Zertifikatsbasis aktuell ist:

```bash
pip install --upgrade certifi
```

## Ein-Klick-Betrieb & Notion-Button

Für den bequemen Dauerbetrieb lassen sich die Zugangsdaten **zentral** als
Umgebungsvariablen hinterlegen (`NOTION_TOKEN`, `NOTION_DATABASE_ID`,
`BRING_EMAIL`, `BRING_PASSWORD`, optional `BRING_LIST`). Dann gilt:

- **Aufruf der Startseite** (`http://<host>:8247/`) überträgt **automatisch**
  und zeigt das Ergebnis. (Mit `?noauto=1` nur die Seite ohne Auto-Lauf.)
- **`/run`** startet die Übertragung ebenfalls sofort – ideal zum Verlinken.
- Die Weboberfläche bietet zusätzlich einen großen **„Jetzt übertragen"**-Button
  und ein ausklappbares Formular zum Überschreiben der Daten (Backup).

### Button direkt in Notion

Notion-Buttons können keine Server direkt ansprechen, aber eine URL öffnen:

1. In Notion einen **Button** einfügen (`/button`).
2. Als Aktion **„Open link"** / **„Link öffnen"** wählen.
3. Als URL eintragen: `http://<TrueNAS-IP>:8247/run`
4. Beschriften, z.B. „🛒 An Bring! senden".

Ein Klick öffnet dann einen Tab, der die Übertragung ausführt und das Ergebnis
anzeigt.

> **Hinweis:** Die App ist nur im **lokalen Netzwerk** erreichbar. Der
> Notion-Button funktioniert daher nur, wenn dein Gerät im selben Netz ist.
> Für Fernzugriff bräuchte es zusätzlich z.B. ein VPN (Tailscale) oder einen
> Reverse Proxy.

> **Sicherheit:** Bei zentral hinterlegten Zugangsdaten liegt das Bring!-Passwort
> als Klartext in der Container-Konfiguration. Für den privaten Heimbetrieb ist
> das üblich; nutze idealerweise einen separaten (Test-)Account.

## Betrieb als Docker-Container / auf TrueNAS SCALE

Die Anwendung lässt sich als Docker-Container betreiben – z.B. dauerhaft auf
einem **TrueNAS SCALE**-Server, erreichbar über den Browser im lokalen Netz.

Schneller Test (lokal, mit Docker):

```bash
docker compose up -d --build
# dann im Browser: http://<host-ip>:8247
```

Die vollständige Schritt-für-Schritt-Anleitung für TrueNAS SCALE (Custom App,
lokal bauen **oder** Image aus der GitHub Container Registry) findest du in
**[`TRUENAS.md`](TRUENAS.md)**.

## Wichtige Hinweise

- Die **Bring!-API ist inoffiziell** (`bring-api`). Sie wird von der App selbst
  genutzt, kann sich aber jederzeit ändern. Sollte etwas nicht mehr funktionieren,
  liegt es meist an einer aktualisierten Bibliothek: `pip install -U bring-api`.
- Zugangsdaten werden **nicht gespeichert** – sie werden nur für die jeweilige
  Übertragung verwendet.
- Das Tool läuft lokal und ist nur über `127.0.0.1` erreichbar.

## Projektstruktur

```
.
├── app.py              # Flask-Weboberfläche (Eingabemaske + Button)
├── notion_helper.py    # Notion lesen / Checkbox zurücksetzen
├── bring_helper.py     # Übertragung nach Bring! (Duplikat-Prüfung)
├── ssl_helper.py       # SSL-Konfiguration (Firmennetz / Zertifikate)
├── templates/
│   └── index.html      # Oberfläche
├── Dockerfile          # Container-Image (Gunicorn)
├── docker-compose.yml  # Start per Compose / TrueNAS Custom App
├── .dockerignore
├── .github/workflows/
│   └── docker-publish.yml  # Auto-Build -> GitHub Container Registry
├── TRUENAS.md          # Deployment-Anleitung für TrueNAS SCALE
├── requirements.txt
├── .env.example
└── README.md
```
