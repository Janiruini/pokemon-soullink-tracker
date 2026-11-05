import streamlit as st
import tracker_logik
import os
import re
import importlib

# Streamlit lädt nach einem Update manchmal nur web_app.py neu, aber nicht tracker_logik.py.
# Passt die Version nicht, wird die Logik-Datei hier frisch geladen.
ERWARTETE_LOGIK_VERSION = 2
if getattr(tracker_logik, "MODUL_VERSION", 0) != ERWARTETE_LOGIK_VERSION:
    tracker_logik = importlib.reload(tracker_logik)

# ==========================================
# 1. SEITEN-KONFIGURATION & STATUS
# ==========================================
st.set_page_config(page_title="Pokémon Soul-Link", page_icon="🎮", layout="wide")

TYP_FARBEN = {
    "Normal": "#A8A77A", "Feuer": "#EE8130", "Wasser": "#6390F0", "Elektro": "#F7D02C",
    "Pflanze": "#7AC74C", "Eis": "#96D9D6", "Kampf": "#C22E28", "Gift": "#A33EA1",
    "Boden": "#E2BF65", "Flug": "#A98FF3", "Psycho": "#F95587", "Käfer": "#A6B91A",
    "Gestein": "#B6A136", "Geist": "#735797", "Drache": "#6F35FC", "Unlicht": "#705848",
    "Stahl": "#B7B7CE", "Fee": "#D685AD", "Unbekannt": "#68A090"
}

POKEMON_NAMEN = tracker_logik.alle_pokemon_namen()

st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner=False)
def runs_laden():
    return tracker_logik.lade_runs()


def melde(art, text):
    """Merkt sich eine Meldung, damit sie nach dem Neuladen noch sichtbar ist."""
    st.session_state.meldung = (art, text)


# ==========================================
# 2. SEITENLEISTE (Sidebar) - SPIELSTAND & LEVEL CAPS
# ==========================================
st.sidebar.title("💾 Spielstand")

NEUER_RUN = "➕ Neuen Run anlegen…"
alle_runs = list(runs_laden())
if st.session_state.pop("run_geloescht", None):
    # Nach dem Löschen eines Runs: Auswahl zurücksetzen, damit ein anderer Run gewählt wird
    st.session_state.pop("run_auswahl", None)
    st.session_state.pop("letzter_run", None)
    st.session_state.pop("geladener_run", None)
    if "run" in st.query_params:
        del st.query_params["run"]

url_run = st.query_params.get("run")

if "run_wunsch" in st.session_state:
    url_run = st.session_state.pop("run_wunsch")
    st.session_state.run_auswahl = url_run

if url_run and url_run not in alle_runs:
    alle_runs.append(url_run)
if not alle_runs:
    alle_runs = ["Standard_Run"]

if st.session_state.get("run_auswahl") not in alle_runs + [NEUER_RUN]:
    if url_run:
        st.session_state.run_auswahl = url_run
    elif "Standard_Run" in alle_runs:
        st.session_state.run_auswahl = "Standard_Run"
    else:
        st.session_state.run_auswahl = alle_runs[0]

auswahl = st.sidebar.selectbox("Run:", alle_runs + [NEUER_RUN], key="run_auswahl")

if auswahl == NEUER_RUN:
    neuer_name = st.sidebar.text_input("Name des neuen Runs:", key="neuer_run_name")
    if st.sidebar.button("Run anlegen", type="primary"):
        name = (neuer_name or "").strip()
        if not name:
            st.sidebar.warning("Bitte einen Namen eingeben.")
        elif name.lower() in [r.lower() for r in alle_runs]:
            st.sidebar.warning("Diesen Run gibt es schon – wähle ihn oben in der Liste aus.")
        else:
            tracker_logik.speichere_run_einstellungen(name, anzahl_spieler=1)
            runs_laden.clear()
            st.session_state.run_wunsch = name
            st.rerun()
    aktueller_run = st.session_state.get("letzter_run", alle_runs[0])
