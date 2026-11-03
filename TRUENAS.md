# Deployment auf TrueNAS SCALE (Docker / Custom App)

Diese Anleitung zeigt, wie du die Notion-zu-Bring!-Anwendung auf
**TrueNAS SCALE** als Container betreibst und im lokalen Netzwerk über den
Browser erreichst.

Die App läuft im Container auf Port **5000** und wird auf den Host-Port
**8247** veröffentlicht. Erreichbar ist sie dann unter:

```
http://<TrueNAS-IP>:8247
```

> ⚠️ **Wichtig zu TrueNAS Custom Apps:** Das TrueNAS-App-System kann Images
> **nicht** aus einem lokalen Ordner bauen (ein `build:`-Block in der Compose
> funktioniert dort nicht). Eine Custom App braucht immer ein **fertiges Image
> aus einer Registry**. Deshalb ist der **empfohlene Weg der Registry-Weg**
> (unten). Nur wer bewusst per SSH arbeitet, kann das Image lokal bauen.

---

## ⭐ Empfohlen: Registry-Weg (ghcr.io) als Custom App

Das Image wird von der GitHub-Actions-Pipeline automatisch gebaut und liegt in
der GitHub Container Registry unter:

```
ghcr.io/derklicker/test_kiro:latest
```

### 1. ghcr.io-Package abrufbar machen

GitHub macht Container-Packages standardmäßig **privat**. Am einfachsten machst
du es **public**, dann kann TrueNAS es ohne Login ziehen:

GitHub → dein Profil → **Packages** → `test_kiro` auswählen →
**Package settings** → **Change visibility** → *Public*.

> Soll es privat bleiben, melde dich auf dem TrueNAS einmal per SSH an:
> `sudo docker login ghcr.io -u <DEIN-GITHUB-NAME>` (als Passwort einen
> Personal Access Token mit `read:packages`-Scope verwenden).

### 2. Custom App anlegen (Install via YAML)

1. TrueNAS SCALE: **Apps → Discover Apps → (oben rechts) Custom App**.
2. **„Install via YAML“** wählen und den Inhalt der Datei
   **`docker-compose.truenas.yml`** komplett einfügen.
3. **Install** klicken und warten, bis der Status **„Running“** ist.
4. Aufrufen unter `http://<TrueNAS-IP>:8247`.

Falls deine SCALE-Version kein YAML-Feld bietet, die Felder manuell setzen:
- **Image Repository:** `ghcr.io/derklicker/test_kiro`  **Tag:** `latest`
- **Port:** Container `5000` → Node `8247`
- **Environment:** `HOST=0.0.0.0`, `PORT=5000`
- **Restart Policy:** `unless-stopped`

### 3. Updates einspielen (manuell)

Nach Änderungen baut GitHub automatisch ein neues `latest`-Image. In TrueNAS
die App öffnen und auf **Update** klicken.

> ⚠️ **„latest“-Cache-Falle:** Da sich der Tag-Name `latest` nie ändert, zieht
> TrueNAS manchmal weiter das alte, gecachte Image. Hilft „Update“ nicht,
> erzwinge den Pull per SSH:
> ```bash
> sudo docker pull ghcr.io/derklicker/test_kiro:latest
> ```
> und starte die App danach neu. Alternativ kannst du gezielt einen
> eindeutigen Tag verwenden, z.B. `...:sha-<commit>` oder einen Versions-Tag.

---

## ⭐ Automatische Updates mit Watchtower

Damit du nicht jedes Mal manuell aktualisieren musst, kann **Watchtower** das
übernehmen: ein kleiner Zusatz-Container, der regelmäßig prüft, ob ein neueres
Image vorliegt, und die App dann automatisch aktualisiert und neu startet.

**Das löst auch die „latest“-Cache-Falle:** Watchtower vergleicht den
Image-*Digest* (den tatsächlichen Inhalt), nicht nur den Tag-Namen. Ein neues
`latest` wird dadurch zuverlässig erkannt.

### Einrichtung

