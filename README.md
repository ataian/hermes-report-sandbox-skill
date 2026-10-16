# Report-Cron Sandbox für Hermes Agent

Ein installierbarer [Hermes-Agent-Skill](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills),
um Report-Crons in kleine, kurzlebige Docker-Container zu verlagern und die
Reporterstellung von der Zustellung zu trennen.

Das Repository enthält eine **Aufbau- und Migrationsanleitung mit wiederverwendbaren
Python-Helfern, Docker-Vorlage und Tests**. Der einrichtende Agent passt sie an die
vorhandenen Reports, Zugänge und Ablageziele an. Der bestehende Hermes-Scheduler
bleibt erhalten; eine vollständige Hermes-Installation in jedem Container ist
nicht erforderlich.

## Installation

Im Terminal der gewünschten Hermes-Umgebung ausführen:

```sh
hermes skills install ataian/hermes-report-sandbox-skill/skills/report-cron-sandbox
```

Bei mehreren Hermes-Profilen darauf achten, den Skill im vorgesehenen Profil zu
installieren. Die Installation macht die Anleitung und ihre Hilfsdateien verfügbar.
**Sie startet keine Report-Container und stellt keine vorhandenen Crons um.**

Anschließend in Hermes beispielsweise diesen Auftrag geben:

> Lade den Skill `report-cron-sandbox` und prüfe meine vorhandenen Report-Crons.
> Erstelle anhand des Einrichtungsblatts eine konkrete Zuordnung von Reportmakern,
> Zustand, benötigten Zugängen, Vault-Ablage und Versandzielen. Prüfe, welche Jobs
> tatsächlich ein LLM benötigen. Kläre mit mir die offenen Entscheidungen und
> erforderlichen Freigaben. Stelle anschließend die freigegebenen Jobs einzeln um,
> erhalte ihre bestehende Reportlogik und prüfe die Einrichtung mit Tests und Rollback.

Alternativ lässt sich das Repository zum Lesen, Anpassen oder Testen auschecken:

```sh
git clone https://github.com/ataian/hermes-report-sandbox-skill.git
cd hermes-report-sandbox-skill
```

Ein Checkout allein installiert den Skill noch nicht. Die manuelle Installation
und der Umgang mit vorhandenen Profilen sind in der
[Einrichtungsanleitung](skills/report-cron-sandbox/references/setup-and-migration.md)
beschrieben.

## Die Methode

Die Aufgaben werden in drei getrennte Rollen aufgeteilt:

| Rolle | Aufgabe | Zugriffsgrenze |
|---|---|---|
| **Reportmaker** | Quellen abrufen, verarbeiten und einen Bericht erzeugen | Nur eigener Code, notwendige Zugänge, optional eigener Zustand und genau ein Ausgabe-Laufverzeichnis; kein Versand und kein Vault-Zugriff |
| **Delivery** | Fertige Berichte technisch prüfen, im Vault ablegen und optional versenden | Feste, außerhalb des Reports konfigurierte Ziele; keine frei agierende LLM-Schleife |
| **Modellselektor** | Ein geeignetes freies Modell auswählen und eine gemeinsame Konfiguration bereitstellen | Eigener Cache und eigene Ausgabe; keine Änderungen an Cronjobs |

```text
Hermes-Scheduler → Hoststarter → Reportmaker-Container
                                      │
                               report.md + READY
                                      │
                         Container beendet und entfernt
                                      │
                         Host prüft und veröffentlicht
                                      ▼
                                    Queue
                                      │
                              Delivery-Container
                                      │
                         Vault + optionale Versandziele

Modellselektor → geprüfte Modellkonfiguration → nur Maker mit LLM-Bedarf
```

Der Reportmaker arbeitet möglichst vollständig in seiner Sandbox. Seine Ausgabe
wird erst nach erfolgreichem Containerende und technischer Prüfung veröffentlicht.
**Das Entfernen des Containers löscht nicht den Bericht:** Dieser bleibt bis zur
vollständig bestätigten Zustellung erhalten. Delivery merkt sich Teilerfolge,
sodass ein Retry bereits abgeschlossene Schritte nicht regulär wiederholt.

## Was enthalten ist

| Datei oder Bereich | Inhalt |
|---|---|
| [SKILL.md](skills/report-cron-sandbox/SKILL.md) | Einstieg und Arbeitsablauf für den einrichtenden Agenten |
| [Architektur](skills/report-cron-sandbox/references/architecture.md) | Vertrauensgrenzen, Verzeichnisplan und Übergabevertrag |
| [Einrichtung und Migration](skills/report-cron-sandbox/references/setup-and-migration.md) | Aufbau, Hoststarter, gezielter Cron-Cutover und Rollback |
| [Delivery](skills/report-cron-sandbox/references/delivery.md) | Validierung, Vault-Ablage, Zustellstatus, Retry und Bereinigung |
| [Modellwahl](skills/report-cron-sandbox/references/model-selection.md) | Ablauf, Voraussetzungen und Kostenverhalten des Referenzselektors |
| [Einrichtungsblatt](skills/report-cron-sandbox/templates/setup-checklist.md) | Checkliste für die lokale Umgebung und offene Entscheidungen |
| [select.py](skills/report-cron-sandbox/scripts/select.py) | Eigenständiger Nous-/Firecrawl-Modellselektor |
| [host_common.py](skills/report-cron-sandbox/scripts/host_common.py) | Hostseitige Pfad-/Lockprüfung und begrenzter Docker-Aufruf |
| [Dockerfile](skills/report-cron-sandbox/templates/selector.Dockerfile) | Minimales Dependency-Image für den Selektor; Code wird readonly gemountet |
| [Tests](skills/report-cron-sandbox/scripts/tests) | Offline-Regressionen und synthetischer Container-Smoke-Test |