else:
    aktueller_run = auswahl
    st.session_state.letzter_run = auswahl
    if st.query_params.get("run") != auswahl:
        st.query_params["run"] = auswahl

# Einstellungen des Runs (Spielernamen, Spiel, besiegte Arenen) einmal laden
if st.session_state.get("geladener_run") != aktueller_run:
    st.session_state.einst = tracker_logik.lade_run_einstellungen(aktueller_run)
    st.session_state.geladener_run = aktueller_run
einst = st.session_state.einst

daten = tracker_logik.lade_daten(aktueller_run)

if auswahl != NEUER_RUN:
    with st.sidebar.expander("🗑️ Run löschen"):
        st.markdown(f"Löscht **{aktueller_run}** komplett: alle **{len(daten)} {'Link' if len(daten) == 1 else 'Links'}** "
                    f"(auch Friedhof & Verpasst) und die gespeicherten Einstellungen. Andere Runs bleiben erhalten.")
        bestaetigung = st.text_input("Zum Bestätigen den Run-Namen eintippen:", key=f"loesch_bestaetigung_{aktueller_run}")
        if st.button("Run endgültig löschen", type="primary", key=f"run_loeschen_{aktueller_run}",
                     disabled=bestaetigung.strip() != aktueller_run):
            erfolg, anzahl = tracker_logik.run_loeschen(aktueller_run)
            runs_laden.clear()
            if erfolg:
                melde("success", f"Run '{aktueller_run}' mit {anzahl} {'Link' if anzahl == 1 else 'Links'} gelöscht.")
            else:
                melde("error", f"Beim Löschen ist ein Fehler aufgetreten ({anzahl} Links wurden gelöscht). Bitte nochmal versuchen.")
            st.session_state.run_geloescht = True
            st.rerun()

st.sidebar.markdown("---")

