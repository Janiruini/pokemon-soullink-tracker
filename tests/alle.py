"""Startet alle Prüfungen der App.   Aufruf:  python tests/alle.py

Braucht kein Internet, kein Firebase und kein installiertes Streamlit – nur Python und das Paket "requests".
Die Prüfungen arbeiten mit Nachbauten (tests/fakes.py) und fassen eure echten Daten nie an.
"""
import os
import subprocess
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)


def alter_code():
    """Holt die allererste Version der App aus dem Branch backup-vor-update (falls vorhanden)."""
    ordner = tempfile.mkdtemp(prefix="soullink_alt_")
    for quelle in ("origin/backup-vor-update", "backup-vor-update"):
        try:
            for datei in ("web_app.py", "tracker_logik.py"):
                inhalt = subprocess.run(["git", "-C", REPO, "show", f"{quelle}:{datei}"],
                                        capture_output=True, check=True).stdout
                with open(os.path.join(ordner, datei), "wb") as f:
                    f.write(inhalt)
            return ordner
        except Exception:
            continue
    return None


def main():
    alt = alter_code()
    if not alt:
        print("Hinweis: Branch backup-vor-update nicht gefunden – die Rückfall-Prüfung wird übersprungen.\n")
    laeufe = [("pruefungen.py", [alt or ""]), ("pruefung_runliste.py", []), ("pruefung_veraltet.py", [])]
    fehlgeschlagen = []
    for skript, argumente in laeufe:
        print(f"===== {skript} =====", flush=True)
        umgebung = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        ergebnis = subprocess.run([sys.executable, os.path.join(HIER, skript)] + argumente, cwd=REPO, env=umgebung)
        if ergebnis.returncode != 0:
            fehlgeschlagen.append(skript)
        print(flush=True)
    if fehlgeschlagen:
        print("FEHLGESCHLAGEN:", ", ".join(fehlgeschlagen))
        sys.exit(1)
    print("Alles in Ordnung: alle Prüfungen bestanden.")


if __name__ == "__main__":
    main()
