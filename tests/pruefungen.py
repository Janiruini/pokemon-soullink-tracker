"""Die große Prüfung: spielt die App mit nachgebautem Firebase/Streamlit komplett durch.

Aufruf:  python tests/pruefungen.py [ORDNER_MIT_ALTEM_CODE]
Der optionale Ordner enthält die allererste Version der App (Branch backup-vor-update); damit wird
geprüft, dass ein Zurücksetzen auf den alten Code mit den heutigen Daten weiterhin funktioniert.
Am einfachsten über  python tests/alle.py  starten – das kümmert sich um alles.
"""
import sys, os, importlib
HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
ALT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None
sys.path.insert(0, HIER)
import fakes, requests
fakes.install_firebase()

api_aufrufe = []
def kein_netz(*a, **k):
    api_aufrufe.append(a[0] if a else k.get("url")); raise requests.exceptions.ConnectionError("offline")
requests.post = requests.get = kein_netz

def neue_app(ordner):
    for m in ["tracker_logik"]: sys.modules.pop(m, None)
    while ordner in sys.path: sys.path.remove(ordner)
    for o in (REPO, ALT):
        while o and o in sys.path: sys.path.remove(o)
    sys.path.insert(0, ordner)
    return fakes.App(os.path.join(ordner, "web_app.py"))

ok = 0
def check(bed, text):
    global ok
    assert bed, "FEHLER: " + text
    ok += 1; print("  ✔", text)

DB = fakes.DB.store
# --- Bestehende Daten wie im alten Format (getippte Namen, Kleinschreibung, fehlende Felder) ---
DB["links"]["alt1"] = {"run_id": "Standard_Run", "route": "Route 1", "n1": "Jan", "p1": "pikachu", "i1": {"bild": "x.png", "typen": ["Elektro"]},
                       "n2": "Max", "p2": "Taubsi", "i2": None, "n3": "", "p3": "", "i3": None, "status": "aktiv", "in_team": True}
DB["links"]["alt2"] = {"run_id": "Standard_Run", "route": "Route 2", "n1": "Jan", "p1": "Raupy", "i1": {}, "n2": "Max", "p2": "Hornliu",
                       "status": "friedhof"}
DB["links"]["alt3"] = {"run_id": "Standard_Run", "route": "Vertania Wald", "n1": "Jan", "p1": "Pikatchu", "n2": "", "p2": "", "status": "verpasst", "in_team": False}
DB["links"]["anderer"] = {"run_id": "Run Kumpel", "route": "Route 1", "n1": "A", "p1": "Glumanda", "status": "aktiv"}

print("1) Neue App startet mit alten Daten")
app = neue_app(REPO).run()
check("Standard_Run" in app.state["run_auswahl"], "Standard_Run ist vorausgewählt")
check(app.query.get("run") == "Standard_Run", "Run steht in der Adresse (bleibt beim Neuladen)")
check(any("Aktive Links (1)" in t and "Friedhof (1)" in t and "Verpasste Encounter (1)" in t for t in app.texts("tabs")), "Tabs zeigen Zähler")
check("⚔️ Im Team=1/6" in app.texts("metric"), "Übersicht zeigt Team 1/6")
check(app.texts("popover").count("🛠️") == 2 and app.texts("popover").count("🗑️") == 1
      and {"e_alt1", "e_alt2", "e_alt3"} <= app.keys_this_run,
      "Listen-Links: Aktionsmenü; jeder Link hat einen Bearbeiten-Knopf")
check(any("class='pc-tab pc-friedhof'" in t for t in app.texts("md")) and any("<b>Max:</b> Hornliu" in t for t in app.texts("md")),
      "Kompakte Zeile: Routen-Reiter + 'Trainer: Pokémon'")
check(any("Nächster Cap" in t and "Lv 14" in t for t in app.texts("success", "sidebar")), "Nächster Level-Cap wird angezeigt")

print("2) Eintragen: Pflichtfelder, Route-Check, Dupes, Static")
app.click("btn_gefangen")
check(any("mindestens eine Route" in t for t in app.texts("warning")), "Leeres Formular -> Warnung")
fn = app.state["formular_nr"]
app.state[f"route_{fn}"] = "route 1"; app.state[f"p_0_{fn}"] = "Glumanda"
app.click("btn_gefangen")
check(any("existiert bereits" in t for t in app.texts("error")), "Doppelte Route wird blockiert (Groß/Klein egal)")
app.state[f"route_{fn}"] = "Route 3"; app.state[f"p_0_{fn}"] = "Raichu"
app.click("btn_gefangen")
check(any("Dupes" in t and "Pikachu" in t for t in app.texts("error")), "Raichu blockiert wegen altem 'pikachu' (Entwicklungsreihe)")
app.state[f"p_0_{fn}"] = "Smettbo"
app.click("btn_gefangen")
check(any("Dupes" in t for t in app.texts("error")), "Smettbo blockiert wegen Raupy auf dem Friedhof")
app.set("n_Standard_Run_0", "Jan"); app.state[f"p_0_{fn}"] = "Glumanda"
app.click("btn_gefangen")
check(any("Erfolgreich gespeichert" in t for t in app.texts("success")), "Erfolgsmeldung bleibt nach dem Speichern sichtbar")
check(app.state["formular_nr"] == fn + 1 and app.state.get(f"route_{fn+1}") == "", "Formular wird danach geleert")
neu = [d for d in DB["links"].values() if d.get("route") == "Route 3"][0]
check(neu["status"] == "aktiv" and neu["in_team"] is False and neu["i1"]["typen"] == ["Feuer"] and neu["i1"]["bild"].endswith("/4.png"), "Neuer Link im alten Format inkl. Bild+Typ")
check(set(neu) == {"run_id","route","n1","p1","i1","n2","p2","i2","n3","p3","i3","status","in_team"}, "Gleiche Felder wie bisher")
fn += 1
app.state[f"route_{fn}"] = "Static Mewtu"; app.state[f"p_0_{fn}"] = "Glumanda"
app.click("btn_gefangen")
check(any("Static Bonus" in t for t in app.texts("success")), "Static-Joker umgeht die Prüfungen")
fn += 1
app.state[f"route_{fn}"] = "Route 4"
app.state[f"p_0_{fn}"] = "Rattfratz"
app.click("btn_verpasst")
check([d for d in DB["links"].values() if d.get("route") == "Route 4"][0]["status"] == "verpasst", "Button 'Verpasst speichern' speichert als verpasst")
check(api_aufrufe == [], "Keine Internet-Abfragen nötig für bekannte Pokémon")

print("3) Team, Verpasst, Friedhof, Zurückholen")
ids = {d["route"]: i for i, d in DB["links"].items() if d["run_id"] == "Standard_Run"}
app.set(f"team_{ids['Route 3']}", True)
check(DB["links"][ids["Route 3"]]["in_team"] is True, "Ins Team setzen")
for r in range(5, 11):
    DB["links"][f"t{r}"] = {"run_id": "Standard_Run", "route": f"R{r}", "p1": "Mew", "status": "aktiv", "in_team": False}
app.run()
for r in range(5, 9): app.set(f"team_t{r}", True)
app.set("team_t9", True)
check(any("Team ist bereits voll" in t for t in app.texts("error")) and not DB["links"]["t9"]["in_team"], "7. Teammitglied wird abgelehnt")
app.click(f"f_{ids['Route 3']}")
check(DB["links"][ids["Route 3"]]["status"] == "friedhof" and not DB["links"][ids["Route 3"]]["in_team"], "💀 -> Friedhof, raus aus dem Team")
app.click(f"a_{ids['Route 3']}")
check(DB["links"][ids["Route 3"]]["status"] == "aktiv", "♻️ holt vom Friedhof zurück")
app.click(f"v_{ids['Route 3']}")
check(DB["links"][ids["Route 3"]]["status"] == "verpasst", "🏃 -> Verpasst")
app.click(f"a_{ids['Route 3']}")

