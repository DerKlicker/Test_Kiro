# Deployment auf TrueNAS SCALE (Docker / Custom App)

Diese Anleitung zeigt, wie du die Notion-zu-Bring!-Anwendung auf
**TrueNAS SCALE** als Container betreibst und im lokalen Netzwerk über den
Browser erreichst.

Es gibt zwei Wege:

- **Weg A – Lokal bauen** (einfachster Start, kein GitHub-Account für die
  Registry nötig). Empfohlen, um schnell loszulegen.
- **Weg B – Registry (ghcr.io)** (komfortable Updates per Versionsnummer).
  Empfohlen für den Dauerbetrieb.

Die App läuft im Container auf Port **5000** und wird auf den Host-Port
**8247** veröffentlicht. Erreichbar ist sie dann unter:

```
http://<TrueNAS-IP>:8247
```

---

## Weg A – Image lokal auf dem TrueNAS bauen

### 1. Code auf den Server bringen

Per SSH auf den TrueNAS einloggen und das Repository klonen (oder die Dateien
in einen Ordner auf einem Dataset legen, z.B. `/mnt/pool/apps/notion-to-bring`):

```bash
cd /mnt/pool/apps            # an deinen Pool-/Dataset-Pfad anpassen
git clone https://github.com/<DEIN-GITHUB-NAME>/Test_Kiro.git notion-to-bring
cd notion-to-bring
```

### 2. Image bauen

```bash
docker build -t notion-to-bring:latest .
```

### 3a. Starten per Docker Compose (einfach)

```bash
docker compose up -d
```

Fertig. Aufrufen unter `http://<TrueNAS-IP>:8247`.

Logs ansehen:   `docker compose logs -f`
Stoppen:        `docker compose down`

### 3b. ODER als „Custom App“ in der TrueNAS-Weboberfläche

1. In TrueNAS SCALE: **Apps → Discover Apps → (oben rechts) Custom App**.
2. Entweder die Felder manuell ausfüllen **oder** – falls deine Version es
   anbietet – **„Install via YAML“** wählen und den Inhalt von
   `docker-compose.yml` einfügen (bei „Install via YAML“ wird häufig nur der
   `services:`-Block ohne `build:` akzeptiert; nutze dann das zuvor lokal
   gebaute Image `notion-to-bring:latest`).

   **Manuelle Felder (falls kein YAML-Import):**
   - **Application Name:** `notion-to-bring`
   - **Image Repository:** `notion-to-bring`
   - **Image Tag:** `latest`
   - **Port Forwarding:** Container-Port `5000` → Node-Port `8247`
   - **Environment Variables:**
     - `HOST` = `0.0.0.0`
     - `PORT` = `5000`
   - **Restart Policy:** `unless-stopped`

3. **Install / Save** klicken und warten, bis der Status „Running“ ist.

---

## Weg B – Image aus der GitHub Container Registry (ghcr.io)

Mit diesem Weg baut GitHub das Image automatisch und TrueNAS zieht es nur noch.

### 1. Automatischen Build aktivieren

Im Repository liegt bereits die Pipeline
`.github/workflows/docker-publish.yml`. Sobald Änderungen nach `main`
gemerged werden (oder du ein Tag wie `v1.0.0` pushst), baut GitHub das Image
und veröffentlicht es unter:

```
ghcr.io/<DEIN-GITHUB-NAME>/test_kiro:latest
```

> Hinweis: GitHub macht ghcr.io-Pakete standardmäßig **privat**. Für einen
> einfachen Pull auf dem TrueNAS kannst du das Paket auf **public** stellen:
> GitHub → dein Profil → **Packages** → Paket wählen → **Package settings** →
> **Change visibility** → *Public*.
> (Bleibt es privat, musst du dich auf dem TrueNAS einmal per
> `docker login ghcr.io` mit einem Personal Access Token anmelden.)

### 2. In TrueNAS als Custom App einrichten

Wie bei Weg A (Punkt 3b), aber mit diesen Werten:
- **Image Repository:** `ghcr.io/<DEIN-GITHUB-NAME>/test_kiro`
- **Image Tag:** `latest`
- Rest (Port `5000`→`8247`, `HOST=0.0.0.0`) identisch.

Alternativ per SSH:

```bash
docker pull ghcr.io/<DEIN-GITHUB-NAME>/test_kiro:latest
# docker-compose.yml: build-Zeilen auskommentieren, image:-Zeile auf ghcr setzen
docker compose up -d
```

---

## Firmen-Zertifikat im Container (optional)

Falls du den sicheren SSL-Weg mit Firmen-Zertifikat nutzen willst, muss die
`.pem`-Datei **im Container** liegen. Dazu einen Ordner einhängen:

1. Zertifikat auf den TrueNAS legen, z.B.
   `/mnt/pool/apps/notion-to-bring/certs/firma-root.pem`.
2. In `docker-compose.yml` den `volumes:`-Block aktivieren (bereits vorbereitet,
   nur einkommentieren):
   ```yaml
   volumes:
     - /mnt/pool/apps/notion-to-bring/certs:/certs:ro
   ```
   In der Custom-App-Oberfläche entspricht das einem **Host Path Volume**:
   Host `/mnt/pool/apps/notion-to-bring/certs` → Mount `/certs` (read-only).
3. In der Weboberfläche im Feld **„Pfad zum Firmen-Zertifikat“** dann
   `/certs/firma-root.pem` eintragen.

---

## Updates einspielen

**Weg A (lokal gebaut):**
```bash
cd /mnt/pool/apps/notion-to-bring
git pull
docker compose up -d --build
```

**Weg B (Registry):**
```bash
docker compose pull
docker compose up -d
```
(oder in der TrueNAS-App-Oberfläche auf **Update** klicken)

---

## Fehlersuche

- **Seite nicht erreichbar:** Prüfe, ob der Container läuft
  (`docker ps` bzw. App-Status „Running“) und ob Port `8247` am Host offen ist.
- **Container startet nicht / stürzt ab:** Logs ansehen
  (`docker compose logs -f` oder in der App-Oberfläche unter „Logs“).
- **SSL-Fehler (`CERTIFICATE_VERIFY_FAILED`):** Siehe Abschnitt
  „Firmen-Zertifikat im Container“ oder nutze die Checkbox
  „SSL-Prüfung deaktivieren“ in der Weboberfläche.
- **Health-Check „unhealthy“:** Meist nur, bis die App vollständig gestartet
  ist (`start_period`). Danach sollte er „healthy“ zeigen.
