# LLM-Freemodel-Selection: nutzbare Referenz, lokale Policy

## Was enthalten ist

`scripts/select.py` ist ein eigenständiger Python-Selektor ohne Hermes-Imports,
OAuth-Store, Cronmutation oder Agentenschleife. Seine mitgelieferte Auswahl- und
Kostenpolitik bleibt unverändert; es gibt keinen neu eingebauten Paid-Sperrschalter.
Der Agent muss bei Einrichtung klären, ob diese konkrete Policy passt, bevor er
reale API-Aufrufe oder den Cron aktiviert.

Die Architektur ist generisch; der Code ist bewusst **Nous-/Firecrawl-spezifisch**.
Wer andere Provider, Ranglisten oder Sprachen nutzen will, passt genau die
betroffenen Funktionen, Tests und Dokumentation an. Es gibt keine generische
„API-Key vorhanden, alles fertig“-Garantie.

## Eingaben, Ausgaben, Credentials

| Containerpfad | Mount | Bedeutung |
|---|---|---|
| `/app/select.py` | einzelne Datei readonly | Selektorcode |
| `/state` | eigener Ordner writable | persistenter `cache.sqlite3` |
| `/config-output` | frischer eigener Stagingordner writable | `llm-config.json` |
| `/warning-run` | frischer eigener Stagingordner writable | optional `report.md` + `READY` |
| `/run/secrets/nous_api_key` | einzelne Datei readonly | roher Nous-Inferenz-API-Key |
| `/run/secrets/firecrawl_api_key` | einzelne Datei readonly | roher Firecrawl-Key für neue Ranglistensuche |

Nicht den gesamten Secretordner oder `.env` mounten. Keine Secretwerte in der
Modellconfig, im Cache-Testfixture oder in Git. Schlüsselbereitstellung und
zulässige Kosten werden während der Installation geklärt, nicht in dieser Anleitung
vorausgesetzt. Firecrawl selbst kann ebenfalls Kosten verursachen.

CLI im Container: `python /app/select.py YYYY-MM-DD`; Datum vorgeben, damit Warnung
und Run-ID zusammenpassen. Python-Safepath muss aktiv sein. Bei implizitem
Programmatic-Aufruf verwendet `main()` Europe/Berlin; andere Zeitzone bewusst
anpassen oder immer das korrekt abgeleitete lokale Datum übergeben. Zeitzonendaten
sind im Dockerfile enthalten.

Feste Netzwerkziele im Code:

- `https://inference-api.nousresearch.com/v1/models`
- `https://inference-api.nousresearch.com/v1/chat/completions`
- `https://api.firecrawl.dev/v1/scrape` zum Rendern von
  `https://portal.nousresearch.com/models`

Der HTTP-Helper erlaubt nur diese Requestziele und folgt keinen Redirects.
Dies ist eine Einschränkung dieses Codepfads, **keine systemweite Egress-Sperre**.

## Vor dem ersten echten Lauf entscheiden

1. Ist Nous mit einem eigenen Inferenz-Key nutzbar? Ein vorhandenes Hermes-OAuth-
   Login ist nicht automatisch dieser Key.
2. Ist Firecrawl verfügbar und erlaubt? Beim Beibehalten eines funktionierenden
   Free-Modells wird kein Rankingabruf benötigt. Beim Erststart oder Ersatzsuchen
   ist der Firecrawl-Pfad dagegen Bestandteil dieses Codes.
3. Ist der exakte Fallback `deepseek/deepseek-v4-flash` freigegeben und aktuell
   tatsächlich vorhanden? Die Referenz verlangt diese ID schon am Anfang der
   Auswahl, **auch wenn ein aktives Free-Modell vorhanden ist**.
4. Sind bezahlte Judge-Aufrufe erlaubt? Ohne bereits qualifizierten verfügbaren
   Free-Judge nutzt die Referenz den genannten Fallback auch zur Bewertung.
   Ein letztlich kostenlos ausgewähltes Modell bedeutet daher nicht, dass seine
   Auswahl kostenlos war. Es ist kein absolutes Dollar-Budgetlimit eingebaut.
5. Passt die Rubrik für deutsche Tagesberichte mit 65.536 Mindestkontext,
   Tool-Calling und synthetischem Kontext-/Injection-Test? Ein Reportmaker ohne
   Tools kann einen anderen Maßstab benötigen. Bei Änderungen `RUBRIC` versionieren.

Wenn ein Punkt nicht passt: Inbetriebnahme aussetzen und eine passende Variante
mit dem Nutzer festlegen. Beispielsweise ohne LLM arbeiten, einen festen bereits
freigegebenen Modellweg nutzen oder die Ranglistenquelle/Policy gezielt anpassen.
Nicht Free-Aliase erfinden, `:free` entfernen oder ungefragt einen Paid-Zwilling nutzen.

## Auswahlablauf

1. Öffentlichen Katalog laden und exakten Fallback nachweisen.
2. Vorhandene aktive Free-Route: aktuelle Preise/Ablaufdatum und reale kurze
   Verfügbarkeitsprobe prüfen. Bei Erfolg Route behalten; kein Ranking, kein neuer
   Qualitätstest. Auch geänderte öffentliche Versionsmetadaten allein erzwingen
   in dieser Referenz keinen Wechsel, sondern aktualisieren den Fingerprint.