LEVEL_CAPS = {
    "Gen 1: Rot/Blau": [
        "1. Arena: Lv 14", "2. Arena: Lv 21", "3. Arena: Lv 24", "4. Arena: Lv 29",
        "5. Arena: Lv 43", "6. Arena: Lv 43", "7. Arena: Lv 47", "8. Arena: Lv 50",
        "Top 4 (1): Lv 56", "Top 4 (2): Lv 58", "Top 4 (3): Lv 60", "Top 4 (4): Lv 62", "Champ: Lv 65"
    ],
    "Gen 1: Gelb": [
        "1. Arena: Lv 12", "2. Arena: Lv 21", "3. Arena: Lv 28", "4. Arena: Lv 32",
        "5. Arena: Lv 50", "6. Arena: Lv 50", "7. Arena: Lv 54", "8. Arena: Lv 55",
        "Top 4 (1): Lv 56", "Top 4 (2): Lv 58", "Top 4 (3): Lv 60", "Top 4 (4): Lv 62", "Champ: Lv 65"
    ],
    "Gen 2: Gold/Silber/Kristall": [
        "1. Arena: Lv 9", "2. Arena: Lv 16", "3. Arena: Lv 20", "4. Arena: Lv 25",
        "5. Arena: Lv 30", "6. Arena: Lv 35", "7. Arena: Lv 31 (niedriger als Arena 6!)", "8. Arena: Lv 40",
        "Top 4 (1): Lv 42", "Top 4 (2): Lv 44", "Top 4 (3): Lv 46", "Top 4 (4): Lv 47", "Champ: Lv 50",
        "-- Kanto Region --",
        "Marmoria Arena: Lv 44", "Azuria Arena: Lv 47", "Orania Arena: Lv 45", "Prismania Arena: Lv 46",
        "Fuchsania Arena: Lv 39", "Saffronia Arena: Lv 48", "Seeschauminseln: Lv 50", "Vertania Arena: Lv 58",
        "Rot: Lv 81"
    ],
    "Gen 3: Rubin/Saphir": [
        "1. Arena: Lv 15", "2. Arena: Lv 18", "3. Arena: Lv 23", "4. Arena: Lv 28",
        "5. Arena: Lv 31", "6. Arena: Lv 33", "7. Arena: Lv 42", "8. Arena: Lv 43",
        "Top 4 (1): Lv 49", "Top 4 (2): Lv 51", "Top 4 (3): Lv 53", "Top 4 (4): Lv 55", "Champ: Lv 58"
    ],
    "Gen 3: Smaragd": [
        "1. Arena: Lv 15", "2. Arena: Lv 19", "3. Arena: Lv 24", "4. Arena: Lv 29",
        "5. Arena: Lv 31", "6. Arena: Lv 33", "7. Arena: Lv 42", "8. Arena: Lv 46",
        "Top 4 (1): Lv 49", "Top 4 (2): Lv 51", "Top 4 (3): Lv 53", "Top 4 (4): Lv 55", "Champ: Lv 58",
        "Meteoritenfälle (Troy): Lv 78"
    ],
    "Gen 3: Feuerrot/Blattgrün": [
        "1. Arena: Lv 14", "2. Arena: Lv 21", "3. Arena: Lv 24", "4. Arena: Lv 29",
        "5. Arena: Lv 43", "6. Arena: Lv 43", "7. Arena: Lv 47", "8. Arena: Lv 50",
        "Top 4 (1): Lv 54", "Top 4 (2): Lv 56", "Top 4 (3): Lv 58", "Top 4 (4): Lv 60", "Champ: Lv 63"
    ],
    "Gen 4: Diamant/Perl": [
        "1. Arena: Lv 14", "2. Arena: Lv 22", "3. Arena: Lv 30", "4. Arena: Lv 30",
        "5. Arena: Lv 36", "6. Arena: Lv 39", "7. Arena: Lv 42", "8. Arena: Lv 49",
        "Top 4 (1): Lv 57", "Top 4 (2): Lv 59", "Top 4 (3): Lv 61", "Top 4 (4): Lv 63", "Champ: Lv 66"
    ],
    "Gen 4: Platin": [
        "1. Arena: Lv 14", "2. Arena: Lv 22", "3. Arena: Lv 26", "4. Arena: Lv 32",
        "5. Arena: Lv 37", "6. Arena: Lv 41", "7. Arena: Lv 44", "8. Arena: Lv 50",
        "Top 4 (1): Lv 53", "Top 4 (2): Lv 55", "Top 4 (3): Lv 57", "Top 4 (4): Lv 59", "Champ: Lv 62"
    ],
    "Gen 4: HeartGold/SoulSilver": [
        "1. Arena: Lv 13", "2. Arena: Lv 17", "3. Arena: Lv 19", "4. Arena: Lv 25",
        "5. Arena: Lv 31", "6. Arena: Lv 35", "7. Arena: Lv 34", "8. Arena: Lv 41",
        "Top 4 (1): Lv 42", "Top 4 (2): Lv 44", "Top 4 (3): Lv 46", "Top 4 (4): Lv 47", "Champ: Lv 50",
        "-- Kanto Region --",
        "Marmoria Arena: Lv 54", "Azuria Arena: Lv 54", "Orania Arena: Lv 53", "Prismania Arena: Lv 56",
        "Fuchsania Arena: Lv 50", "Saffronia Arena: Lv 55", "Seeschauminseln: Lv 59", "Vertania Arena: Lv 60",
        "Rot: Lv 88"
    ],
    "Gen 5: Schwarz/Weiß": [
        "1. Arena: Lv 14", "2. Arena: Lv 20", "3. Arena: Lv 23", "4. Arena: Lv 27",
        "5. Arena: Lv 31", "6. Arena: Lv 35", "7. Arena: Lv 39", "8. Arena: Lv 43",
        "Pokémon Liga: Lv 50", "N (Plasma Schloss): Lv 52", "G-Cis (Plasma Schloss): Lv 54",
        "Top 4 Rematch: Lv 73", "Champ: Lv 77", "Cynthia (Ondula): Lv 77"
    ],
    "Gen 5: Schwarz 2/Weiß 2": [
        "1. Arena: Lv 13", "2. Arena: Lv 18", "3. Arena: Lv 24", "4. Arena: Lv 30",
        "5. Arena: Lv 33", "6. Arena: Lv 39", "7. Arena: Lv 48", "8. Arena: Lv 51",
        "Pokémon Liga: Lv 58", "Champ: Lv 59",
        "Top 4 Rematch: Lv 74", "Champ Rematch: Lv 78"
    ],
    "Gen 6: X/Y": [
        "1. Arena: Lv 12", "2. Arena: Lv 25", "3. Arena: Lv 32", "4. Arena: Lv 34",
        "5. Arena: Lv 37", "6. Arena: Lv 42", "7. Arena: Lv 48", "8. Arena: Lv 59",
        "Top 4: Lv 65", "Champ: Lv 68", "Top 4 Rematch: Lv 74", "Champ Rematch: Lv 78"
    ],
    "Gen 6: Omega Rubin/Alpha Saphir": [
        "1. Arena: Lv 14", "2. Arena: Lv 16", "3. Arena: Lv 21", "4. Arena: Lv 28",
        "5. Arena: Lv 30", "6. Arena: Lv 35", "7. Arena: Lv 45", "8. Arena: Lv 46",
        "Top 4 (1): Lv 52", "Top 4 (2): Lv 53", "Top 4 (3): Lv 54", "Top 4 (4): Lv 55", "Champ: Lv 59",
        "Top 4 (1) Rematch: Lv 72", "Top 4 (2) Rematch: Lv 73", "Top 4 (3) Rematch: Lv 74", "Top 4 (4) Rematch: Lv 75",
        "Champ Rematch: Lv 79"
    ],
    "Gen 7: Sonne/Mond": [
        "Hinweis: Sonne und Mond haben eine abweichende",
        "Struktur (Insel-Prüfungen statt Arenen).",
        "Bitte richte dich hier am besten nach den",
        "Inselkönigen (Grand Trials) oder den Werten",
        "von Ultra Sonne/Ultra Mond."
    ],
    "Gen 7: Ultra Sonne/Ultra Mond": [
        "Lehrerin Emily: Lv 10", "Elima: Lv 12", "Hala: Lv 16", "Tracy: Lv 20",
        "Kiawe: Lv 22", "Maho: Lv 24", "Mayla: Lv 28", "Chrys: Lv 33",
        "Yasu: Lv 35", "Lola: Lv 44", "Poni Canyon: Lv 49", "Ultra-Necrozma: Lv 60",
        "Matsurika: Lv 55", "Hapu'u: Lv 54", "Top 4: Lv 57", "Champ: Lv 60"
    ],
    "Gen 8: Schwert/Schild": [
        "1. Arena: Lv 20", "2. Arena: Lv 24", "3. Arena: Lv 27", "4. Arena: Lv 36",
        "5. Arena: Lv 38", "6. Arena: Lv 42", "7. Arena: Lv 46", "8. Arena: Lv 48",
        "Mary: Lv 49", "Hop: Lv 49", "Betys: Lv 53", "Kate: Lv 53",
        "Saida/Nio: Lv 54", "Roy: Lv 55", "Champ Delion: Lv 65"
    ],
    "Gen 9: Karmesin/Purpur": [
        "-- Der Weg des Champs --",
        "Käfer-Arena: Lv 15", "Pflanzen-Arena: Lv 17", "Elektro-Arena: Lv 24",
        "Wasser-Arena: Lv 30", "Normal-Arena: Lv 36", "Geist-Arena: Lv 42",
        "Psycho-Arena: Lv 45", "Eis-Arena: Lv 48", "Letztes Top 4 Mitglied: Lv 61",
        "Champ (Sagaria): Lv 62", "Nemila: Lv 66"
    ]
}