print("4) Löschen nur mit Bestätigung")
anzahl = len(DB["links"])
app.run()
check(len(DB["links"]) == anzahl, "Öffnen der Löschabfrage löscht nichts")
check("d_t10" not in app.keys_this_run, "'Ja, löschen' erscheint erst nach 'Löschen'")
app.click("dfrage_t10")
check("d_t10" in app.keys_this_run and "t10" in DB["links"], "Rückfrage erscheint, noch nichts gelöscht")
app.click("dnein_t10")
check("d_t10" not in app.keys_this_run and "t10" in DB["links"], "'Abbrechen' schließt die Rückfrage")
app.click("dfrage_t10")
app.click("d_t10")
check("t10" not in DB["links"] and any("gelöscht" in t for t in app.texts("success")), "'Ja, löschen' löscht den Link")

print("5) Bearbeiten (z.B. Entwicklung)")
check(f"ep_{ids['Route 3']}_0" not in app.keys_this_run and not app.texts("dialog"), "Bearbeiten-Formular wird erst auf Klick aufgebaut")
app.click(f"e_{ids['Route 3']}")
check(app.texts("dialog") == ["Link bearbeiten"] and f"ep_{ids['Route 3']}_0" in app.keys_this_run, "Klick auf Bearbeiten öffnet das Fenster mit dem Formular")
app.set(f"ep_{ids['Route 3']}_0", "Glutexo")
check(app.texts("dialog") == ["Link bearbeiten"], "Fenster bleibt beim Auswählen offen")
app.click(f"submit_edit_{ids['Route 3']}")
check(not app.texts("dialog"), "Nach dem Speichern schließt sich das Fenster")
e = DB["links"][ids["Route 3"]]
check(e["p1"] == "Glutexo" and e["i1"]["bild"].endswith("/5.png") and e["status"] == "aktiv", "Pokémon geändert, Bild aktualisiert, Status bleibt")
app.click("e_alt3")
check(app.state.get("ep_alt3_0") == "Pikatchu", "Alter Tippfehler-Name bleibt im Bearbeiten-Feld wählbar")
app.set("ep_alt3_0", "Pikachu"); app.click("submit_edit_alt3")
check(DB["links"]["alt3"]["p1"] == "Pikachu", "Tippfehler lässt sich korrigieren")

print("6) Spieler & Run-Einstellungen bleiben gespeichert")
app.click("btn_➕ Spieler hinzufügen")
app.set("n_Standard_Run_1", "Max")
app2 = neue_app(REPO); app2.query["run"] = "Standard_Run"; app2.run()
check(app2.state["anzahl_Standard_Run"] == 2 and app2.state["n_Standard_Run_1"] == "Max" and app2.state["n_Standard_Run_0"] == "Jan", "Nach Neuladen: 2 Spieler, Namen da")
app2.click("btn_➖ Spieler entfernen")
check(app2.state["anzahl_Standard_Run"] == 1, "Spieler entfernen")

print("7) Run-Auswahl & neuer Run")
app2.set("run_auswahl", "Run Kumpel")
check(app2.query["run"] == "Run Kumpel" and any("Run Kumpel" in t for t in app2.texts("caption")), "Wechsel auf anderen Run")
check(any("Aktive Links (1)" in t for t in app2.texts("tabs")), "Nur Daten dieses Runs sichtbar")
app2.set("run_auswahl", "➕ Neuen Run anlegen…")
app2.state["neuer_run_name"] = "standard_run"; app2.click("btn_Run anlegen")
check(any("gibt es schon" in t for t in app2.texts("warning", "sidebar")), "Doppelter Run-Name wird verhindert")
app2.state["neuer_run_name"] = "Platin Run"; app2.click("btn_Run anlegen")
check(app2.state["run_auswahl"] == "Platin Run" and app2.query["run"] == "Platin Run", "Neuer Run angelegt und ausgewählt")

print("8) Level-Cap-Fortschritt")
app2.set("spiel_Platin Run", "Gen 4: Platin")
sk = "Gen_4_Platin"
app2.set(f"orden_Platin Run_{sk}_0", True); app2.set(f"orden_Platin Run_{sk}_1", True)
check(any("Nächster Cap" in t and "Lv 26" in t for t in app2.texts("success", "sidebar")), "Nach 2 Arenen: nächster Cap Lv 26")
check(any("Lv 26" in t for t in app2.texts("caption", "main")), "Nächster Cap auch oben im Hauptbereich")
app3 = neue_app(REPO); app3.query["run"] = "Platin Run"; app3.run()
check(app3.state["spiel_Platin Run"] == "Gen 4: Platin" and app3.state[f"orden_Platin Run_{sk}_1"] is True, "Spiel + Haken bleiben nach Neuladen")
app3.set("spiel_Platin Run", "Gen 7: Sonne/Mond")
check(not app3.texts("success", "sidebar") and any("Hinweis" in t for t in app3.texts("md")), "Sonne/Mond (nur Hinweis) funktioniert ohne Fehler")
check("Kämpfe abhaken" in app3.texts("expander") and "ordenkoffer" not in app3.texts("container"), "Sonne/Mond: kein Orden-Koffer, Liste direkt offen")
app3.set("spiel_Platin Run", "Gen 9: Karmesin/Purpur")
for i, c in enumerate(["x"] * 12):
    k = f"cap_Platin Run_Gen_9_Karmesin_Purpur_{i}"
    if k not in app3.state: k = f"orden_Platin Run_Gen_9_Karmesin_Purpur_{i}"
    if k in app3.state: app3.set(k, True)
check(any("Alle Caps geschafft" in t for t in app3.texts("success", "sidebar")), "Alle abgehakt -> 'Alle Caps geschafft'")

print("9) Rückfallsicherheit: ALTER Code läuft mit den neuen Daten")
if ALT:
    alt = neue_app(ALT)
    alt.state["n_0"] = ""
    alt.run()
    check(any("Aktive Links" in t for t in alt.texts("tabs")), "Alte App startet fehlerfrei mit den jetzt gespeicherten Daten")
    alt.state["auto_Name des Runs:"] = "Platin Run"; alt.run()
    check(True, "Alte App kommt auch mit dem neuen Run klar")
else:
    print("  – übersprungen (kein alter Code angegeben)")

print("10) Run löschen")
d = neue_app(REPO); d.query["run"] = "Run Kumpel"; d.run()
check("🗑️ Run löschen" in d.texts("expander"), "Aufklappmenü 'Run löschen' ist da")
check(any("**1 Link**" in t for t in d.texts("md")), "Zeigt an, wie viele Links gelöscht werden")
vorher_std = len([x for x in DB["links"].values() if x["run_id"] == "Standard_Run"])
d.click("run_loeschen_Run Kumpel")
check(any(x["run_id"] == "Run Kumpel" for x in DB["links"].values()), "Ohne Namens-Bestätigung wird NICHTS gelöscht")
d.set("loesch_bestaetigung_Run Kumpel", "run kumpel"); d.click("run_loeschen_Run Kumpel")
check(any(x["run_id"] == "Run Kumpel" for x in DB["links"].values()), "Falsch geschriebener Name löscht nichts")
d.state["loesch_bestaetigung_Run Kumpel"] = "Run Kumpel"; d.click("run_loeschen_Run Kumpel")
check(not any(x["run_id"] == "Run Kumpel" for x in DB["links"].values()), "Alle Links des Runs sind gelöscht")
check(len([x for x in DB["links"].values() if x["run_id"] == "Standard_Run"]) == vorher_std, "Andere Runs bleiben komplett erhalten")
check(any("gelöscht" in t for t in d.texts("success")), "Erfolgsmeldung nach dem Löschen")
check(d.state["run_auswahl"] != "Run Kumpel" and d.query.get("run") != "Run Kumpel", "App wechselt automatisch auf einen anderen Run")
d.set("run_auswahl", "Platin Run")
d.state["loesch_bestaetigung_Platin Run"] = "Platin Run"; d.click("run_loeschen_Platin Run")
check("Platin Run" not in [x.get("run_id") for x in DB["runs"].values()], "Run-Einstellungen (Spieler, Caps) sind mit gelöscht")
check("Platin Run" not in d.state["run_auswahl"], "Gelöschter Run taucht nicht mehr in der Auswahl auf")

