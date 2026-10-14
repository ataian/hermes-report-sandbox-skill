# Aufbau, Installation und gezielte Migration

## 1. Skill installieren ist nicht Runtime installieren

Den Skill vollständig in das **richtige Profil** installieren. Native
GitHub-Installation nach Veröffentlichung (OWNER/REPO durch die tatsächlichen Werte
ersetzen), über `terminal`:

```sh
hermes skills install OWNER/REPO/skills/report-cron-sandbox
```

Nicht `--force` benutzen, um einen Scanbefund ungeprüft zu übergehen. Ein Sicherheits-
scanner darf Docker-, Netzwerk- und Bereinigungsfunktionen zur Prüfung markieren.
Nach Installation `skill_view(name="report-cron-sandbox")` und verlinkte Hilfsdateien
prüfen. Bei anderer Hermes-Version zuerst `hermes skills install --help` lesen.

Bei einem bereits geprüften lokalen Checkout kann der Agent den gesamten Ordner
`skills/report-cron-sandbox/` nach `$HERMES_HOME/skills/report-cron-sandbox/` kopieren.
Das Ziel muss neu sein; bestehende Version zunächst vergleichen und sichern, nicht
überschreiben. `HERMES_HOME` aus dem aktiven Profil ermitteln; nur beim tatsächlich
aktiven Default-Profil auf `~/.hermes` zurückfallen. Eine solche lokale Kopie ist
kein Nachweis eines nativen Hub-Sicherheitsscans. Keine fremden Profile verändern.

**Es gibt keinen Ein-Klick-Migrationsinstaller.** Ein Agent muss erst die lokalen
Jobs verstehen und das Einrichtungsblatt ausfüllen. Der Skill gibt Verfahren und
kleine geprüfte Bausteine vor, nicht universelle Zugangsdaten oder Vaultpfade.

## 2. Bestand und Entscheidungen

Mit `terminal` prüfen, zum Beispiel:

```sh
hermes --version
hermes cron list --all
hermes cron edit --help
id
docker version
docker info --format '{{json .SecurityOptions}}'
```

Anschließend mit `read_file`/`search_files` die betroffenen Skripte und Aufrufketten
lesen, nicht sämtliche privaten Dateien sammeln. Benötigte Quellzugänge gezielt
feststellen. Ein Mail-/Kalenderjob bekommt nicht automatisch das gesamte Hermes-
Profil. Wenn nur eine breit berechtigte OAuth-Session verfügbar ist, zuerst einen
schmalen Zugang oder einen separaten vertrauenswürdigen Datenexport prüfen. Keine
Hermes-Installation in den Maker schmuggeln, nur um Auth einfach zu kopieren.

Mit dem Nutzer nur offene Punkte klären: Credentialbeschaffung über sichere lokale
Mechanismen, zulässige Kosten, konkrete Vault-/Versandziele, Fehleralarm, persistente
Daten, Aufbewahrung und Freigabe zum produktiven Umstellen. Keys nie in Chat,
Kommandoargumenten, Dockerfile, Build-Kontext oder Git ablegen. Einzelne Keydateien
mit 0600 und privatem Elternverzeichnis anlegen; Bereitstellung nicht protokollieren.
Ein Nein zu einem Provider ist kein Auftrag, einen anderen kostenpflichtigen zu nehmen.

## 3. Images und Hostcode

Pro unterschiedlichem Abhängigkeitssatz ein kleines Image. Mehrere deterministische
Python-Standardbibliotheksjobs können ein Image teilen, starten aber getrennte
Container mit getrennten Mounts. Python Alpine ist ein praktikables Beispiel, kein
Muss; native Bibliotheken können ein Slim-Image erfordern. Abhängigkeiten beim Build
installieren, keine Paketinstallation beim Cronstart. Imageversion/digest und Größen
festhalten, Updates bewusst testen. Keine globale Dockerbereinigung.

Für den Referenzselektor `templates/selector.Dockerfile` als `Dockerfile` und
`templates/selector.dockerignore` als `.dockerignore` in ein neues privates
Build-Verzeichnis kopieren. Über `terminal`, aus genau diesem Verzeichnis:

```sh
docker build -t report-model-selector:0.1.0 .
docker image inspect report-model-selector:0.1.0 --format '{{.Id}} {{.Size}}'
```

Der Kontextfilter lässt nur das Dockerfile hinein. Kein Appcode und keine Keys
werden eingebaut. `select.py` wird beim Start einzeln readonly nach `/app/select.py`
gemountet. Der Image-Defaultnutzer 65532 ist nur ein sicherer Default; der Starter
übergibt die tatsächliche Nicht-root-Host-UID/GID und richtet Mountrechte passend ein.
Rootless Docker/Usernamespace-Mapping gesondert prüfen statt UID-Gleichheit anzunehmen.

## 4. Hoststarter auf Basis des Helpers

`scripts/host_common.py` ist **Hostcode**, gehört nicht in den Maker. Schnittstellen:

```python
from host_common import checked, checked_lock, docker_run

# Alle Werte stammen aus vertrauenswürdiger lokaler Konfiguration.
roots = (REPORT_ROOT,)
checked(APP_DIR, "dir", roots)
checked(RUN_DIR, "dir", roots)
checked(KEY_FILE, "file", roots)
# Für Secrets zusätzlich private Modi (0600) und Eigentümer prüfen.

rc = docker_run(
    GENERATED_CONTAINER_NAME,
    FIXED_IMAGE,
    [(APP_DIR, "/app", True), (RUN_DIR, "/output", False)],
    ["python", "/app/make_report.py"],
    timeout=300,
    network=False,
)
# Erst rc == 0 UND vollständige technische Validierung erlauben Publish.
```

Das ist ein Integrationsausschnitt, kein ausführbarer kompletter Starter. `roots`
enthält geprüfte absolute freigegebene Wurzeln ohne abschließenden Slash. Der Helper
prüft Pfadbestandteile ohne Symlink-Folgen, Typ/Eigentümer/Modi und Einzellinks für
Dateien. `checked_lock(fd)` prüft eine bereits mit `O_NOFOLLOW` geöffnete Lockdatei;
der Starter nimmt den eigentlichen `fcntl.flock` selbst. Mit restriktivem `umask`
und nicht-root ausführen. Keine Mountquellen aus Reportdaten. Der Helper lehnt nicht absolute/nicht
kanonische Mountpfade, CSV-Sonderzeichen (Komma/Anführungszeichen), NUL/Zeilenumbrüche
und ungültige Containernamen ab. Er nimmt die Eigentümer-/Typ-/Wurzelprüfung nicht
automatisch für alle Mounts vor: `checked()` im Starter für jede Quelle aufrufen.

`docker_run` liefert Exitstatus, setzt `--rm`, readonly Rootfs, cap-drop ALL,
no-new-privileges, private tmpfs, 384 MiB RAM ohne zusätzlichen Swap, 64 PIDs und
1 CPU. Er nutzt die UID/GID des Hostprozesses. Das sind Startwerte; echten Bedarf
messen und innerhalb des vereinbarten Ressourcenbudgets anpassen. `network=True`
ist der Default und bedeutet normales Docker-Netzwerk, **keine** Egress-Allowlist.
Offline-Jobs und Dateizusteller ausdrücklich mit `network=False` aufrufen.

Der Helper behandelt seinen eigenen Timeout und entfernt nur den generierten
Container. Er ist kein kompletter Supervision-Dienst: der fertige Starter muss
SIGTERM/SIGINT und Abbruch durch den Scheduler behandeln, den eigenen Container
beenden und Ende bestätigen. SIGKILL/Hostausfall braucht beim nächsten Start eine
eng begrenzte Wiederanlaufprüfung (eigener Name/Joblabel), keinen globalen Prune.
Container-Timeout kürzer als Scheduler-Skriptdeadline inklusive Cleanup-Puffer
festlegen. Die aktuelle Hermes-Dokumentation nennt `cron.script_timeout_seconds`
bzw. `HERMES_CRON_SCRIPT_TIMEOUT`; tatsächlich installierte Version/Profil prüfen,
keine globale Deadline nur wegen eines Jobs ungefragt verändern.