st.sidebar.title("📈 Level Caps")
spiele = list(LEVEL_CAPS.keys())
spiel_key = f"spiel_{aktueller_run}"
if spiel_key not in st.session_state:
    st.session_state[spiel_key] = einst.get("spiel") if einst.get("spiel") in spiele else spiele[0]


def spiel_gewechselt(run, key):
    einst["spiel"] = st.session_state[key]
    tracker_logik.speichere_run_einstellungen(run, spiel=st.session_state[key])


gewaehlte_gen = st.sidebar.selectbox("Wähle dein Spiel:", spiele, key=spiel_key,
                                     on_change=spiel_gewechselt, args=(aktueller_run, spiel_key))

spiel_schluessel = tracker_logik.schluessel(gewaehlte_gen)
besiegt = set(einst["besiegt"].get(spiel_schluessel, []))
caps = LEVEL_CAPS[gewaehlte_gen]


def ist_cap(text):
    return re.search(r"Lv \d+", text) is not None and not text.startswith("--")


naechster_cap = next((c for i, c in enumerate(caps) if ist_cap(c) and i not in besiegt), None)
hat_caps = any(ist_cap(c) for c in caps)

if naechster_cap:
    st.sidebar.success(f"🎯 Nächster Cap: **{naechster_cap}**")