**Nicht enthalten:** individuelle fachliche Reportmaker, ein universeller
Vault-/Versandsender oder ein automatischer Produktivinstaller. Die Anleitung
beschreibt, wie vorhandene Funktionen übernommen und die nötigen lokalen Starter
und Zustellschritte ergänzt werden.

## Voraussetzungen und lokale Entscheidungen

Für die beschriebene Runtime werden Linux, ein funktionierender Docker-Zugang und
Python ab 3.11 benötigt. Das Referenzimage verwendet Python 3.12 Alpine; `pytest`
ist nur für die Tests erforderlich. Die Linux-spezifischen Pfad- und Rechteprüfungen
sind nicht als macOS-/Windows-kompatibel zugesagt.

Bei der Einrichtung klärt der Agent insbesondere:

- welche Datenquellen, Bibliotheken und Zugangsdaten jeder Maker wirklich braucht;
- ob und wo Zustand oder Datenbanken dauerhaft gespeichert werden müssen;
- welches Vault verwendet wird und wie Berichte dort abgelegt werden sollen;
- welche Versand- und Fehlerziele gewünscht sind;
- welche Zeitpläne, Ressourcenlimits und Aufbewahrungsregeln gelten;
- ob Modellwahl benötigt wird und welche Provider und Kosten erlaubt sind.

API-Keys und andere Geheimnisse werden lokal bereitgestellt, nicht im Repository
oder in Berichten hinterlegt. Die Skillinstallation ist keine Freigabe für
Produktivänderungen, zusätzliche API-Kosten oder Änderungen an Docker und Netzwerk.

### Optionaler Modellselektor

Deterministische Reports benötigen weder ein LLM noch den Selektor. Die enthaltene
Referenz ist für **Nous-Inferenz und Firecrawl** ausgelegt: Sie bevorzugt ein
geprüftes kostenloses Modell und verwendet `deepseek/deepseek-v4-flash` als exakten
Fallback. Dieser Fallback und die LLM-gestützte Qualitätsbewertung können Kosten
verursachen; auch Firecrawl kann kostenpflichtig sein.

Benötigte Keys, zulässige Kosten, verfügbare Modell-IDs und Bewertungsmaßstab müssen
vor dem ersten echten Lauf geklärt werden. Für andere Provider oder eine andere
Kostenpolitik wird die Referenz gezielt angepasst. Details stehen in der
[Selektor-Dokumentation](skills/report-cron-sandbox/references/model-selection.md).

## Sicherheitsgrenzen

Die Trennung begrenzt die Dateien und Fähigkeiten, auf die ein Reportmaker
zugreifen kann. Sie garantiert weder faktisch richtige Berichte noch Schutz vor
jeder Prompt Injection. Mitgegebene API-Keys bleiben im Container lesbar; normales
Docker-Netzwerk ist keine Egress-Allowlist.

Delivery behandelt Reports ausschließlich als Daten. Pfade, Empfänger und Befehle
werden niemals aus dem Report übernommen. Auch nachgelagerte Agenten müssen
Berichtsinhalte als unvertrauenswürdige Quellen behandeln.

## Tests und Abnahme

Aus einem Checkout, mit Python ab 3.11 und `pytest` in der verwendeten Testumgebung:

```sh
cd skills/report-cron-sandbox
python -c "from pathlib import Path; Path('.verification').mkdir(mode=0o700, exist_ok=True)"
python -m pytest -q --basetemp=.verification/pytest scripts/tests
```

Das angegebene Testverzeichnis ist ausschließlich für temporäre Testdaten bestimmt;
Pytest kann es bei erneuter Ausführung bereinigen. Die Offline-Tests verwenden
synthetische Daten und benötigen keine API-Keys.

Der [Verifikationsbericht](VERIFICATION.md) dokumentiert die Paketprüfung. Der
[Prüfplan](skills/report-cron-sandbox/references/verification.md) beschreibt zusätzlich
die echten Container-, Übergabe-, Vault-, Versand- und Retry-Tests für eine lokale
Einrichtung. Bestandene Pakettests ersetzen keine Abnahme der eigenen Report-Crons.

## Lizenz

[MIT](LICENSE). Lokale Runtime-Daten, Secrets, Datenbanken, Berichte und private
Einrichtungsblätter gehören nicht in dieses Repository.
