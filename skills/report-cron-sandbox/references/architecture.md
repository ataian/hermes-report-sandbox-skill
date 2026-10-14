# Architektur und Übergabevertrag

## Vertrauensgrenzen

| Komponente | Darf lesen | Darf schreiben | Darf nicht erhalten |
|---|---|---|---|
| Hoststarter | feste lokale Konfiguration, freigegebene Pfade | eigenen Staging-/Queuebereich, geprüfte Config | Aufträge aus Reporttext |
| Reportmaker | eigener readonly Code, nötige Quellen/Keys, optional Config-Snapshot | genau eigener Lauf, optional eigene DB | Vault, Versandkeys, andere Maker, Scheduler, Docker-Socket, gesamtes Home |
| Modellselektor | eigener Code, öffentliche Modellinformationen, Inferenz-/Rankingkeys | eigenen Cache und eigene Staging-Ausgabe | Vault, Reports anderer Jobs, Versand-/Cron-Rechte |
| Delivery | Queue, readonly Routing/Code, benötigte Versandkeys | feste Vault-Ziele, eigene Zustellbelege, vollständig zugestellte Läufe bereinigen | freie Befehle/Ziele aus Reports, LLM-/Agentenruntime |

Der Hoststarter ist vertrauenswürdiger Code mit Docker-Autorität. Er darf kein `eval`,
keine vom Maker gelieferten Shellargumente und keine vom Report gelieferten Mounts
verwenden. Alle Dockerargumente als feste Argumentliste übergeben. Dateipfade und
Containername stammen aus lokaler Konfiguration bzw. sicherer Run-ID-Erzeugung.

Die Architektur schützt primär vor Schäden außerhalb der bewusst freigegebenen
Dateien und Fähigkeiten. Sie schützt nicht vor einem kompromittierten Hoststarter,
Kernel-/Container-Escape, falschen Inhalten oder Missbrauch erlaubter APIs.
Ein readonly gemounteter Key ist lesbar und kann entwendet werden. Netzwerkzugang
ist nicht gleich „nur diese API erreichbar“. Egress-Proxy/Allowlist ist eine eigene,
nach lokaler Netzfreigabe aufzubauende Schutzschicht; keine vorhandenen Netze ändern,
nur weil dieser Skill installiert wurde. Docker-Bridge kann interne Dienste erreichen.

## Verzeichnisplan

`REPORT_ROOT` ist ein während der Einrichtung festzulegender absoluter Hostpfad.
Er liegt außerhalb des veröffentlichten Skill-Repositories. Namen sind Vorschläge,
keine verpflichtenden Pfade:

```text
REPORT_ROOT/
  starters/                        vertrauenswürdige Hoststarter + host_common.py
  reportmakers/JOB/
    app/                           nur dieser Maker; readonly im Container
    state/                         optional persistent, nur dieser Maker
    staging/RUN/                   genau dieser Lauf wird /output
  selector/
    app/                           readonly select.py
    state/                         eigener SQLite-Cache
    staging/RUN/config/            /config-output, nicht Live-Config!
    staging/RUN/warning/           /warning-run
  config/llm-config.json            validierte Live-Konfiguration
  unprocessed_reports/JOB/RUN/      nur veröffentlichte abgeschlossene Läufe
  delivery/                        readonly Code/Routing + vertrauenswürdige Belege
  secrets/                         jede benötigte Secretdatei einzeln
  backups/                         nicht im Repo; Aufbewahrung separat abstimmen
```

Eigentümer auf den ausführenden Nutzer abstimmen; sensible Verzeichnisse 0700,
Keys/DBs/Belege 0600, keine allgemein beschreibbaren Eltern. Staging und Queue sowie
Selektor-Staging und Config-Ziel müssen für atomare Umbenennung jeweils auf demselben
Dateisystem liegen. Bei NAS/CIFS Lock-, fsync-, Rename- und Berechtigungssemantik real
prüfen. Nicht einfach `shutil.move` als Cross-Filesystem-Ersatz einsetzen: dabei wäre
halbfertige Ausgabe für den Zusteller sichtbar.