elif hat_caps:
    st.sidebar.success("🏆 Alle Caps geschafft!")
if hat_caps:
    st.sidebar.caption("Hake besiegte Kämpfe ab – das wird pro Run gespeichert.")


def cap_umschalten(run, sk, idx, key):
    liste = set(einst["besiegt"].get(sk, []))
    if st.session_state[key]:
        liste.add(idx)
    else:
        liste.discard(idx)
    einst["besiegt"][sk] = sorted(liste)
    tracker_logik.speichere_run_einstellungen(run, besiegt={sk: sorted(liste)})


for idx, cap in enumerate(caps):
    if ist_cap(cap):
        key = f"cap_{aktueller_run}_{spiel_schluessel}_{idx}"
        st.sidebar.checkbox(f"**{cap}**", value=idx in besiegt, key=key,
                            on_change=cap_umschalten, args=(aktueller_run, spiel_schluessel, idx, key))
    else:
        st.sidebar.markdown(f"*{cap}*")

# ==========================================
# 3. EINGABE-BEREICH
# ==========================================
st.title(f"🔥 Pokémon Soul-Link Tracker")
cap_hinweis = f" · 🎯 Nächster Level-Cap: **{naechster_cap}**" if naechster_cap else ""
st.caption(f"Aktueller Spielstand: **{aktueller_run}**{cap_hinweis}")

formular_nr = st.session_state.setdefault("formular_nr", 0)

col1, col2 = st.columns([1, 1])
with col1:
    route_input = st.text_input("📍 Route", placeholder="z.B. Route 1", key=f"route_{formular_nr}")
with col2:
    status_input = st.radio("Status:", ["Gefangen", "Verpasst"], horizontal=True)

anzahl_key = f"anzahl_{aktueller_run}"
if anzahl_key not in st.session_state:
    st.session_state[anzahl_key] = einst["anzahl_spieler"]
anzahl_spieler = st.session_state[anzahl_key]


def name_geaendert(run, i, key):
    einst["spieler"][i] = st.session_state[key]
    tracker_logik.speichere_run_einstellungen(run, spieler=list(einst["spieler"]))


spieler_cols = st.columns(3)

p_names = ["", "", ""]
p_pokes = ["", "", ""]

for i in range(anzahl_spieler):
    with spieler_cols[i]:
        name_key = f"n_{aktueller_run}_{i}"
        p_names[i] = st.text_input(f"Name Spieler {i+1}", value=einst["spieler"][i], key=name_key,
                                   on_change=name_geaendert, args=(aktueller_run, i, name_key))
        p_pokes[i] = st.selectbox("Pokémon", POKEMON_NAMEN, index=None,
                                  placeholder="Tippen zum Suchen…", key=f"p_{i}_{formular_nr}") or ""


def spieleranzahl_setzen(neu):
    st.session_state[anzahl_key] = neu
    einst["anzahl_spieler"] = neu
    tracker_logik.speichere_run_einstellungen(aktueller_run, anzahl_spieler=neu)