Zusätzlich erforderlich: jobbezogener Lock, einmalige Run-ID, sichere
Stagingerzeugung, Validierung/atomarer Publish, bei Selektor Configschema und
Fallbackwarnung. Diese kleinen Starter sind lokal anzupassen; absichtlich kein
universelles Framework oder generischer Mount-Interpreter.

## 5. Delivery und Modellwahl

`references/delivery.md` und `references/model-selection.md` befolgen. Ein gemeinsamer
Delivery-Cron reicht normalerweise für alle Maker. Pro Job feste Validatoren und
Routing ergänzen. Kein neuer Zusteller pro Maker, solange nicht unterschiedliche
Berechtigungsgruppen eine zusätzliche Trennung verlangen.

Die gemeinsame Modellconfig nur an LLM-Nutzer weitergeben. Vor jedem Lauf unter
vertrauenswürdiger Kontrolle in einen privaten readonly Snapshot übernehmen.
Das verhindert, dass ein Wechsel mitten im Lauf verschiedene Modelle mischt.
Keine URLs, Tokens, Shellkommandos oder freien Providerdefinitionen in die Config.

## 6. Abnahme und Cutover

1. Tests aus `references/verification.md` an künstlichen Daten und separatem Testvault
   bestehen lassen; keine echten Berichte doppelt versenden.
2. Betroffene Jobdefinitionen sichern; aktive Altjobs pausieren, Ende abwarten.
   SQLite über Backup-API konsistent sichern, keine rohe WAL-Dateikopie.
3. Runtime installieren; vorhandene DBs nicht neu initialisieren oder ungeprüft
   durch ältere Snapshots ersetzen. Pending Reports und Cursors erhalten.
4. Bestehende Job-IDs einzeln auf feste Shims in `$HERMES_HOME/scripts/` umstellen.
   Über `terminal` oder das vorhandene Cron-Tool, nach lokaler Freigabe:

   ```sh
   hermes cron edit JOB_ID --script start-JOB.sh --no-agent --deliver local
   ```

   `JOB_ID`/`JOB` sind Platzhalter, keine geratenen Werte. Zeitplan nicht ändern,
   wenn es nur um Isolation geht. Fehlerziel ausdrücklich setzen und prüfen.
   `deliver local` verhindert einen zweiten externen Versand des Starter-stdout;
   der eigentliche Report geht ausschließlich über Delivery. Beschreibung/Prompt
   und veraltete Skills passend aktualisieren, keine irreführenden Altaufrufe lassen.
5. Delivery/Selektor nur anlegen, wenn kein passender Job existiert. Neue Jobs
   zunächst pausiert anlegen. Selektor mit ausreichendem Vorlauf planen; ein voller
   Kandidatentest kann deutlich länger dauern als der tägliche Erhaltungsprobeaufruf.
6. Zieldefinitionen zurücklesen, unbeteiligte Jobs mit Baseline vergleichen. Nach
   erfolgreich bestätigter Testzustellung Jobs gezielt fortsetzen und echte nächste
   Ausführung samt Ergebnis beobachten. Ein angenommener manueller Run ist noch
   kein abgeschlossener Run; finalen Status und Ausgaben lesen.

## 7. Rollback

Neue Erzeuger/Zusteller pausieren, laufende Container abwarten/beenden. Pending
Reports, Zustellbelege, aktuelle DB und Config sichern. Pro betroffenem Job genau
alten Script-/Agentmodus, Zustellparameter und Zeitplan wiederherstellen. Keine
komplette `jobs.json` über den aktiven Store kopieren. Kein paralleler alter/neuer
Versand. DB-Rückkehr nur nach Bewertung neuerer Daten und festgelegter Cursorstrategie.
Exakte lokale IDs und Befehle in einem privaten Betriebsblatt dokumentieren.

## Offizielle Hermes-Referenzen

- https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- https://hermes-agent.nousresearch.com/docs/user-guide/features/cron
- https://hermes-agent.nousresearch.com/docs/user-guide/security

Bei Versionsabweichungen aktuelle Dokumentation und installierte CLI prüfen; keine
hier genannten Flags erfinden oder ungeprüft in eine andere Version übernehmen.
