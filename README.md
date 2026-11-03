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
├── templates/
│   └── index.html      # Oberfläche
├── requirements.txt
├── .env.example
└── README.md
```
