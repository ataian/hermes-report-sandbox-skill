# Report-Cron Sandbox — ein portabler Hermes-Skill

Eine Bau- und Migrationsanleitung für kleine, kurzlebige Reportmaker-Container.
**Kein Komplettdienst, kein automatischer Cronumbau, keine privaten Reportskripte.**

## Methode

1. **Reportmaker:** Quellen abrufen, verarbeiten, Bericht in genau einen eigenen
   Staginglauf schreiben. Kein Vault, kein Versand, kein gesamtes Hermes-Profil.
   Container endet und wird verworfen; der Host veröffentlicht nur fertige Ausgabe.
2. **Delivery:** deterministisch prüfen, an fest konfigurierte Vault-/Versandziele
   liefern, Teilfortschritt merken und erst nach vollständigem Erfolg bereinigen.
3. **Modellwahl:** separater Selektor und Cache, kleine validierte gemeinsame Config.
   Nur Maker mit echtem LLM-Bedarf lesen sie readonly. Keine Cronmutation.

Der vorhandene Hermes-Scheduler bleibt bestehen und ruft feste Hoststarter als
script-only Jobs auf. Die Container enthalten nur ihre tatsächlichen Abhängigkeiten.

## Inhalt

- [SKILL.md](skills/report-cron-sandbox/SKILL.md): direkt installierbarer Skill.
- `references/`: Architektur, Einrichtung/Migration, Delivery, Modellwahl und Prüfplan.
- `templates/setup-checklist.md`: offene lokale Entscheidungen beim Installieren klären.
- `scripts/select.py`: eigenständig nutzbarer Nous-/Firecrawl-Modellselektor, keine
  vollständige Agentenruntime. Bestehende Policy mit Free-Bevorzugung und exaktem
  `deepseek/deepseek-v4-flash`-Fallback; auch Judge-Aufrufe können bezahlt sein.
- `scripts/host_common.py`: wiederverwendbare Host-Pfad-/Lockprüfung und begrenztes
  Docker-Run. Keine vollständige Starter-/Deliveryimplementierung.
- Dockerfile, synthetischer Maker und Offline-/Container-Smoke-Tests.

## Installation von GitHub

Nach Veröffentlichung den echten Repo-Pfad verwenden (über Hermes `terminal`):

```sh
hermes skills install OWNER/REPO/skills/report-cron-sandbox
```

`OWNER/REPO` ist ein Platzhalter. Alternativ geprüften Checkout herunterladen und
**den vollständigen** Ordner `skills/report-cron-sandbox` in das Skills-Verzeichnis
des richtigen Hermes-Profils kopieren; bestehende Installation nicht überschreiben.
Die Details und Profilgrenzen stehen in der Aufbauanleitung.

Keine Installationsaktion in diesem Repository startet Docker oder verändert Crons.
Der einrichtende Agent muss Abhängigkeiten, Credentials, Ziele und Freigaben zuerst
mit der tatsächlichen Umgebung abgleichen. Die native GitHub-Installation ist erst
nach Veröffentlichung gegen den echten Repo-Pfad prüfbar; lokale Pakettests ersetzen
diesen Nachweis nicht.

## Auftrag an den anderen Agenten

> Lies den Skill `report-cron-sandbox` vollständig und prüfe meine vorhandenen
> Report-Crons. Erstelle anhand des Einrichtungsblatts eine konkrete Zuordnung von
> Reportmakern, State, Credentials, Vault-/Versandzielen und gegebenenfalls Modellwahl.
> Kläre mit mir nur die offenen Entscheidungen und notwendigen Freigaben.
> Verwende die mitgelieferten Bausteine, erhalte die bestehende Reportlogik und
> stelle danach die freigegebenen Jobs einzeln mit Tests und Rollback um.
> Installieren des Skills allein ist noch keine Freigabe für Produktivänderungen.

## Voraussetzungen und Grenzen

Linux und funktionierender Docker-Zugang; Python ab 3.11 für Hostcode/Tests,
`pytest` nur zum Testen. Referenzimage Python 3.12 Alpine. Keine Systeminstallation
oder Docker-/Netzwerkänderung ohne lokale Freigabe. macOS/Windows sind für diesen
Linux-spezifischen Pfad-/Rechtehelper nicht als geprüft zugesagt.

Der Selektor benötigt Nous-Inferenzzugang und für neue Kandidatensuche Firecrawl.
API-Keys, bezahlter Judge/Fallback, Rankingsquelle und Rubrik sind **Einrichtungsfragen**.
Weder heimliche Paid-Sperre noch automatische Kostenfreigabe durch Skillinstallation.
Docker begrenzt Zugriffe, garantiert aber keine sicheren/faktisch richtigen Texte
oder gesperrten Netzverkehr.

## Verifikation

Siehe [Prüfplan](skills/report-cron-sandbox/references/verification.md) und
[Verifikationsstand des Pakets](VERIFICATION.md). Die Tests enthalten ausschließlich
synthetische Daten; ein Offline-PASS ersetzt keine lokale API-/Deliveryabnahme.

## Veröffentlichung

Das Repository enthält nur Anleitung, Templates, ausgewählte Hilfen und Tests.
Runtime, Secrets, DBs, Queue, private lokale Einrichtungsblätter und Backups gehören
außerhalb dieses Repositories. Vor jedem Push auch den tatsächlich gestagten Inhalt
prüfen; `.gitignore` ist kein Geheimnisscanner. Keine fremde Deploymenthistorie
importieren. Lizenz: MIT, siehe [LICENSE](LICENSE).