3. Sonst gerenderte Portal-Tabelle auswerten: ausdrücklich `Daily usage↓`, sichtbare
   Ränge 1–10, Text + FREE, eindeutige Zuordnung zur kostenfreien exakten API-ID.
   Nicht behaupten, die `/models`-Reihenfolge sei diese Rangliste. Der Parser
   verlangt mindestens fünf verifizierbare Rangzeilen, nicht zwingend zehn;
   unlesbare/nicht zuordenbare Einträge sind keine Kandidaten.
4. Preis-/Versionsprüfung unmittelbar vor jedem Kandidatenaufruf; echte Probe
   und `usage.cost == 0`. Fehlende/unbekannte Kosten sind kein Free-Nachweis.
5. Synthetische Tests für Bericht, simulierten Toolaufruf und Kontext, dann
   Bewertung. Tool-Calling wird mit künstlichen Daten simuliert; kein vom Modell
   angeforderter Hostbefehl wird ausgeführt.
6. Positive und deterministische negative Qualitätsbewertungen nach exakter
   Modell-ID, öffentlichem Versionsfingerprint und Rubrik in SQLite cachen.
   Judge-Identität und Evidenz speichern; vorübergehende APIfehler nicht als
   dauerhafte Qualitätsnote cachen.
7. Geeigneten Kandidaten nach Score, dann Rang auswählen. Andernfalls exakt
   Fallback proben und verwenden. Nicht verfügbare Modelle oder kaputte Ausgabe
   blockieren die Veröffentlichung.
8. Config schreiben; nur bei Fallback Warnreport schreiben. Free→Free-Wechsel
   erzeugt in dieser Referenz keine Nachricht. Route/Prüfzeitpunkt im Cache speichern.

**Wichtiges Fehlerverhalten:** Fehler der Ranglisten-/Kandidatenphase werden in der
Referenz als „kein qualifiziertes Free-Modell bestätigt“ behandelt und können zum
bezahlten Fallback führen. Ein fehlender Firecrawl-Key ist deshalb nicht automatisch
hartes Abbrechen. Der Installations-Preflight muss diese Voraussetzungen prüfen.

## Config veröffentlichen, nicht direkt konsumieren

Beispiel des vorhandenen Schemas (Modell-ID ist ein Platzhalter):

```json
{"provider": "custom:nous-api-key", "model": "EXACT_API_MODEL_ID"}
```

Optional kann `reasoning_effort: "low"` enthalten sein. `custom:nous-api-key` ist
hier ein festes Routinglabel für den Konsumenten, keine automatische Hermes-
Providerregistrierung. Das Paket ändert keine globale Hermes-Modellkonfiguration.

Das Skript schreibt **nur Stagingdateien**, nicht atomar in die Live-Config.
Der lokale Hoststarter muss nach Exit 0:

- reguläre Datei, maximal 4096 Byte, UTF-8/JSON und exakt erlaubte Schlüssel prüfen;
- festes Providerlabel, kurze nichtleere exakte Modell-ID und erlaubten
  Reasoning-Wert validieren; keinen Endpoint aus JSON übernehmen;
- erwartete Ordnerinhalte prüfen; Warnung nur beim freigegebenen Fallback, mit
  passenden Modelldaten, Datum und exaktem `READY`;
- Configdatei fsyncen, atomar in Liveziel ersetzen und Zielverzeichnis fsyncen;
- Warnlauf getrennt in die Delivery-Queue veröffentlichen.

Config und Warnqueue sind keine gemeinsame Transaktion. Nach Crash zwischen beiden
Schritten kann bereits Fallback aktiv sein, während die Warnung noch im Staging
liegt. Recovery muss genau diesen Lauf/Configzustand prüfen und gegebenenfalls die
Warnung nachveröffentlichen. Niemals wegen eines Fehlers die letzte gültige Config
mit halbfertigen Daten überschreiben. Der Cache ist nicht das Live-Configsignal.

## Reportmaker als Konsumenten

LLM-freie Maker bekommen weder Config noch Inferenz-Key. LLM-Maker erhalten einen
validierten readonly Snapshot plus eigenen nötigen Key, nutzen einen festen
vertrauenswürdigen Endpoint und übernehmen nur erlaubte Inferenzparameter.

Die Referenzconfig enthält **keinen** Ablaufzeitpunkt und kein Kostenbudget.
Die lokale Installation muss eine maximale Gültigkeit und Verhalten bei
Selektorausfall festlegen, beispielsweise anhand eines vertrauenswürdig gespeicherten
Publishzeitpunkts. Keine unbegrenzte „last known good“-Nutzung behaupten.

Ein täglicher Free-Check ist keine Preisgarantie für spätere Maker-Aufrufe.
Konsumenten müssen die vereinbarte Kostenpolitik unmittelbar vor ihren eigenen
Requests prüfen und Response-Kosten auswerten; bezahlten Fallback nur gemäß
Freigabe zulassen. Selbst dann sind Preisabfrage und Upstream-Billing nicht atomar.
Eine nachträgliche Kostenprüfung kann bereits entstandene Kosten nur erkennen.

## Grenzen der Bewertung

Synthetische Tests sind kein allgemeines Qualitäts- oder Injection-Sicherheitszertifikat.
Unsichtbare Modelländerungen ohne neue öffentliche Metadaten bleiben unentdeckt.
Der Referenz-Cache besitzt eine ungenutzte `checks`-Tabelle; der Code schreibt dort
keine Request-/Billinghistorie. Qualitätsbewertungen werden nicht automatisch
bereinigt oder nach Alter verworfen. Cache-Retention bei Einrichtung separat
festlegen; die Queue-Retention gilt nicht für SQLite. Keine Auditgarantie versprechen.
Sensible Originaldaten
niemals als Bewertungstest an fremde Modelle schicken.
