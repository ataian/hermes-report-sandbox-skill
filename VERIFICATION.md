# Verifikationsstand des portablen Pakets

Dieses Dokument beschreibt die Prüfung des Pakets, nicht eine fertig installierte
Runtime auf einem anderen Host.

## Durchgeführt

- **37 Offline-Tests bestanden:** Selektor-Regressionen und generischer Hosthelper,
  einschließlich Ablehnung ungültiger Mountpfade und Containernamen. Ausführung
  mit Python 3.11 und pytest 9.1.1; derselbe vollständige Testlauf besteht auch
  aus einer getrennten, nur aus den Skilldateien aufgebauten Installationskopie.
- Nativer Hermes-Supportdatei-Resolver erkennt sämtliche 15 verlinkten Hilfsdateien;
  keine fehlen. Frontmatter und lokale Markdownlinks geprüft. Der geprüfte
  Releaseumfang umfasst 20 Dateien inklusive README, Lizenz und Verifikationsbericht.
- Release-Scan auf private Hostpfade/-namen, Empfängerkennungen, Schlüsselmarker und
  Credentialmuster ohne Treffer. Sichtbare Testtokens sind künstliche Fixtures.
- Den mitgelieferten Hosthelper selbst mit echtem Docker und dem synthetischen
  Maker ausgeführt: Exit 0 und erwartete Ausgabe. Produktive Quellskripte bleiben
  gegenüber ihrem Git-Stand unverändert.
- Referenz-Dockerfile tatsächlich gebaut: `report-model-selector:0.1.0`.
  Image-ID `sha256:6203a7b9c9583f725a0b649d22068b7fc34ccc5c38a04ed57c4d6a8bf249b96d`,
  Größe 55.243.761 Byte (52,68 MiB). Image-ID/Größe können sich bei späteren Builds
  durch das versionierte, aber nicht digest-fixierte Basisimage ändern.
- Echter Container mit abgeschaltetem Netzwerk, künstlichen Katalog-/APIantworten
  und ohne Schlüssel: Selektor erstellt die erwartete Config, keine Fallbackwarnung,
  Exit 0. Kein produktiver oder kostenpflichtiger API-Aufruf.
- Normaler Selektor-Entrypoint ohne Datum: erwarteter Exit 1 mit
  `selection blocked: PolicyError: one run date required`; kein Import-/Safepathfehler.
- Synthetischer Maker im echten Container: exakt `report.md` und `READY`, korrekter
  Marker, Exit 0. Keine Vault- oder Versandaktion.
- `docker inspect` bestätigt für einen realen Testcontainer: Nicht-root-Nutzer,
  readonly Rootfs, Netzwerk `none`, `cap-drop ALL`, `no-new-privileges`, 384 MiB RAM
  ohne zusätzlichen Swap, 64 PIDs, 1 CPU und begrenztes tmpfs.
- Schreibprobe im Rootfilesystem abgelehnt; Docker-Socket und Inferenz-Key fehlen
  im synthetischen Test. Automatische Entfernung des beendeten Inspect-Containers
  anschließend bestätigt. `docker wait` meldet Ende vor möglichem Abschluss der
  asynchronen Entfernung; daher Entfernung separat zurücklesen.

## Nicht als erledigt behauptet

- Keine Veröffentlichung auf GitHub und deshalb noch kein echter Download-/Install-
  Test gegen den künftigen Repositorypfad.
- Keine neue Live-Providerabnahme: verfügbare Keys, Modell-IDs und Kostenfreigabe
  müssen in der Zielumgebung geklärt werden.
- Keine universelle Delivery-/Starterruntime implementiert oder installiert.
  Joblogik, Vaultformat, Ziele, Signale/Timeouts und Publish/Retry sind Gegenstand
  der lokalen Einrichtung gemäß dem Prüfplan.
- Keine laufenden Crons, anderen Profile oder produktiven Skripte verändert.

Das mitgelieferte Selektorverhalten wurde nicht durch eine neue Paid-Sperre verändert.
Nur der fiktive Reviewername in synthetischen Testprompts ist neutral formuliert.
