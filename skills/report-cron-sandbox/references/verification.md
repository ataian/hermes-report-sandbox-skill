# Prüfplan: Paket und lokale Einrichtung

## A. Offline-Regressionen des mitgelieferten Codes

Aus dem Skill-Verzeichnis über `terminal`, mit einer Projekt-Pythonumgebung,
in der `pytest` vorhanden ist:

```sh
python -c "from pathlib import Path; Path('.verification').mkdir(mode=0o700, exist_ok=True)"
python -m pytest -q --basetemp=.verification/pytest scripts/tests
```

Für jeden unabhängigen Wiederholungslauf ein neues `--basetemp` verwenden, wenn
vorherige Evidenz erhalten werden soll. Pytest kann sein eigenes Basetemp-Verzeichnis
bei Wiederholung bereinigen; niemals reale Lauf-/DB-/Vaultverzeichnisse dafür angeben.
Testpfad unter einem privaten Projektverzeichnis anlegen, nicht unter einem
weltbeschreibbaren System-Temp-Elternpfad: der Hosthelper lehnt solche Vorfahren ab.

Tests verwenden künstliche APIantworten und Modelle. Sie prüfen Preise, Redirects,
Antwortlimits, Cache, Ranking, Judge-Rubrik, Fallback, fehlenden Fallback,
Retain-Free-Pfad, Toolvertrag, Interpreter-Safepath und Hosthelperverhalten.
Sie beweisen keine heutige Providerverfügbarkeit oder tatsächliche Kostenfreiheit.

## B. Echter Container ohne Netzwerk und Keys

Zuerst das Referenzimage aus dem Dockerfile gemäß Aufbauanleitung bauen. Frische
private Testordner `state`, `config`, `warning`, `maker` anlegen. Nur synthetische
Daten verwenden; keine Produktiv-DB einhängen. Die folgenden Befehle über `terminal`
ausführen, nachdem `SKILL`, `FIXTURE`, `UID_NUM` und `GID_NUM` auf absolute geprüfte
Pfade bzw. die tatsächliche Nicht-root-UID/GID gesetzt wurden. Pfade müssen frei von
Kommas sein. `FIXTURE` darf ausschließlich für diesen Test neu erzeugte Daten enthalten.

```sh
docker run --rm --network none --user "$UID_NUM:$GID_NUM" \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --memory 384m --memory-swap 384m --pids-limit 64 --cpus 1 \
  --tmpfs "/tmp:rw,noexec,nosuid,size=32m,uid=$UID_NUM,gid=$GID_NUM" \
  --mount "type=bind,src=$SKILL/scripts/select.py,dst=/app/select.py,readonly" \
  --mount "type=bind,src=$SKILL/scripts/tests/container_smoke.py,dst=/app/container_smoke.py,readonly" \
  --mount "type=bind,src=$FIXTURE/state,dst=/state" \
  --mount "type=bind,src=$FIXTURE/config,dst=/config-output" \
  --mount "type=bind,src=$FIXTURE/warning,dst=/warning-run" \
  report-model-selector:0.1.0 python /app/container_smoke.py
```

Erwartung: Exit 0 und `PASS: synthetic selector output...`, Config mit
`fixture/free:free`, keine Warnung. SQLite-Cache gehört dem ausführenden Nutzer.
Der Test mockt Katalog und Inferenz **im Testprozess**; Netzwerk ist wirklich aus.
Die Testfunktion wird niemals im Produktionsstarter verwendet.

Den normalen Entrypoint ebenfalls ausführen (gleiche Schutzoptionen, readonly
`select.py`-Mount, kein Datum): Erwartung Exit 1 mit
`selection blocked: PolicyError: one run date required`, nicht Importfehler oder
`select.select`-Fehler. Das ist ein erfolgreicher Negativtest, kein Selektionslauf.

Den Makervertrag separat mit demselben Dependency-Image prüfen, diesmal nur
`fixture_maker.py` readonly nach `/app/fixture_maker.py` und den frischen
`maker`-Ordner nach `/output` mounten; Kommando `python /app/fixture_maker.py`.
Erwartung: exakt `report.md` und `READY`, `READY` gleich `ready\n`.
Keine Queue-/Vaultveröffentlichung durch diesen Test.

## C. Tatsächliche Isolation des lokalen Starters

