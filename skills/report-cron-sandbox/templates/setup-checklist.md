# Lokales Einrichtungsblatt

Diese Vorlage lokal ausfüllen; keine geheimen Werte und keine privaten Zieladressen
in das öffentliche Repository zurückcommitten. „Offen“ ist kein akzeptierter Default.

## Umgebung und Freigaben

- Aktives Profil / tatsächliches HERMES_HOME:
- Hermes-Version / geprüfte Cron-CLI:
- REPORT_ROOT / Dateisystem / Platzbudget:
- Docker rootless oder rootful / ausführender Nicht-root-Nutzer / UID:GID:
- Geklärte Usernamespace-/Mountrechte:
- Projektverzeichnis für lokale Implementierung:
- Freigegebene automatische Containerentfernung / Datenbereinigung / Retention:
- Freigabe für produktiven Cutover:
- Fehleralarm / technische Bestätigung:

## Für jeden Reportmaker wiederholen

- Job-ID / Name / Schedule / Zeitzone:
- Bisheriger Script-/Wrapper-/Agenten-Aufrufpfad:
- Datenquellen und engster nötiger Zugriff:
- Bisherige Reportlogik, Filter, Schwellen, Leerfall:
- Tatsächlicher LLM-Bedarf (ja/nein und warum):
- Abhängigkeiten / Image / Version oder Digest:
- Readonly Code-/Inputmounts:
- Einzelne Secretdateien (nur Pfade/Bezeichnungen, nie Werte):
- Netzwerkbedarf / verbleibendes Egressrisiko:
- Eigener state / DB / Backup- und Cursorstrategie:
- Laufverzeichnis, Dateivertrag, Limits:
- CPU / RAM / PIDs / tmpfs / Container- und Schedulerdeadline:
- Eigener Lock / SIGTERM- und Wiederanlaufbehandlung:
- Atomare Veröffentlichung / Fehlerlauf-Recovery:
- Neuer Hoststarter / Shim / alter Rollback-Aufruf:

## Modellwahl (nur falls benötigt)

- Provider und Beschaffung des Inferenz-Keys:
- Firecrawl vorhanden/erlaubt oder andere vereinbarte Ranglistenquelle:
- Exakte erlaubte IDs / Fallback (oder vereinbartes Stopverhalten):
- Erlaubte Kosten für Kandidaten, Judge, Fallback und Rankingdienst:
- Bewertungsrubrik, Sprache, Kontext-/Toolanforderungen, Rubrikversion:
- Cache neu oder eigene kompatible Migration, niemals fremde DB kopieren:
- Schedule und Vorlauf / Timeoutbudget:
- Configschema / Snapshot pro Maker / maximale Configgültigkeit:
- Preisprüfung in den Konsumenten / Verhalten bei Selektorausfall:
- Warnrouting / Recovery zwischen Config-Publish und Warnqueue:

## Delivery

- Bestehender oder neu anzulegender gemeinsamer Zustellerjob:
- Feste Job-Allowlist / Formatvalidator je Job:
- Vault-Wurzel und tatsächlich nötige Unterordnermounts:
- Ganze Reportdatei oder eigener Abschnitt einer Tagesnotiz:
- Namensregel / Abschnittmarker / Konkurrenz mit anderen Vault-Writern:
- Optionale feste Empfänger / transportsichere Formatierung:
- Statusschema / Schreibrechte / Retry / akzeptiertes Crash-Duplikatfenster:
- Aufbewahrung abgelehnter, unfertiger und vollständig zugestellter Läufe:

## Abnahme und Umstellung

- Offline-Testprotokoll:
- Containerinspect / Negativtests / Timeout und Aufräumen:
- Isolierter Testvault / markierte Testempfänger:
- Vault-Readback / Kanalbestätigung / Teilfehler und Retry:
- Backup-Pfade / DB-Konsistenzprüfung / gespeicherte alte Zieldefinitionen:
- Zielcrons einzeln geändert und zurückgelesen / andere Jobs unverändert:
- Erster echter Schedulerlauf bestätigt:
- Exakte Rollback-Befehle und Zustandserhalt:
- Offene Punkte (keine Einrichtung als abgeschlossen melden, solange relevant):