col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])
with col_btn1:
    if anzahl_spieler < 3:
        if st.button("➕ Spieler hinzufügen"):
            spieleranzahl_setzen(anzahl_spieler + 1)
            st.rerun()
with col_btn2:
    if anzahl_spieler > 1:
        if st.button("➖ Spieler entfernen"):
            spieleranzahl_setzen(anzahl_spieler - 1)
            st.rerun()

with col_btn3:
    if st.button("💾 Link speichern", type="primary"):
        if not route_input or not p_pokes[0]:
            st.warning("Bitte mindestens eine Route und ein Pokémon eingeben!")
        else:
            with st.spinner('Prüfe Datenbank...'):
                erfolg, nachricht = tracker_logik.link_hinzufuegen(
                    aktueller_run, route_input, p_names[0], p_pokes[0], p_names[1], p_pokes[1], p_names[2], p_pokes[2], status_input
                )
            if erfolg:
                melde("success", nachricht)
                st.session_state.formular_nr = formular_nr + 1  # leert Route & Pokémon-Felder
                st.rerun()
            else:
                st.error(nachricht)

if "meldung" in st.session_state:
    art, text = st.session_state.pop("meldung")
    getattr(st, art)(text)

st.divider()

# ==========================================
# 4. KOMPAKTE LISTEN-ZEICHNUNG
# ==========================================
def bearbeiten_formular(eintrag):
    link_id = eintrag["id"]
    with st.form(key=f"edit_{link_id}"):
        st.markdown("**Link bearbeiten**")
        neue_route = st.text_input("📍 Route", value=eintrag.get("route", ""), key=f"er_{link_id}")
        namen, pokes = [], []
        for idx in range(3):
            alt_p = eintrag.get(f"p{idx+1}") or ""
            alt_n = eintrag.get(f"n{idx+1}") or ""
            if not alt_p:
                namen.append(alt_n)
                pokes.append("")
                continue
            treffer = tracker_logik.finde_pokemon(alt_p)
            optionen = list(POKEMON_NAMEN)
            if treffer:
                start = optionen.index(treffer["name"])
            else:
                optionen = [alt_p] + optionen
                start = 0
            namen.append(st.text_input(f"Name Spieler {idx+1}", value=alt_n, key=f"en_{link_id}_{idx}"))
            pokes.append(st.selectbox("Pokémon", optionen, index=start, key=f"ep_{link_id}_{idx}"))
        if st.form_submit_button("💾 Änderung speichern", type="primary"):
            erfolg, nachricht = tracker_logik.link_bearbeiten(link_id, eintrag, neue_route, namen, pokes)
            melde("success" if erfolg else "error", nachricht)
            st.rerun()


def team_umschalten(run, link_id, key):
    erfolg, msg = tracker_logik.team_status_aendern(run, link_id, st.session_state[key])
    if not erfolg:
        st.session_state.team_fehler = msg