print("11) Passwortschutz")
import fakes as F
o = neue_app(REPO); o.query["run"] = "Standard_Run"; o.run()
check(any("Kein Passwort" in t for t in o.texts("info", "sidebar")), "Run ohne Passwort ist offen (wie bisher)")
o.state["pw_neu1_Standard_Run"] = "abc"; o.state["pw_neu2_Standard_Run"] = "abc"; o.click("pw_speichern_Standard_Run")
check(any("mindestens 4" in t for t in o.texts("error")), "Zu kurzes Passwort wird abgelehnt")
o.state["pw_neu1_Standard_Run"] = "pika1234"; o.state["pw_neu2_Standard_Run"] = "pika9999"; o.click("pw_speichern_Standard_Run")
check(any("stimmen nicht" in t for t in o.texts("error")), "Ungleiche Wiederholung wird abgelehnt")
o.state["pw_neu2_Standard_Run"] = "pika1234"; o.click("pw_speichern_Standard_Run")
check(o.query.get("schluessel") and any("Passwort gespeichert" in t for t in o.texts("success")), "Passwort gesetzt, Besitzer bleibt freigeschaltet")
runs_doc = [d for d in DB["runs"].values() if d.get("run_id") == "Standard_Run"][0]
check("pika1234" not in str(runs_doc) and runs_doc.get("pw_hash"), "In der Datenbank steht nur ein Hash, nicht das Passwort")
eigener_link = dict(o.query)

k = neue_app(REPO); k.query["run"] = "Standard_Run"; k.run()   # Kollege ohne Passwort
check(any("Geschützter Run" in t for t in k.texts("warning", "sidebar")) and any("geschützt" in t for t in k.texts("info")), "Kollege sieht: geschützt, nur ansehen")
check(any("Aktive Links" in t for t in k.texts("tabs")), "Kollege kann den Run trotzdem ansehen")
check("🗑️ Run löschen" not in k.texts("expander"), "Run-löschen-Menü ist für ihn ausgeblendet")
vorher = {i: dict(d) for i, d in DB["links"].items()}
fn = k.state["formular_nr"]; k.state[f"route_{fn}"] = "Route 99"; k.state[f"p_0_{fn}"] = "Mew"; k.click("btn_gefangen")
ziel = next(i for i, d in DB["links"].items() if d["run_id"] == "Standard_Run" and d["status"] == "aktiv")
k.click(f"f_{ziel}"); k.click(f"d_{ziel}"); k.click(f"e_{ziel}"); check(not k.texts("dialog"), "Gesperrt: Bearbeiten-Fenster öffnet nicht")
check({i: dict(d) for i, d in DB["links"].items()} == vorher, "Eintragen, Friedhof, Löschen, Bearbeiten: alles blockiert")
k.state["pw_eingabe_Standard_Run"] = "falsch"; k.click("entsperren_Standard_Run")
check(any("Falsches Passwort" in t for t in k.texts("error", "sidebar")) and not k.query.get("schluessel"), "Falsches Passwort wird abgelehnt")
k.state["pw_eingabe_Standard_Run"] = "pika1234"; k.click("entsperren_Standard_Run")
check(k.query.get("schluessel") and "🗑️ Run löschen" in k.texts("expander"), "Richtiges Passwort entsperrt alles")

r = neue_app(REPO); r.query.update(eigener_link); r.run()      # Neuladen / Lesezeichen
check(any("freigeschaltet" in t for t in r.texts("success", "sidebar")), "Nach Neuladen bleibt die Freigabe (Schlüssel in der Adresse)")
r.click("sperren_Standard_Run")
check(not r.query.get("schluessel") and any("Geschützter" in t for t in r.texts("warning", "sidebar")), "'Wieder sperren' funktioniert")

alt_schluessel = eigener_link["schluessel"]
k2 = neue_app(REPO); k2.query.update(k.query); k2.run()
k2.state["pw_neu1_Standard_Run"] = "neuesPW"; k2.state["pw_neu2_Standard_Run"] = "neuesPW"; k2.click("pw_speichern_Standard_Run")
x = neue_app(REPO); x.query.update({"run": "Standard_Run", "schluessel": alt_schluessel}); x.run()
check(any("Geschützter" in t for t in x.texts("warning", "sidebar")), "Nach Passwortänderung gilt ein alter Link nicht mehr")

n = neue_app(REPO); n.run(); n.set("run_auswahl", "➕ Neuen Run anlegen…")
n.state["neuer_run_name"] = "Kollegen Run"; n.state["neuer_run_pw"] = "geheim1"; n.click("btn_Run anlegen")
check(n.state["run_auswahl"] == "Kollegen Run" and n.query.get("schluessel"), "Neuer Run mit Passwort: Ersteller ist direkt freigeschaltet")
y = neue_app(REPO); y.query["run"] = "Kollegen Run"; y.run()
check(any("Geschützter" in t for t in y.texts("warning", "sidebar")), "Für alle anderen ist der neue Run gesperrt")

if ALT:
    alt2 = neue_app(ALT); alt2.run()
    check(any("Aktive Links" in t for t in alt2.texts("tabs")), "Alter Code läuft weiterhin mit den Passwort-Daten")

print("12) Team-Liste, markierte Pokémon, keine Live-Aktualisierung")
DB["links"]["L1"] = {"run_id": "Live Run", "route": "Route 1", "n1": "Jan", "p1": "Pikachu", "i1": {"bild": "https://x/25.png", "typen": ["Elektro"]}, "n2": "Max", "p2": "Evoli", "i2": {}, "status": "aktiv", "in_team": False}
DB["links"]["L2"] = {"run_id": "Live Run", "route": "Route 2", "n1": "Jan", "p1": "Hornliu", "status": "aktiv", "in_team": False}
A = neue_app(REPO); A.query["run"] = "Live Run"; A.run()
check(not any("🟢 Live" in t for t in A.texts("caption")) and A.fragment_fn is None, "Kein Live-Modus mehr (kein Fragment, kein Hinweis)")
fnA = A.state["formular_nr"]
check("⛔ Reihe von Pikachu" in A.formats[f"p_0_{fnA}"]("Raichu") and "⛔ schon gehabt" in A.formats[f"p_0_{fnA}"]("Evoli"), "Vergebene Pokémon sind in der Auswahl markiert")
check(A.formats[f"p_0_{fnA}"]("Glumanda") == "Glumanda", "Freie Pokémon stehen ganz normal da")
check("⛔" in A.formats[f"p_0_{fnA}"]("Flamara"), "Auch Evoli-Entwicklungen sind markiert")
A.set("team_L1", True)
check("teamslot_L1" in A.texts("container"), "Team-Link steckt im Party-Slot-Rahmen")
slots = [t for t in A.texts("md") if "class='teamslot'" in t]
check({"slot_L1_0", "slot_L1_1"} <= set(A.texts("container")), "Ein Slot pro Trainer (2 Spieler -> 2 Slots)")
check(len(slots) == 2 and "Jan" in slots[0] and "Pikachu" in slots[0] and "Max" in slots[1] and "Evoli" in slots[1], "Slots zeigen Trainer + Pokémon (Jan/Pikachu links, Max/Evoli rechts)")
check("border-color:#F7D02C" in slots[0] and "https://x/25.png" in slots[0], "Ring in Typ-Farbe (Elektro) mit echtem Sprite")
check(all("margin-bottom: 1rem" in css for css in [t for t in A.texts("md") if ".teamslot {" in t]), "Ausgleich gegen das Überhängen ist gesetzt")
check(any("<b>Jan:</b> Hornliu" in t for t in A.texts("md")) and "teamslot_L2" not in A.texts("container"), "PC-Box bleibt in der normalen Listenansicht")
check("⚔️ Im Team=1/6" in A.texts("metric"), "Team-Zähler stimmt")
A.set("team_L1", False)
check("⚔️ Im Team=0/6" in A.texts("metric"), "Haken weg: Link wandert zurück in die PC-Box")
check("teamslot_L1" not in A.texts("container") and any("<b>Jan:</b> Pikachu" in t for t in A.texts("md")), "…und sieht dort wieder wie eine normale Listenzeile aus")
DB["links"]["L3"] = {"run_id": "Live Run", "route": "<b>Route 9</b>", "n1": "<i>X</i>", "p1": "Mew", "status": "aktiv", "in_team": True}
A.run()
check(not any("<b>Route 9</b>" in t for t in A.texts("md") if "teamslot-route" in t), "Sonderzeichen in Route/Namen können das Layout nicht zerschießen")
del DB["links"]["L3"]
A.click("f_L2")
check(DB["links"]["L2"]["status"] == "friedhof", "Buttons in der Liste funktionieren")
A.set("team_L1", True); A.click("v_L1")
check(DB["links"]["L1"]["status"] == "verpasst" and not DB["links"]["L1"]["in_team"], "Buttons bei Team-Links funktionieren")

