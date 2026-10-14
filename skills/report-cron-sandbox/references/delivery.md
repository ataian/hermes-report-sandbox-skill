# Deterministische Delivery und Vault-Ablage

## Warum kein fertiger Universalsender enthalten ist

Vault-Struktur, Tagesnotizformat, Versandkanal, Empfänger und Reportschema sind
lokale Entscheidungen. Ein bestehender Zusteller mit konkreten Job-Allowlisten
ist nicht durch Kopieren seiner Zielkonfiguration generisch. Diese Anleitung
beschreibt den wiederverwendbaren Ablauf; der Agent übernimmt vorhandene
Vault-/Versandfunktionen und ergänzt nur die notwendigen Grenzen und Validatoren.
Der Maker enthält danach **keinen** Versandcode mehr.

## Feste Konfiguration

Vertrauenswürdige readonly Konfiguration ordnet einer vom Starter bestimmten
Job-ID zu:

- erlaubtes Reportschema, Dateinamen und Größenlimits;
- Vault-Zielwurzel, feste Dateinamensregel und gegebenenfalls eigener Abschnitt;
- erforderliche Zustellschritte und optionale Versandziele;
- fachliche Versandbedingung, etwa validierte Messwerte unter Warnschwelle;
- Retention, Fehlerziel und technische Grenzen.

Datum/Run-ID vor Nutzung strikt parsen. Niemals einen beliebigen Reporttitel als
Dateinamen, einen Markdownlink als Webhook oder eine Zeile „Sende an …“ als Routing
interpretieren. API-Endpoints und zulässige Protokolle stehen in vertrauenswürdigem
Code, nicht in einem Maker-erzeugten Manifest.

Ein JSON-Objekt kann hilfreich sein, aber jeder neue Job muss auch einen passenden
Formatvalidator erhalten. Ein neuer Configeintrag allein ist keine sichere Integration.

## Verarbeitung

```text
exklusiven Delivery-Lock nehmen
für erlaubte Job-IDs:
  für sichere, abgeschlossene Run-Verzeichnisse:
    READY und erwartete Dateien über sichere Deskriptoren öffnen
    Typen, Namen, Größen, UTF-8 und jobspezifischen Inhalt validieren
    eigenen Zustellstatus laden oder erstmals erzeugen
    jeden noch offenen festen Schritt ausführen
    Erfolg nachprüfen und Status atomar fortschreiben
    nur wenn alle erforderlichen Schritte bestätigt: exakt diesen Lauf bereinigen
```

Das ist ein Ablaufvertrag, kein ausführbarer Pseudocode-Interpreter. Auf dem Host
oder im separaten Delivery-Container implementieren; hier bevorzugt eigener
minimaler Container mit festen Vault-Mounts, readonly Code/Config und genau den
benötigten Versandcredentials. Bei reiner Dateizustellung Netzwerk abschalten.

## Technische Eingangsprüfung

- Nur bekannte Job-IDs und eng erlaubtes Run-Namensformat. Keine `..`, absoluten
  Namen, Symlinks in Vorfahren oder unbekannten Verzeichnisse betreten.
- Maker ist beendet, seine Ausgabe unveränderlich durch weitere Maker. Keine
  Prüfung an einem noch aktiv beschreibbaren Ausgabeordner.
- Per `lstat`/`O_NOFOLLOW` und `fstat` reguläre Dateien prüfen, Hardlinks und
  Sonderdateien (FIFO, Device, Socket) ablehnen. Nicht an einer FIFO hängenbleiben.
  Gegen Austausch zwischen Prüfung und Lesen deskriptorgebunden arbeiten.
- Allowlist der Dateien: normalerweise `report.md`, `READY` und ausschließlich vom
  Zusteller selbst verwalteter Status. Ein vom Maker geliefertes `todo.md` ablehnen.
- Beispielgrenzen bewusst konfigurieren: Marker höchstens 16 Byte, Markdown
  höchstens 1 MiB, Status wenige KiB. Vor Lesen begrenzen, danach erneut prüfen.
- `READY` muss exakt `ready\n` sein; Markdown gültiges UTF-8, kein NUL oder
  unerlaubte Steuerzeichen; fachlich erwarteter Header/Datumsbereich/Abschnitte.