def zeichne_zeile(eintrag, zeige_checkbox=False):
    link_id = eintrag["id"]
    status = eintrag.get("status", "aktiv")

    with st.container(border=True):
        top_cols = st.columns([4, 2, 1, 1, 1, 1])
        with top_cols[0]:
            st.markdown(f"**📍 {eintrag.get('route', '')}**")
        with top_cols[1]:
            if zeige_checkbox:
                team_key = f"team_{link_id}"
                st.session_state[team_key] = bool(eintrag.get("in_team", False))
                st.checkbox("Im Team", key=team_key, on_change=team_umschalten, args=(aktueller_run, link_id, team_key))
        with top_cols[2]:
            with st.popover("✏️", help="Bearbeiten (z.B. nach einer Entwicklung)"):
                bearbeiten_formular(eintrag)
        with top_cols[3]:
            if status == "aktiv":
                if st.button("🏃", key=f"v_{link_id}", help="Verpasst"): tracker_logik.status_aendern(link_id, "verpasst"); st.rerun()
            else:
                if st.button("♻️", key=f"a_{link_id}", help="Aktiv"): tracker_logik.status_aendern(link_id, "aktiv"); st.rerun()
        with top_cols[4]:
            if status != "friedhof":
                if st.button("💀", key=f"f_{link_id}", help="Friedhof"): tracker_logik.status_aendern(link_id, "friedhof"); st.rerun()
            else:
                if st.button("🏃", key=f"v2_{link_id}", help="Verpasst"): tracker_logik.status_aendern(link_id, "verpasst"); st.rerun()
        with top_cols[5]:
            with st.popover("🗑️", help="Löschen"):
                st.markdown(f"**{eintrag.get('route', '')}** wirklich endgültig löschen?")
                st.caption("Das kann nicht rückgängig gemacht werden.")
                if st.button("Ja, löschen", key=f"d_{link_id}", type="primary"):
                    tracker_logik.link_loeschen(link_id)
                    melde("success", f"Link '{eintrag.get('route', '')}' gelöscht.")
                    st.rerun()

        karten_cols = st.columns(3)
        for idx, (p_key, n_key, i_key) in enumerate([('p1', 'n1', 'i1'), ('p2', 'n2', 'i2'), ('p3', 'n3', 'i3')]):
            pokemon_name = eintrag.get(p_key)
            if pokemon_name:
                infos = eintrag.get(i_key, {})
                spieler_name = eintrag.get(n_key) or f"S{idx+1}"
                with karten_cols[idx]:
                    sub_col1, sub_col2 = st.columns([1, 4])
                    with sub_col1:
                        bild_pfad = infos.get("bild") if infos else None
                        if bild_pfad:
                            st.image(bild_pfad, width=45)
                        else:
                            st.markdown("<h4>❓</h4>", unsafe_allow_html=True)
                    with sub_col2:
                        st.markdown(f"<div style='line-height: 1.1; margin-bottom: 2px;'><b>{spieler_name}:</b> {pokemon_name}</div>", unsafe_allow_html=True)
                        typen = infos.get("typen", ["Unbekannt"]) if infos else ["Unbekannt"]
                        badges_html = ""
                        for typ in typen:
                            farbe = TYP_FARBEN.get(typ, "#68A090")
                            badges_html += f"<span style='background-color:{farbe}; color:white; padding:1px 5px; border-radius:3px; font-size:11px; margin-right:3px;'>{typ}</span>"
                        st.markdown(badges_html, unsafe_allow_html=True)

# ==========================================
# 5. ÜBERSICHT & TABS ZEICHNEN
# ==========================================
aktive =[e for e in daten if e.get("status") == "aktiv"]
team_links = [e for e in aktive if e.get("in_team", False)]
box_links = [e for e in aktive if not e.get("in_team", False)]
friedhof_links = [e for e in daten if e.get("status") == "friedhof"]
verpasst_links = [e for e in daten if e.get("status") == "verpasst"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("🟢 Lebende Links", len(aktive))
m2.metric("⚔️ Im Team", f"{len(team_links)}/6")
m3.metric("💀 Friedhof", len(friedhof_links))
m4.metric("🏃 Verpasst", len(verpasst_links))

tab_aktiv, tab_friedhof, tab_verpasst = st.tabs([
    f"🟢 Aktive Links ({len(aktive)})",
    f"💀 Friedhof ({len(friedhof_links)})",
    f"🏃 Verpasste Encounter ({len(verpasst_links)})",
])

with tab_aktiv:
    if "team_fehler" in st.session_state:
        st.error(st.session_state.team_fehler)
        del st.session_state.team_fehler

    st.markdown(f"**⚔️ Aktives Team ({len(team_links)}/6)**")
    for e in team_links:
        zeichne_zeile(e, zeige_checkbox=True)

    st.divider()

    st.markdown(f"**📦 PC Box ({len(box_links)})**")
    for e in box_links:
        zeichne_zeile(e, zeige_checkbox=True)

with tab_friedhof:
    for e in friedhof_links:
        zeichne_zeile(e, zeige_checkbox=False)

with tab_verpasst:
    for e in verpasst_links:
        zeichne_zeile(e, zeige_checkbox=False)
