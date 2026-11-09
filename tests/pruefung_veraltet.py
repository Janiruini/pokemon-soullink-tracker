"""Prüft den Schutz gegen eine veraltete tracker_logik im Speicher von Streamlit.

Hintergrund: Streamlit lädt nach einem Update manchmal nur web_app.py neu. web_app.py vergleicht deshalb
eine Versionsnummer (ERWARTETE_LOGIK_VERSION / MODUL_VERSION) und lädt tracker_logik bei Abweichung selbst neu.
"""
import sys, os
HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
sys.path.insert(0, HIER); sys.path.insert(0, REPO)
import fakes, requests
fakes.install_firebase()
requests.post = requests.get = lambda *a, **k: (_ for _ in ()).throw(requests.exceptions.ConnectionError())
DB = fakes.DB.store
DB["links"]["a"] = {"run_id": "Platin1", "route": "R1", "p1": "Chelast", "status": "aktiv"}
DB["links"]["b"] = {"run_id": "Platin1", "route": "R2", "p1": "Staralili", "status": "friedhof"}
DB["links"]["c"] = {"run_id": "Standard_Run", "route": "R1", "p1": "Pikachu", "status": "aktiv"}
app = fakes.App(os.path.join(REPO, "web_app.py")); app.query["run"] = "Platin1"; app.run()
# Situation wie auf Streamlit Cloud: alte Logik im Speicher (ohne run_loeschen / Version)
tl = sys.modules["tracker_logik"]; del tl.run_loeschen; del tl.MODUL_VERSION
assert not hasattr(sys.modules["tracker_logik"], "run_loeschen")
app.state["loesch_bestaetigung_Platin1"] = "Platin1"; app.click("run_loeschen_Platin1")
assert not any(d["run_id"] == "Platin1" for d in DB["links"].values()), "Platin1 nicht gelöscht"
assert any(d["run_id"] == "Standard_Run" for d in DB["links"].values())
print("✔ Veraltete Logik wird automatisch neu geladen (Run löschen funktioniert, andere Runs unberührt)")

import re
web = open(os.path.join(REPO, "web_app.py"), encoding="utf-8").read()
logik = open(os.path.join(REPO, "tracker_logik.py"), encoding="utf-8").read()
erwartet = int(re.search(r"^ERWARTETE_LOGIK_VERSION = (\d+)", web, re.M).group(1))
modul = int(re.search(r"^MODUL_VERSION = (\d+)", logik, re.M).group(1))
assert erwartet == modul, f"Versionsnummern passen nicht: web_app erwartet {erwartet}, tracker_logik hat {modul}"
print(f"✔ Versionsnummern stimmen überein ({modul})")
print("\nAlle 2 Prüfungen bestanden.")