## Lebenszyklus eines Makers

1. Starter hält einen jobbezogenen Hostlock, prüft freigegebene Pfade, Eigentümer,
   Dateitypen und Mountquellen. Keine überlappenden Writer auf derselben DB.
2. Frischen Lauf anlegen: beispielsweise UTC-Datum/Uhrzeit plus zufälliger Suffix.
   Job-ID stammt aus Starter-Konfiguration, nicht aus der Ausgabe.
3. Container mit `--rm` und ausschließlich seinen Mounts starten. Code readonly,
   `/output` nur dieser Lauf, `/state` nur falls nötig. Config für LLM-Nutzer als
   geprüften readonly Snapshot; Endpoint und erlaubte Provider bleiben im Code.
4. Maker schreibt UTF-8 `report.md`, schließt die Datei, schreibt zuletzt `READY`
   mit exakt `ready\n` und beendet sich mit Exit 0. Bei Fehler: nonzero, keine
   Fertigmarkierung. Fachlich leere Tage separat definieren: bewusster Leerreport
   oder explizit dokumentierter No-Report-Status, nicht still „Datei fehlt = Erfolg“.
5. Starter wartet auf tatsächliches Containerende. Bei Timeout/Schedulerabbruch
   nur den eigenen Container beenden und dessen Ende bestätigen. Fehlgeschlagene
   Ausgabe verbleibt im Staging; kein Publish.
6. Nach Exit 0 prüfen: erwartete Dateien, echte reguläre Dateien, keine Symlinks,
   Hardlinks/Sonderdateien, Größenlimits und Format, `READY` exakt. Nur erlaubte
   Dateinamen; zusätzliche Metadaten nur mit festem Jobvertrag.
7. Dateien/Verzeichnisse nach benötigter Haltbarkeitsgarantie synchronisieren und
   ganzen Lauf atomar nach `unprocessed_reports/JOB/RUN` umbenennen. Ziel darf nicht
   existieren. Danach ändert kein Maker diese Daten.

**Container verwerfen ≠ Bericht löschen.** Image und optionaler Zustand bleiben
für spätere Läufe erhalten. Die Queue-Ausgabe bleibt bis zur vollständigen Zustellung.
Die Entfernung des kurzlebigen Containers ist Teil dieses Betriebsmodells; die
Berechtigung zur automatischen Datenbereinigung separat bei Einrichtung festhalten.

## Jobzustand und verlorene Reports

Ein persistenter Cursor oder eine „bereits verarbeitet“-DB darf nicht unbemerkt
fortschreiten und die einzige dazugehörige Ausgabe verschwinden lassen. Scheitert
Publish nach DB-Commit, muss der erhaltene Staginglauf wiederherstellbar sein.
Definieren, ob ein Retry den bestehenden Lauf veröffentlicht oder die Daten erneut
berechnet. Nicht einfach den nächsten Lauf starten und den Fehlerlauf löschen.
Bei kritischen Jobs DB/Outbox-Transaktion nutzen; nicht ohne Bedarf eine neue
zentrale Queue-Datenbank einführen. Backups berücksichtigen SQLite-WAL konsistent.

## Markdown bleibt untrusted

Auch ein technisch valider Bericht kann erfundene Fakten oder manipulative
Anweisungen enthalten. Delivery behandelt ihn als Text, führt nichts aus und ruft
keine darin vorkommenden URLs ab. Markdownrenderer ohne aktive HTML-/Scriptinhalte
verwenden; Remote-Bilder/Embeds können Tracking auslösen und sind standardmäßig
nicht Teil des Übergabevertrags. Nachgelagerte Agenten müssen Reports wiederum als
untrusted Quelle lesen, nicht als neue Systemanweisungen.
