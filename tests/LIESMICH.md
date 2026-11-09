# Automatische Prüfungen

Diese Prüfungen spielen die komplette App durch – Eintragen, Dupes Clause, Static, Team, Friedhof, Bearbeiten,
Löschen, Passwortschutz, Level-Caps, Orden-Koffer, Fangchance (Gen 1–5), Schwächen, Zwischenspeicher – und
melden, wenn eine Änderung etwas kaputt macht.

## Starten

```
python tests/alle.py
```

Voraussetzung: Python und das Paket `requests` (`pip install requests`). Internet, Firebase oder ein
installiertes Streamlit werden **nicht** gebraucht: Die Prüfungen arbeiten mit Nachbauten (`fakes.py`)
und fassen die echten Daten nie an.

## Automatisch bei jedem Push

GitHub startet die Prüfungen bei jedem Push von selbst (`.github/workflows/pruefungen.yml`).
Das Ergebnis steht im Repository unter **Actions**: grüner Haken = alles in Ordnung, rotes Kreuz = etwas ist kaputt.
Die App auf Streamlit wird davon nicht beeinflusst.

## Dateien

| Datei | Inhalt |
| --- | --- |
| `alle.py` | Startet alle Prüfungen |
| `pruefungen.py` | Die große Prüfung (über 200 Einzelprüfungen) |
| `pruefung_runliste.py` | Run-Liste: Umstellung alter Runs, sparsames Laden |
| `pruefung_veraltet.py` | Schutz gegen veraltete Logik im Speicher, Versionsnummern |
| `fakes.py` | Nachbauten von Firebase und Streamlit |

## Grenzen

Die Nachbauten prüfen die **Logik** und was gezeichnet wird, aber nicht, wie die Seite im Browser aussieht.
Design-Änderungen (CSS) muss man sich weiterhin auf der echten Seite ansehen.