print("13) Gleiches Pokémon im selben Link")
DB["runs"]["Duo"] = {"run_id": "Duo", "spieler": ["Jan", "Max", ""], "anzahl_spieler": 2}
D = neue_app(REPO); D.query["run"] = "Duo"; D.run()
fn = D.state["formular_nr"]
D.set(f"p_0_{fn}", "Zubat")
check(D.formats[f"p_1_{fn}"]("Zubat") == "Zubat  ⛔ schon in diesem Link" and "⛔ schon in diesem Link" in D.formats[f"p_1_{fn}"]("Golbat"), "Auswahl von Spieler 2 markiert Zubat/Golbat als 'schon in diesem Link'")
check("⛔" not in D.formats[f"p_1_{fn}"]("Glumanda"), "Andere Pokémon bleiben frei wählbar")
D.state[f"route_{fn}"] = "Route 1"; D.state[f"p_1_{fn}"] = "Zubat"; D.click("btn_gefangen")
check(any("zweimal in diesem Link" in t for t in D.texts("error")) and not any(d["run_id"] == "Duo" for d in DB["links"].values()), "Zubat + Zubat im selben Link wird blockiert")
D.state[f"p_1_{fn}"] = "Golbat"; D.click("btn_gefangen")
check(any("dieselbe Entwicklungsreihe" in t for t in D.texts("error")), "Zubat + Golbat im selben Link wird blockiert")
D.state[f"route_{fn}"] = "Static Lapras Geschenk"; D.state[f"p_0_{fn}"] = "Lapras"; D.state[f"p_1_{fn}"] = "Lapras"; D.click("btn_gefangen")
check(any("Static Bonus" in t for t in D.texts("success")), "Mit Static ist dasselbe Geschenk-Pokémon erlaubt")
fn = D.state["formular_nr"]
D.state[f"route_{fn}"] = "Route 2"; D.state[f"p_0_{fn}"] = "Zubat"; D.state[f"p_1_{fn}"] = "Glumanda"; D.click("btn_gefangen")
check(any("Erfolgreich" in t for t in D.texts("success")), "Unterschiedliche Pokémon werden normal gespeichert")
zid = next(i for i, d in DB["links"].items() if d["run_id"] == "Duo" and d["route"] == "Route 2")
D.click(f"e_{zid}"); D.set(f"ep_{zid}_1", "Golbat"); D.click(f"submit_edit_{zid}")
check(DB["links"][zid]["p2"] == "Glumanda" and any("Entwicklungsreihe" in t for t in D.texts("error")), "Auch beim Bearbeiten wird ein Doppel im Link verhindert")
D.set(f"team_{zid}", True)
check("⚔️ Im Team=1/6" in D.texts("metric") and not any("🧢" in t for t in D.texts("md")), "Team ohne Trainer-Kopfzeile")

print("14) Drei Spieler: Buttons kompakt in der Kopfzeile")
DB["runs"]["Trio"] = {"run_id": "Trio", "spieler": ["Jan", "Max", "Tom"], "anzahl_spieler": 3}
DB["links"]["T1"] = {"run_id": "Trio", "route": "Route 1", "n1": "Jan", "p1": "Pikachu", "n2": "Max", "p2": "Evoli", "n3": "Tom", "p3": "Glumanda", "status": "aktiv", "in_team": True}
X = neue_app(REPO); X.query["run"] = "Trio"; X.run()
check({"slot_T1_0", "slot_T1_1", "slot_T1_2"} <= set(X.texts("container")), "Drei Slots nebeneinander")
check("teamaktionen_T1" in X.texts("container") and "[2, 3, 2]" in X.texts("columns"), "Aktionen mittig über den Slots (Route | Aktionen | frei)")
X.click("f_T1")
check(DB["links"]["T1"]["status"] == "friedhof", "Buttons funktionieren auch im Drei-Spieler-Layout")

print("15) Typ-Suche oben rechts")
Y = neue_app(REPO); Y.query["run"] = "Trio"; Y.run()
check(Y.state.get("typ_suche") is None and not any("Flug" in t and "<b>Habitak</b>" in t for t in Y.texts("md")), "Ohne Eingabe wird nichts angezeigt")
Y.set("typ_suche", "Habitak")
anz = [t for t in Y.texts("md") if "<b>Habitak</b>" in t]
check(len(anz) == 1 and ">Normal<" in anz[0] and ">Flug<" in anz[0], "Habitak -> Normal + Flug")
Y.set("typ_suche", "Glurak")
check(any("<b>Glurak</b>" in t and ">Feuer<" in t and ">Flug<" in t for t in Y.texts("md")), "Glurak -> Feuer + Flug")
vorher = {i: dict(d) for i, d in DB["links"].items()}; Y.set("typ_suche", "Mew")
check({i: dict(d) for i, d in DB["links"].items()} == vorher, "Die Suche ändert nichts an den Daten")