- Echten fertig integrierten Starter nutzen, nicht nur nachgebaute Dockeroptionen.
- Während eines kontrollierten Testlaufs `docker inspect` auswerten: Mountquellen,
  Schreibrechte, Nutzer, readonly Rootfs, CapDrop, SecurityOpt, Netzwerkmodus,
  Memory/MemorySwap, PidsLimit, NanoCpus und Tmpfs.
- Schreiben nach `/app` und nicht gemountetem Hostmarker muss fehlschlagen bzw.
  Marker unsichtbar sein. Schreiben in eigenen Lauf erlaubt; Zugriff auf Vault,
  fremde Makerstate/Queue, Hermes-Konfiguration und Docker-Socket nicht möglich.
- Normalende, Containerfehler, Timeout, SIGTERM und Wiederanlauf prüfen. Eigener
  Container verschwunden/beendet; keine Nachbarcontainer angefasst.
- Producer nicht beendet oder Exit nonzero → kein Publish, auch wenn READY liegt.
- Alter State bleibt erhalten; bei Publishfehler darf kein Bericht verloren gehen.

## D. Übergabe, Delivery und Vault

Negative Fälle mit Fixtures: fehlendes/falsches READY, ungültiges UTF-8, NUL,
zu große Datei, Symlink in Datei/Elternpfad, Hardlink, FIFO, Pfadtraversal,
unbekannte Job-ID, Zusatzdatei, vorgetäuschtes todo, aktive HTML-/Embedinhalte,
unerlaubte URLs, ausgetauschte Datei während Prüfung, unpassendes Reportdatum.
Alle werden nicht zugestellt und bleiben für Diagnose erhalten.

Positive Fälle:

1. Echter Testreport aus Container atomar in Testqueue veröffentlichen.
2. Delivery in isoliertes Testvault schreiben und exakten Inhalt zurücklesen.
3. Wiederholung erzeugt keinen doppelten Tagesabschnitt; andere Notizinhalte bleiben.
4. Simuliert „Vault erfolgreich, Kanal fehlgeschlagen“: Retry nur offenen Kanal;
   noch keine Bereinigung. Kanalbestätigung und lokalen Fortschritt prüfen.
5. Erst nach kompletter Bestätigung exakt diesen Lauf bereinigen; Nachbarlauf und
   abgelehnter Lauf bleiben unverändert.
6. Gleichzeitige Delivery-Starts durch Lock serialisieren; Vaultkonflikt mit einem
   anderen Writer erkennen statt dessen Daten zu überschreiben.

Externe Testnachrichten nur an vereinbarte Testziele und klar als Test kennzeichnen.
Keine künstliche Schwellenwarnung als echte Kontowarnung versenden.

## E. Selektor live, erst nach Credential-/Kostenentscheidung

Mit erlaubten eigenen Credentials real ausführen. Belegen: exakte Modell-ID,
aktuelle Preise, echte Antwort, `usage.cost`, Config-Publish. Falls die vereinbarte
Abnahme einen Fallbacktest enthält, dessen mögliche Kosten vorab freigeben.
Wiederholung mit gesundem Free-Modell: Ranking darf nicht angefragt werden,
Qualitätscache bleibt gleich, kurze reale Probe funktioniert.

Fehlende Keys, Firecrawl-Ausfall, kaputtes Ranking, nicht mehr kostenlose SKU,
fehlender Fallback und unlesbare Config mit kontrollierten Fixtures testen.
Dokumentieren, welche davon gemäß vereinbarter Policy fallbacken und welche stoppen.
Config-Publishfehler darf altes Livefile nicht zerstören. Crash zwischen Publish und
Warnqueue muss anhand erhaltenem Staging wiederherstellbar sein.

## F. Abschlussnachweis

Für jede Umgebung separat festhalten: getesteter Commit/Image-Digest, Testanzahl,
Containerinspect, Vault-Readback, Versandbestätigung, angepasste Cron-IDs und deren
Rücklese, unbeeinflusste andere Jobs, erster echter Schedulerabschluss und Rollback.
Keine Keys oder privaten Berichtsinhalte in öffentliches Testprotokoll schreiben.

Dieses Paket enthält keinen universellen Delivery- oder produktiven Cronstarter;
deren Abnahme ist eine Aufgabe der lokalen Einrichtung. Ein bestandener synthetischer
Smoke-Test darf niemals als vollständige Produktionsmigration ausgegeben werden.
