"""Prüft die Run-Liste: einmalige Umstellung alter Runs und sparsames Laden (ein Lesevorgang pro Run)."""
import sys, os
HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
sys.path.insert(0, HIER); sys.path.insert(0, REPO)
import fakes, requests
fakes.install_firebase()
requests.post = requests.get = lambda *a, **k: (_ for _ in ()).throw(requests.exceptions.ConnectionError())
DB = fakes.DB.store
# Bestand wie in echt: alte Runs nur als Links (ohne Eintrag in "runs"), einer mit Einstellungen
for r in range(10):
    for i in range(40):
        DB["links"][f"r{r}_{i}"] = {"run_id": f"Run {r}", "route": f"R{i}", "p1": "Mew", "status": "aktiv"}
DB["runs"]["Run 0"] = {"run_id": "Run 0", "spieler": ["Jan", "Max", ""], "anzahl_spieler": 2}

app = fakes.App(os.path.join(REPO, "web_app.py")); app.query["run"] = "Run 0"; app.run()
T = sys.modules["tracker_logik"]
T.lade_runs()                       # erster Aufruf: einmalige Umstellung
vorher = fakes.LESEN[0]; runs = T.lade_runs(); kosten = fakes.LESEN[0] - vorher
assert runs == sorted(f"Run {r}" for r in range(10)), runs
print(f"✔ Alle {len(runs)} alten Runs stehen nach der Umstellung in der Liste")
assert DB["runs"]["Run 0"]["spieler"] == ["Jan", "Max", ""], "Einstellungen dürfen nicht überschrieben werden"
print("✔ Bestehende Einstellungen (Spielernamen) bleiben bei der Umstellung erhalten")
assert kosten <= len(runs) + 1, kosten
print(f"✔ Run-Liste laden kostet {kosten} Lesevorgänge (statt aller 400 Links)")

# Neuer Link in einem Run, der nur über die Adresse geöffnet wurde -> taucht in der Liste auf
T.link_hinzufuegen("Adress-Run", "Route 1", "Jan", "Glumanda", "", "", "", "", "Gefangen")
assert "Adress-Run" in T.lade_runs()
print("✔ Neue Runs erscheinen weiterhin in der Liste")
print("\nAlle 4 Prüfungen bestanden.")