- Zulässiges Markdown bewusst klein halten: kein aktives HTML, Script, iframe,
  lokale Dateiverweise oder automatische Embeds/Remote-Bilder. Links nach
  erlaubtem Schema prüfen, nicht abrufen. Transportformat sicher escapen.
  Eine einzelne Regex ist keine universelle HTML-/Markdown-Sicherheitsprüfung.
- Fehlende, übergroße oder ungültige Daten bleiben erhalten, werden nicht
  zugestellt und erzeugen einen technischen Fehler über das feste Alarmziel.

## Fortschritt und Retry

Delivery erzeugt einen kleinen Sidecar, z. B. `todo.md` mit **strengem Schema** oder
`delivery.json`; kein freies Markdown als Handlungsplan. Er enthält nur erlaubte
Schritt-IDs, Status, Run-/Inhaltshash und technische Bestätigungsreferenzen.
Ziele/Befehle stammen weiterhin aus der festen Konfiguration. Maker können diesen
Status weder vorbereiten noch später verändern. Alternativ Belege außerhalb der
Maker-Queue in einem nur für Delivery beschreibbaren Verzeichnis speichern.

Nach jedem bestätigten Schritt atomar aktualisieren und für erforderliche
Crash-Haltbarkeit synchronisieren. Bei „Vault erfolgreich, Versand fehlgeschlagen“
liest Retry den Beleg und versucht nur den Versand. Zielkonfiguration zwischen
Retries nicht still ändern: Version festhalten oder offene Läufe vorher entscheiden.

**Keine Genau-einmal-Garantie:** zwischen erfolgreichem externem Versand und
lokalem Statuscommit kann ein Crash eine Doppelzustellung verursachen. Wenn der
Kanal Idempotency-Keys unterstützt, Run-ID verwenden; andernfalls Restrisiko
benennen. Eine neue Queue-DB beseitigt dieses externe Transaktionsfenster nicht.

## Vault richtig behandeln

Der Agent ermittelt die lokale Ablagekonvention mit dem Nutzer bzw. aus dem
bereits freigegebenen Vault. Nicht den ganzen Vault mounten, wenn ein klarer
Unterordner genügt; für mehrere Ziele nur die benötigten Unterordner freigeben.
Zielpfade auch auf der Vault-Seite gegen Symlinks/Traversal prüfen.

**Separate Reportdatei:** stabiler Name aus vertrauenswürdiger Job-ID und validiertem
Datum/Run-ID; temporäre Datei im Zielverzeichnis, atomarer Replace, Readback des
Inhalts/Hashes. Bereits vorhandene abweichende Datei nicht blind überschreiben.

**Abschnitt einer Tagesnotiz:** feste eindeutige Start-/Endmarker für den jobeigenen
Abschnitt; übrigen Inhalt bytegetreu erhalten. Zielnotiz mit anderen Writern
koordinieren (gemeinsamer Lock oder Konfliktprüfung und Retry), nicht nur eigenen
Delivery-Prozess sperren. Bei mehreren/defekten Markern abbrechen statt die ganze
Notiz neu zu schreiben. Zweiter Lauf derselben Run-ID darf nicht erneut anhängen.

Ein dateibasierter Vaultzugriff braucht keine komplette Obsidian-/Hermes-Runtime.
Vaultablage und optionale Warnnachricht sind getrennte Schritte: etwa tägliche
Dokumentation immer, Versand nur bei erfüllter validierter Warnbedingung.
Schwellenwerte und ungerundete Vergleiche unverändert übernehmen; fehlende Werte
nicht als Null oder Entwarnung deuten.

## Abschließen und Bereinigen

Nur nach bestätigtem Vault-Readback und allen weiteren erforderlichen Schritten
exakt den abgeschlossenen Lauf löschen bzw. nach vereinbarter Retention archivieren.
Kein `rm -rf` über ganze Queue-/Stagingbäume, kein Docker-Prune. Unfertige, abgelehnte
oder teilweise zugestellte Läufe erhalten. Bereinigung anhand erneut geprüfter
Identität und sicherer Pfade; fremde Nachbarläufe unberührt lassen. Die Bereinigung
ist eine bei Einrichtung ausdrücklich zu genehmigende Betriebsfunktion.