Lege **eine** Custom App mit beiden Diensten an (App + Watchtower). Nimm dafür
den Inhalt von **`docker-compose.truenas-autoupdate.yml`** bei
**„Install via YAML“**.

Kernpunkte dieser Konfiguration:
- Die App bekommt das Label `com.centurylinklabs.watchtower.enable=true`.
- Watchtower läuft mit `--label-enable`, aktualisiert also **nur** diese App
  (nicht andere Container auf dem System).
- Prüfintervall: alle 6 Stunden (`WATCHTOWER_POLL_INTERVAL=21600`), anpassbar.
- `--cleanup` entfernt alte Images, damit die Platte nicht vollläuft.

> **Hinweis zum Docker-Socket:** Watchtower braucht Zugriff auf
> `/var/run/docker.sock`, um Container zu steuern. Das ist für dieses Tool
> normal und nötig. Wer das vermeiden will, nutzt stattdessen das manuelle
> Update oben.

Ab jetzt gilt: Sobald du Code änderst → GitHub baut ein neues `latest` →
Watchtower zieht es beim nächsten Check automatisch. Kein Handanlegen mehr. 🎉

---

## Alternative: per SSH auf der Kommandozeile

Dieser Weg ist nur für den schnellen Test gedacht. TrueNAS verwaltet Docker
normalerweise selbst – manuelle CLI-Container tauchen nicht in der App-Oberfläche
auf und können bei TrueNAS-Updates verloren gehen.

### Variante 1: Image lokal bauen und starten

```bash
# Repo klonen (an deinen Dataset-Pfad anpassen)
cd /mnt/pool/apps
git clone https://github.com/DerKlicker/Test_Kiro.git notion-to-bring
cd notion-to-bring

# Image bauen und starten (sudo, da docker als root läuft)
sudo docker compose up -d --build
```

### Variante 2: Fertiges Registry-Image starten

```bash
cd /mnt/pool/apps/notion-to-bring
sudo docker compose -f docker-compose.truenas.yml up -d
```

Nützliche Befehle:

```bash
sudo docker compose logs -f      # Logs ansehen
sudo docker compose down         # stoppen und entfernen
sudo docker ps                   # laufende Container anzeigen
```

Aufrufen unter `http://<TrueNAS-IP>:8247`.

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

**Custom App (Registry-Weg):** In der TrueNAS-App-Oberfläche die App öffnen und
auf **Update** klicken. TrueNAS zieht dann das neue `latest`-Image.

**Per SSH (Registry-Image):**
```bash
cd /mnt/pool/apps/notion-to-bring
sudo docker compose -f docker-compose.truenas.yml pull
sudo docker compose -f docker-compose.truenas.yml up -d
```

**Per SSH (lokal gebaut):**
```bash
cd /mnt/pool/apps/notion-to-bring
git pull
sudo docker compose up -d --build
```

---

## Fehlersuche

- **`Failed 'up' action ... image not found` / Custom App startet nicht:**
  TrueNAS kann keine lokalen Images bauen. Nutze den **Registry-Weg** mit
  `docker-compose.truenas.yml` (Image aus ghcr.io) und stelle sicher, dass das
  ghcr.io-Package **public** ist bzw. du per `docker login ghcr.io` angemeldet bist.
- **`permission denied ... /var/run/docker.sock`:** CLI-Befehle mit `sudo`
  ausführen (`sudo docker ...`).
- **Seite nicht erreichbar:** Prüfe, ob der Container läuft
  (`sudo docker ps` bzw. App-Status „Running“) und ob Port `8247` erreichbar ist.
- **Container startet nicht / stürzt ab:** Logs ansehen
  (`sudo docker compose logs -f` oder in der App-Oberfläche unter „Logs“).
- **SSL-Fehler (`CERTIFICATE_VERIFY_FAILED`):** Siehe Abschnitt
  „Firmen-Zertifikat im Container“ oder nutze die Checkbox
  „SSL-Prüfung deaktivieren“ in der Weboberfläche.
- **Health-Check „unhealthy“:** Meist nur, bis die App vollständig gestartet
  ist (`start_period`). Danach sollte er „healthy“ zeigen.