print("16) Fangchance-Rechner (Gen 3/4)")
T = sys.modules["tracker_logik"]
c, x = T.fangchance("Habitak", "poke", 100, "Kein Status", 5, "Gen 3")
check(x == 85 and abs(c - (49931 / 65536) ** 4) < 1e-12 and f"{c*100:.1f}" == "33.7", "Handrechnung Habitak Lv5, volle KP, Pokéball: X=85, 33,7 %")
check(T.fangchance("Habitak", "poke", 1, "Schlaf", 5, "Gen 3", eins_kp=True)[0] == 1.0, "X >= 255 -> garantierter Fang")
check(T.fangchance("Mewtu", "meister", 100, "Kein Status", 70, "Gen 3")[0] == 1.0, "Meisterball fängt immer")
voll, _ = T.fangchance("Mewtu", "hyper", 100, "Kein Status", 70, "Gen 4 (DPPt)")
wenig, _ = T.fangchance("Mewtu", "hyper", 1, "Schlaf", 70, "Gen 4 (DPPt)", eins_kp=True)
check(voll < wenig < 0.1, f"Mewtu: volle KP {voll*100:.2f} % < 1 KP + Schlaf {wenig*100:.2f} % (bleibt schwer)")
check(T.fangchance("Kokowei", "poke", 50, "Schlaf", 30, "Gen 3")[1] == 2 * T.fangchance("Kokowei", "poke", 50, "Kein Status", 30, "Gen 3")[1], "Schlaf verdoppelt X")
check(T.fangchance("Kokowei", "poke", 50, "Paralyse", 30, "Gen 3")[1] == (T.fangchance("Kokowei", "poke", 50, "Kein Status", 30, "Gen 3")[1] * 15) // 10, "Paralyse = x1,5 (abgerundet)")
_, xp = T.fangchance("Relaxo", "poke", 100, "Kein Status", 30, "HGSS")
check(T.fangchance("Relaxo", "netz", 100, "Kein Status", 30, "HGSS")[1] == xp, "Netzball wirkt nicht auf Normal-Typ")
_, xr = T.fangchance("Karpador", "poke", 100, "Kein Status", 10, "HGSS"); _, xn = T.fangchance("Karpador", "netz", 100, "Kein Status", 10, "HGSS")
check(xn == 3 * xr or xn >= 255, "Netzball x3 auf Wasser-Typ")
_, n5 = T.fangchance("Relaxo", "nest", 100, "Kein Status", 5, "HGSS"); _, n40 = T.fangchance("Relaxo", "nest", 100, "Kein Status", 40, "HGSS")
check(n5 > T.fangchance("Relaxo", "poke", 100, "Kein Status", 5, "HGSS")[1], "Nestball besser als Pokéball bei Lv 5")
_, t1 = T.fangchance("Relaxo", "timer", 100, "Kein Status", 30, "HGSS", runde=1); _, t31 = T.fangchance("Relaxo", "timer", 100, "Kein Status", 30, "HGSS", runde=31)
check(t1 == xp and t31 > 3.5 * xp, "Timerball: Runde 1 wie Pokéball, ab Runde 31 ~x4")
_, f1 = T.fangchance("Relaxo", "flott", 100, "Kein Status", 30, "Gen 4 (DPPt)", runde=1); _, f2 = T.fangchance("Relaxo", "flott", 100, "Kein Status", 30, "Gen 4 (DPPt)", runde=2)
check(f1 > 3.5 * xp and f2 == xp, "Flottball nur in Runde 1 stark")
_, s1 = T.fangchance("Relaxo", "schwer", 100, "Kein Status", 30, "HGSS")
check(s1 > xp, "Schwerball: Relaxo (460 kg) +40 Fangrate")
_, m1 = T.fangchance("Piepi", "mond", 100, "Kein Status", 20, "HGSS"); _, m0 = T.fangchance("Piepi", "poke", 100, "Kein Status", 20, "HGSS")
check(m1 > m0 and T.fangchance("Relaxo", "mond", 100, "Kein Status", 30, "HGSS")[1] == xp, "Mondball nur bei Mondstein-Familien")
_, l1 = T.fangchance("Relaxo", "level", 100, "Kein Status", 10, "HGSS", eigenes_level=45)
check(l1 > T.fangchance("Relaxo", "poke", 100, "Kein Status", 10, "HGSS")[1], "Levelball: eigenes Level 45 vs. 10")
check("finster" not in T.baelle_fuer("Gen 3") and "turbo" in T.baelle_fuer("HGSS") and "turbo" not in T.baelle_fuer("Gen 4 (DPPt)"), "Ballauswahl passt zum Spiel")
check(T.wuerfe_fuer(0.5) == 4 and T.wuerfe_fuer(1.0) == 1, "Würfe für 90 % Sicherheit")

F = neue_app(REPO); F.query["run"] = "Trio"; F.run()
nr = F.state["formular_nr"]
check("🎯 Fangchance" not in F.texts("expander"), "Ohne gewähltes Pokémon keine Fangchance im Eingabebereich")
F.set("spiel_Trio", "Gen 3: Rubin/Saphir"); F.set(f"p_0_{nr}", "Habitak")
check("🎯 Fangchance" in F.texts("expander") and any(">Normal<" in t and ">Flug<" in t for t in F.texts("md")), "Pokémon gewählt -> Typen + Fangchance-Aufklappmenü erscheinen")
F.set(f"fc0_level_{nr}", 5)
check(any("33,7 %" in t for t in F.texts("md")), "Fangchance im Eingabebereich: 33,7 % für Habitak Lv5 (Gen 3)")
check(f"fc0_runde_{nr}" not in F.keys_this_run, "Rundenfeld nur bei Timer-/Flottball sichtbar")
F.set("fc0_ball_Gen 3", "timer")
check(f"fc0_runde_{nr}" in F.keys_this_run, "Timerball -> Rundenfeld erscheint")
F.set("fc0_ball_Gen 3", "meister")
check(any("100,0 %" in t for t in F.texts("md")) and any("garantiert" in t for t in F.texts("caption")), "Meisterball: 100 %, garantiert")
F.set(f"p_1_{nr}", "Bisasam")
check(f"fc1_level_{nr}" in F.keys_this_run, "Jeder Spieler hat seine eigene Fangchance")
F.state[f"route_{nr}"] = "Route 77"; F.click("btn_gefangen")
check(F.state["formular_nr"] == nr + 1 and F.state.get("fc0_ball_Gen 3") == "meister" and F.state.get(f"fc0_level_{nr+1}", 10) == 10 and any("Erfolgreich" in t for t in F.texts("success")),
      "Nach dem Speichern: Ball bleibt gemerkt, Level & Co. werden zurückgesetzt")

check("traum" in T.baelle_fuer("Gen 5") and "safari" not in T.baelle_fuer("Gen 5"), "Gen 5 Ballauswahl passt")

G = neue_app(REPO); G.query["run"] = "Trio"; G.run()
G.set("spiel_Trio", "Gen 1: Rot/Blau"); nr = G.state["formular_nr"]; G.set(f"p_0_{nr}", "Habitak"); G.set(f"fc0_level_{nr}", 5)
check(any("39,5 %" in t for t in G.texts("md")), "Rechner Gen 1 zeigt 39,5 %")
G.set("spiel_Trio", "Gen 5: Schwarz/Weiß"); G.set("fc0_dex", 0)
check(any("43,9 %" in t for t in G.texts("md")) and f"fc0_gras_{nr}" in G.keys_this_run and "fc0_dex" in G.keys_this_run, "Rechner Gen 5 zeigt 43,9 % + Gras/Pokédex-Felder")
G.set("spiel_Trio", "Gen 2: Gold/Silber/Kristall"); G.set(f"fc0_status_{nr}", "Paralyse")
check(any("Spiel-Bug" in t for t in G.texts("caption")) and f"fc0_gras_{nr}" not in G.keys_this_run, "Gen 2: Hinweis auf Status-Bug, keine Gen-5-Felder")
G.set("spiel_Trio", "Gen 9: Karmesin/Purpur")
check(any("ab Gen 6" in t for t in G.texts("caption")), "Ab Gen 6: Hinweis, dass es nur eine Näherung ist")

print("19) Schwächen oben rechts")
T = sys.modules["tracker_logik"]
W = neue_app(REPO); W.query["run"] = "Trio"; W.run(); W.set("spiel_Trio", "Gen 4: Platin")
check("🎯 Fangchance" not in W.texts("expander") and "🛡️ Schwächen" in W.texts("expander"), "Oben rechts: Schwächen statt Fangchance")
W.set("typ_suche", "Habitak")
zeile = " ".join(t for t in W.texts("md") if "min-width:30px" in t)
check("<b style='min-width:30px; font-size:13px;'>2×</b>" in zeile and ">Elektro<" in zeile and "0×" in zeile and "4×" not in zeile and "¼×" not in zeile,
      "Habitak: 2× Elektro/Eis/Gestein, 0× Boden/Geist – leere Stufen (4×, ¼×) fehlen")
check(T.typen_fuer("Piepi", 4) == ["Normal"] and T.typen_fuer("Piepi", 9) == ["Fee"], "Piepi: Gen 4 Normal, Gen 9 Fee")
check("Unlicht" not in sum(T.schwaechen("Gengar", 1).values(), []) and "Fee" not in sum(T.schwaechen("Gengar", 4).values(), []), "Nur Typen, die es in der Generation gab")
check(0.5 in [w for w, ts in T.schwaechen("Magnetilo", 4).items() if "Geist" in ts] and 1.0 in [w for w, ts in T.schwaechen("Magnetilo", 9).items() if "Geist" in ts],
      "Stahl widersteht Geist bis Gen 5, ab Gen 6 nicht mehr")
check(T.schwaechen("Gengar", 1)[2.0] == ["Boden", "Geist", "Psycho"] and "Psycho" in T.schwaechen("Gengar", 4)[2.0], "Gen-1-Sonderregeln (Gengar)")
check(4.0 in T.schwaechen("Magnetilo", 4) and T.schwaechen("Magnetilo", 4)[4.0] == ["Boden"], "4×-Stufe wird erkannt (Magnetilo: Boden)")


print("18) GBC-Design umschaltbar")
DB["runs"]["Design Run"] = {"run_id": "Design Run"}
DB["links"]["DZ1"] = {"run_id": "Design Run", "route": "Route 1", "n1": "Jan", "p1": "Pikachu", "status": "aktiv", "in_team": False}
G1 = neue_app(REPO); G1.query["run"] = "Design Run"; G1.run()
gbc_an = lambda app: any("--gbc-shell" in t for t in app.texts("md"))
check(gbc_an(G1) and G1.state["design_Design Run"] is True, "Standard: GBC-Design ist an")
check("eingabebox" in G1.texts("container"), "Eingabebereich steckt in der GBC-Box")
css = [t for t in G1.texts("md") if "--gbc-shell" in t][0]
check("stTextInputRootElement" in css and "stRadioOption" in css and "z-index: 1000100" in css, "Regeln für neue Streamlit-Bausteine + Rahmen über der Seitenleiste")
check("zeile_DZ1" in G1.texts("container") and any("class='typ'" in t for t in G1.texts("md")), "Zeilen und Typ-Badges sind für das Design markiert")
G1.set("design_Design Run", False)
check(not gbc_an(G1) and DB["runs"]["Design Run"]["design"] == "klassisch", "Schalter aus -> klassisches Design, wird gespeichert")
G2 = neue_app(REPO); G2.query["run"] = "Design Run"; G2.run()
check(not gbc_an(G2), "Nach Neuladen bleibt das klassische Design")
G2.set("design_Design Run", True)
check(gbc_an(G2) and DB["runs"]["Design Run"]["design"] == "gbc", "Wieder an -> GBC")
vor = {i: dict(d) for i, d in DB["links"].items()}
G2.set("design_Design Run", False); G2.set("design_Design Run", True)
check({i: dict(d) for i, d in DB["links"].items()} == vor, "Umschalten ändert nichts an den Einträgen")
G2.click("f_DZ1")
check(DB["links"]["DZ1"]["status"] == "friedhof", "Buttons funktionieren im GBC-Design")

print("20) Layout je nach Spieleranzahl")
DB["runs"]["Lay2"] = {"run_id": "Lay2", "spieler": ["Jan", "Niklas", ""], "anzahl_spieler": 2}
L = neue_app(REPO); L.query["run"] = "Lay2"; L.run()
check("[2, 1]" in L.texts("columns") and "2" in L.texts("columns") and "[3, 1]" not in L.texts("columns"),
      "2 Spieler: Eingabe 2/3 breit, Typ-Suche/Schwächen rechts daneben, 2 Spielerspalten")
check("🛡️ Schwächen" in L.texts("expander") and "typ_suche" in L.keys_this_run, "Typ-Suche + Schwächen sind da")
L.click("btn_➕ Spieler hinzufügen")
check("[3, 1]" in L.texts("columns") and "3" in L.texts("columns") and "[2, 1]" not in L.texts("columns"),
      "3 Spieler: Typ-Suche wieder oben neben dem Titel, Eingabe volle Breite")
L.set("typ_suche", "Habitak"); L.click("btn_➖ Spieler entfernen")
check(L.state.get("typ_suche") == "Habitak" and "[2, 1]" in L.texts("columns"), "Zurück auf 2 Spieler: Suche bleibt erhalten")
nr = L.state["formular_nr"]; L.state[f"route_{nr}"] = "R1"; L.state[f"p_0_{nr}"] = "Habitak"; L.state[f"p_1_{nr}"] = "Bisasam"
L.click("btn_gefangen")
check(any("Erfolgreich" in t for t in L.texts("success")), "Speichern funktioniert im neuen Layout")

print("21) Schwächen im Team-Slot")
DB["runs"]["Schwach"] = {"run_id": "Schwach", "spieler": ["Jan", "Niklas", ""], "anzahl_spieler": 2, "spiel": "Gen 4: Platin"}
DB["links"]["SW1"] = {"run_id": "Schwach", "route": "R1", "n1": "Jan", "p1": "Magnetilo", "i1": {"typen": ["Elektro", "Stahl"]},
                      "n2": "Niklas", "p2": "Mew", "i2": {"typen": ["Psycho"]}, "status": "aktiv", "in_team": True}
Z = neue_app(REPO); Z.query["run"] = "Schwach"; Z.run()
slots = [t for t in Z.texts("md") if "class='teamslot'" in t]
check(len(slots) == 2 and "class='schwach'" in slots[0] and "stufe-4'>4×</b>" in slots[0] and ">Boden<" in slots[0]
      and "stufe-2'>2×</b>" in slots[0] and ">Kampf<" in slots[0] and ">Feuer<" in slots[0], "Magnetilo: 4× Boden, 2× Kampf/Feuer rechts im Slot")
check("stufe-4" not in slots[1] and "stufe-2'>2×</b>" in slots[1] and ">Käfer<" in slots[1] and ">Geist<" in slots[1] and ">Unlicht<" in slots[1],
      "Mew (Gen 4): nur 2×-Zeile (Käfer, Geist, Unlicht), keine leere 4×-Zeile")
check(not any("class='schwach'" in t for t in Z.texts("md") if "pc-pokes" in t), "PC-Box-Zeilen bleiben ohne Schwächen")
check("class='warn'" in slots[0] and ">!</span>" in slots[0], "Rotes Ausrufezeichen vor den Schwächen")

print("22) Zwischenspeicher: weniger Lesevorgänge, gleiches Verhalten")
fakes.CACHE_BEI_JEDEM_LAUF_LEEREN[0] = False
fakes.cache_ablaufen()
DB["runs"]["Cache"] = {"run_id": "Cache", "spieler": ["Jan", "Niklas", ""], "anzahl_spieler": 2}
for i in range(30):
    DB["links"][f"c{i}"] = {"run_id": "Cache", "route": f"C{i}", "n1": "Jan", "p1": "Mew", "status": "aktiv", "in_team": False}
A = neue_app(REPO); A.query["run"] = "Cache"; A.run()
B = neue_app(REPO); B.query["run"] = "Cache"; B.run()
vor = fakes.LESEN[0]; A.run(); A.run(); B.run()
check(fakes.LESEN[0] - vor < 5, f"Neu zeichnen ohne Änderung kostet fast nichts ({fakes.LESEN[0] - vor} statt ~90 Lesevorgänge)")
nr = A.state["formular_nr"]; A.state[f"route_{nr}"] = "Neu A"; A.state[f"p_0_{nr}"] = "Glumanda"; A.state[f"p_1_{nr}"] = "Bisasam"
A.click("btn_gefangen")
check(any("Aktive Links (31)" in t for t in A.texts("tabs")), "Eigener neuer Link erscheint sofort")
B.run()
check(any("Aktive Links (31)" in t for t in B.texts("tabs")), "Mitspieler sieht den neuen Link beim nächsten Klick")
B.click("f_c0")
A.run()
check(DB["links"]["c0"]["status"] == "friedhof" and any("Friedhof (1)" in t for t in A.texts("tabs")), "Änderung des Mitspielers erscheint bei mir")
B.set("n_Cache_0", "Jan2")
A2 = neue_app(REPO); A2.query["run"] = "Cache"; A2.run()
check(A2.state["n_Cache_0"] == "Jan2", "Geänderte Einstellungen werden sofort übernommen")
nr = B.state["formular_nr"]; B.state[f"route_{nr}"] = "Neu B"; B.state[f"p_0_{nr}"] = "Glurak"; B.state[f"p_1_{nr}"] = "Schiggy"
B.click("btn_gefangen")
check(any("Dupes" in t for t in B.texts("error")), "Dupes-Prüfung arbeitet weiter mit frischen Daten (Glurak-Reihe schon vergeben)")
fakes.CACHE_BEI_JEDEM_LAUF_LEEREN[0] = True

print("23) Static-Häkchen")
DB["runs"]["StaticRun"] = {"run_id": "StaticRun", "spieler": ["Jan", "Niklas", ""], "anzahl_spieler": 2, "spiel": "Gen 4: Platin"}
DB["links"]["ST1"] = {"run_id": "StaticRun", "route": "Route 209", "n1": "Jan", "p1": "Glumanda", "n2": "Niklas", "p2": "Schiggy", "status": "aktiv"}
Q = neue_app(REPO); Q.query["run"] = "StaticRun"; Q.run()
nr = Q.state["formular_nr"]
check(f"static_{nr}" in Q.keys_this_run, "Static-Häkchen ist im Eingabekasten")
Q.state[f"route_{nr}"] = "Route 209"; Q.state[f"p_0_{nr}"] = "Glurak"; Q.state[f"p_1_{nr}"] = "Glurak"
Q.click("btn_gefangen")
check(any("existiert bereits" in t or "Dupes" in t or "zweimal" in t for t in Q.texts("error")), "Ohne Häkchen: Prüfungen greifen")
Q.set(f"static_{nr}", True); Q.click("btn_gefangen")
neu = [d for k, d in DB["links"].items() if d["run_id"] == "StaticRun" and k != "ST1"]
check(any("Static Bonus" in t for t in Q.texts("success")) and len(neu) == 1 and neu[0].get("static") is True and neu[0]["route"] == "Route 209",
      "Mit Häkchen: gespeichert, Route bleibt 'Route 209', als Static markiert")
check(Q.state.get(f"static_{nr+1}", False) is False, "Häkchen ist beim nächsten Eintrag wieder aus")
check(any("static-tag" in t for t in Q.texts("md")), "Static-Links sind in der Liste gekennzeichnet")
DB["links"]["ST1"]["status"] = "aktiv"
del DB["links"]["ST1"]
Q.run(); nr = Q.state["formular_nr"]; Q.state[f"route_{nr}"] = "Route 209"; Q.state[f"p_0_{nr}"] = "Bisasam"; Q.state[f"p_1_{nr}"] = "Endivie"
Q.click("btn_gefangen")
check(any("Erfolgreich" in t for t in Q.texts("success")), "Ein Static-Link blockiert die Route nicht für den normalen Encounter")

print("24) Team-Schwachstellen pro Trainer")
DB["runs"]["Analyse"] = {"run_id": "Analyse", "spieler": ["Jan", "Niklas", ""], "anzahl_spieler": 2, "spiel": "Gen 4: Platin"}
for i, (a, b) in enumerate([("Magnetilo", "Glumanda"), ("Pikachu", "Ponita"), ("Kleinstein", "Fukano"), ("Bisasam", "Taubsi")]):
    DB["links"][f"AN{i}"] = {"run_id": "Analyse", "route": f"R{i}", "n1": "Jan", "p1": a, "n2": "Niklas", "p2": b, "status": "aktiv", "in_team": True}
N = neue_app(REPO); N.query["run"] = "Analyse"; N.run()
kasten = [t for t in N.texts("md") if "class='teamanalyse" in t]
check("teamanalyse" in N.texts("container") and len(kasten) == 2, "Ein Kasten pro Trainer unter dem Team")
check("Jan" in kasten[0] and ">Boden<" in kasten[0] and "<b>3/4</b>" in kasten[0], "Jan: Boden trifft 3 von 4 (Magnetilo, Pikachu, Kleinstein)")
check("Niklas" in kasten[1] and ">Wasser<" in kasten[1] and "<b>3/4</b>" in kasten[1] and ">Gestein<" in kasten[1], "Niklas: Wasser 3/4, Gestein dabei")
c_index = N.log.index(next(x for x in N.log if x[1] == "container" and x[2] == "teamanalyse"))
s_index = max(i for i, x in enumerate(N.log) if x[1] == "container" and x[2].startswith("teamslot_"))
check(c_index > s_index, "Analyse steht unter dem letzten Team-Link")
DB["links"]["AN9"] = {"run_id": "Analyse", "route": "R9", "n1": "Jan", "p1": "Mew", "status": "aktiv", "in_team": False}
for k in list(DB["links"]):
    if k.startswith("AN") and k != "AN9": DB["links"][k]["in_team"] = False
N.run()
check("teamanalyse" not in N.texts("container"), "Ohne Team keine Analyse")

print("25) Pixel-Badges & Orden-Koffer")
O = neue_app(REPO); O.query["run"] = "Analyse"; O.run()
css = [t for t in O.texts("md") if "--gbc-shell" in t][0]
check("span.typ {" in css and "Press Start 2P" in css.split("span.typ {")[1][:200], "Typen im Pixel-Look (nur GBC-Design)")
check("ordenkoffer" in O.texts("container"), "Orden-Koffer bei Platin vorhanden")
bilder = [t for t in O.texts("md") if "class='orden " in t]
check(len(bilder) == 8 and "/badges/25.png" in bilder[0] and "/badges/29.png" in bilder[2] and "/badges/32.png" in bilder[7],
      "Platin: 8 Orden in Platin-Reihenfolge (Kohle, Wald, Relikt, …, Leuchtfeuer)")
check(all("class='orden aus'" in b for b in bilder), "Noch nichts besiegt -> alle grau")
sk = "Gen_4_Platin"
O.set(f"orden_Analyse_{sk}_0", True)
check(DB["runs"]["Analyse"]["besiegt"][sk] == [0], "Orden-Haken gesetzt -> gespeichert")
check(f"cap_Analyse_{sk}_0" not in O.keys_this_run and f"cap_Analyse_{sk}_8" in O.keys_this_run and f"cap_Analyse_{sk}_12" in O.keys_this_run,
      "Liste enthält keine Arenen mehr, nur Top 4 und Champ")
check(any("class='orden an'" in t and "/badges/25.png" in t for t in O.texts("md")), "Besiegter Orden leuchtet")
O.set(f"cap_Analyse_{sk}_8", True)
check(DB["runs"]["Analyse"]["besiegt"][sk] == [0, 8], "Top-4-Haken in der Liste wird gespeichert")
O.set(f"orden_Analyse_{sk}_0", False)
check(O.state[f"orden_Analyse_{sk}_0"] is False and DB["runs"]["Analyse"]["besiegt"][sk] == [8], "Abwählen funktioniert")
check("Weitere Kämpfe abhaken" in O.texts("expander"), "Restliche Kämpfe als Aufklappmenü")
fakes.CACHE_BEI_JEDEM_LAUF_LEEREN[0] = False; fakes.cache_ablaufen(); O.run()
vor = fakes.LESEN[0]; O.set(f"orden_Analyse_{sk}_1", True)
check(fakes.LESEN[0] - vor <= 2, f"Orden abhaken kostet nur {fakes.LESEN[0] - vor} Lesevorgang (Links werden nicht neu geladen)")
fakes.CACHE_BEI_JEDEM_LAUF_LEEREN[0] = True
O.set("spiel_Analyse", "Gen 4: HeartGold/SoulSilver")
bilder = [t for t in O.texts("md") if "class='orden " in t]
check(len(bilder) == 16 and "/badges/9.png" in bilder[0] and "/badges/1.png" in bilder[8], "HGSS: Johto + Kanto (16 Orden)")
O.set("spiel_Analyse", "Gen 9: Karmesin/Purpur")
bilder = [t for t in O.texts("md") if "class='orden " in t]
check(len(bilder) == 8 and "/badges/70.png" in bilder[0] and "/badges/77.png" in bilder[7], "Karmesin/Purpur: Paldea-Orden")

print("26) Mitgeführter Zwischenspeicher: Sonderfälle")
fakes.CACHE_BEI_JEDEM_LAUF_LEEREN[0] = False; fakes.cache_ablaufen()
DB["runs"]["WT"] = {"run_id": "WT", "spieler": ["Jan", "Niklas", ""], "anzahl_spieler": 2, "spiel": "Gen 4: Platin"}
for i, (a, b) in enumerate([("Mew", "Celebi"), ("Jirachi", "Manaphy"), ("Shaymin", "Victini"), ("Arceus", "Darkrai"), ("Cresselia", "Heatran"), ("Regigigas", "Giratina"), ("Dialga", "Palkia")]):
    DB["links"][f"wt{i}"] = {"run_id": "WT", "route": f"W{i}", "n1": "Jan", "p1": a, "n2": "Niklas", "p2": b, "status": "aktiv", "in_team": i < 5}
P = neue_app(REPO); P.query["run"] = "WT"; P.run()
T = sys.modules["tracker_logik"]
vor = fakes.LESEN[0]
nr = P.state["formular_nr"]; P.state[f"route_{nr}"] = "W-neu"; P.state[f"p_0_{nr}"] = "Glumanda"; P.state[f"p_1_{nr}"] = "Schiggy"
P.click("btn_gefangen")
neu_id = next(k for k, d in DB["links"].items() if d.get("route") == "W-neu")
P.set(f"team_{neu_id}", True); P.click(f"f_wt6"); P.click("a_wt6")
check(fakes.LESEN[0] - vor == 0, "Eintragen + Team + Friedhof + Zurückholen: 0 Lesevorgänge")
check(any("Aktive Links (8)" in t for t in P.texts("tabs")) and "⚔️ Im Team=6/6" in P.texts("metric"), "Anzeige stimmt trotzdem (8 aktiv, Team 6/6)")
anzeige = sorted(d["id"] for d in T.lade_daten_cache("WT")); echt = sorted(k for k, d in DB["links"].items() if d["run_id"] == "WT")
check(anzeige == echt and all(T.lade_daten_cache("WT")[i] == dict(DB["links"][k], id=k) for i, k in enumerate(echt)),
      "Zwischenspeicher und Firebase sind Feld für Feld identisch")
P.set("team_wt5", True)
check(any("Team ist bereits voll" in t for t in P.texts("error")) and not DB["links"]["wt5"]["in_team"], "Max. 6 im Team gilt weiter (aus dem Zwischenspeicher geprüft)")
nr = P.state["formular_nr"]; P.state[f"route_{nr}"] = "W-dupe"; P.state[f"p_0_{nr}"] = "Glurak"; P.state[f"p_1_{nr}"] = "Bisasam"
P.click("btn_gefangen")
check(any("Dupes" in t for t in P.texts("error")), "Dupes-Prüfung erkennt den eben gespeicherten Link (Glumanda -> Glurak)")
P.click("dfrage_wt6"); P.click("d_wt6")
check("wt6" not in DB["links"] and "wt6" not in [d["id"] for d in T.lade_daten_cache("WT")], "Löschen wird nachgetragen")
P.click(f"e_wt5"); P.set("ep_wt5_0", "Kyogre"); P.click("submit_edit_wt5")
check(DB["links"]["wt5"]["p1"] == "Kyogre" and next(d for d in T.lade_daten_cache("WT") if d["id"] == "wt5")["p1"] == "Kyogre", "Bearbeiten wird nachgetragen")

# Schreibfehler -> Zwischenspeicher wird verworfen, nichts Falsches bleibt stehen
echtes_update = fakes.DocRef.update
def kaputt(self, data): raise Exception("Firebase nicht erreichbar")
fakes.DocRef.update = kaputt
try:
    try: T.status_aendern("wt0", "friedhof"); fehler = False
    except Exception: fehler = True
finally:
    fakes.DocRef.update = echtes_update
check(fehler and DB["links"]["wt0"]["status"] == "aktiv" and next(d for d in T.lade_daten_cache("WT") if d["id"] == "wt0")["status"] == "aktiv",
      "Schreibfehler: Anzeige zeigt weiter den echten Stand (aktiv), nicht den gescheiterten")

# Änderung von außen (Firebase-Konsole) -> nach Ablauf sichtbar
DB["links"]["wt1"]["route"] = "Von außen geändert"
check(next(d for d in T.lade_daten_cache("WT") if d["id"] == "wt1")["route"] != "Von außen geändert", "Änderung von außen: vor Ablauf noch nicht sichtbar")
T._LINK_CACHE["WT"]["zeit"] -= T.LINK_CACHE_TTL + 1
check(next(d for d in T.lade_daten_cache("WT") if d["id"] == "wt1")["route"] == "Von außen geändert", "…nach 10 Minuten wird frisch geladen")

# Rückgabe ist eine Kopie -> Anzeige-Code kann den Zwischenspeicher nicht versehentlich verändern
kopie = T.lade_daten_cache("WT"); kopie[0]["route"] = "MANIPULIERT"; kopie[0].setdefault("i1", {})
check(T.lade_daten_cache("WT")[0]["route"] != "MANIPULIERT", "Zwischenspeicher ist vor versehentlichen Änderungen geschützt")

# Zwei Spieler speichern gleichzeitig dieselbe Route -> nur einer kommt durch
import threading
ergebnisse = []
def speichere(p): ergebnisse.append(T.link_hinzufuegen("WT", "Gleichzeitig", "Jan", p, "", "", "", "", "Gefangen")[0])
faeden = [threading.Thread(target=speichere, args=(p,)) for p in ("Rayquaza", "Groudon", "Latias", "Latios")]
[f.start() for f in faeden]; [f.join() for f in faeden]
check(ergebnisse.count(True) == 1 and sum(1 for d in DB["links"].values() if d.get("route") == "Gleichzeitig") == 1,
      "Vier gleichzeitige Einträge auf dieselbe Route: genau einer wird gespeichert")

# Run löschen leert auch den Zwischenspeicher
T.run_loeschen("WT")
check("WT" not in T._LINK_CACHE and not any(d["run_id"] == "WT" for d in DB["links"].values()), "Run löschen leert Firebase und Zwischenspeicher")
fakes.CACHE_BEI_JEDEM_LAUF_LEEREN[0] = True

print("27) Seitengewicht: Auswahllisten pro Seitenaufbau")
DB["runs"]["Gewicht"] = {"run_id": "Gewicht", "spieler": ["Jan", "Niklas", ""], "anzahl_spieler": 2, "spiel": "Gen 4: Platin"}
for i in range(40):
    DB["links"][f"gw{i}"] = {"run_id": "Gewicht", "route": f"G{i}", "n1": "Jan", "p1": "Mew", "n2": "Niklas", "p2": "Mew",
                             "status": "aktiv" if i % 3 else "friedhof", "in_team": i in (1, 2, 4, 5)}
gezaehlt = {"listen": 0, "eintraege": 0}
echte_auswahl = fakes.FakeST.selectbox
def zaehlende_auswahl(self, label, options, *a, **k):
    gezaehlt["listen"] += 1; gezaehlt["eintraege"] += len(options)
    return echte_auswahl(self, label, options, *a, **k)
fakes.FakeST.selectbox = zaehlende_auswahl
try:
    GW = neue_app(REPO); GW.query["run"] = "Gewicht"; GW.run()
    gezaehlt["listen"] = gezaehlt["eintraege"] = 0
    GW.run()
finally:
    fakes.FakeST.selectbox = echte_auswahl
check(gezaehlt["eintraege"] < 6000 and gezaehlt["listen"] < 12,
      f"40 Links: nur {gezaehlt['listen']} Auswahllisten / {gezaehlt['eintraege']} Einträge pro Seitenaufbau (früher über 80.000)")

print(f"\nAlle {ok} Prüfungen bestanden.")
