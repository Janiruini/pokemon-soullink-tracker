import streamlit as st
import tracker_logik
import os

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

if 'anzahl_spieler' not in st.session_state:
    st.session_state.anzahl_spieler = 1

st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SEITENLEISTE (Sidebar) - SPIELSTAND & LEVEL CAPS
# ==========================================
st.sidebar.title("💾 Spielstand")
aktueller_run = st.sidebar.text_input("Name des Runs:", value="Standard_Run")

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
gewaehlte_gen = st.sidebar.selectbox("Wähle dein Spiel:", list(LEVEL_CAPS.keys()))

for cap in LEVEL_CAPS[gewaehlte_gen]:
    if cap.startswith("--") or cap.startswith("Hinweis"):
        st.sidebar.markdown(f"*{cap}*")
    else:
        st.sidebar.markdown(f"**{cap}**")

# ==========================================
# 3. EINGABE-BEREICH
# ==========================================
st.title(f"🔥 Pokémon Soul-Link Tracker")
st.caption(f"Aktueller Spielstand: **{aktueller_run}**")

col1, col2 = st.columns([1, 1])
with col1:
    route_input = st.text_input("📍 Route", placeholder="z.B. Route 1")
with col2:
    status_input = st.radio("Status:", ["Gefangen", "Verpasst"], horizontal=True)

spieler_cols = st.columns(3)

p_names = ["", "", ""]
p_pokes = ["", "", ""]

for i in range(st.session_state.anzahl_spieler):
    with spieler_cols[i]:
        p_names[i] = st.text_input(f"Name Spieler {i+1}", key=f"n_{i}")
        p_pokes[i] = st.text_input(f"Pokémon", key=f"p_{i}")

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    if st.session_state.anzahl_spieler < 3:
        if st.button("➕ Spieler hinzufügen"):
            st.session_state.anzahl_spieler += 1
            st.rerun()

with col_btn2:
    if st.button("💾 Link speichern", type="primary"):
        if not route_input or not p_pokes[0]:
            st.warning("Bitte mindestens eine Route und ein Pokémon eingeben!")
        else:
            with st.spinner('Prüfe Datenbank...'):
                erfolg, nachricht = tracker_logik.link_hinzufuegen(
                    aktueller_run, route_input, p_names[0], p_pokes[0], p_names[1], p_pokes[1], p_names[2], p_pokes[2], status_input
                )
                if erfolg:
                    st.success(nachricht)
                    st.rerun()
                else:
                    st.error(nachricht)

st.divider()

# ==========================================
# 4. KOMPAKTE LISTEN-ZEICHNUNG
# ==========================================
def zeichne_zeile(eintrag, zeige_checkbox=False):
    link_id = eintrag["id"]
    status = eintrag.get("status", "aktiv")
    
    with st.container(border=True):
        top_cols = st.columns([4, 2, 1, 1, 1])
        with top_cols[0]:
            st.markdown(f"**📍 {eintrag.get('route', '')}**")
        with top_cols[1]:
            if zeige_checkbox:
                in_team = eintrag.get("in_team", False)
                neu_in_team = st.checkbox("Im Team", value=in_team, key=f"team_{link_id}")
                if neu_in_team != in_team:
                    erfolg, msg = tracker_logik.team_status_aendern(aktueller_run, link_id, neu_in_team)
                    if not erfolg: st.session_state.team_fehler = msg
                    st.rerun()
        with top_cols[2]:
            if status == "aktiv":
                if st.button("🏃", key=f"v_{link_id}", help="Verpasst"): tracker_logik.status_aendern(link_id, "verpasst"); st.rerun()
            else:
                if st.button("♻️", key=f"a_{link_id}", help="Aktiv"): tracker_logik.status_aendern(link_id, "aktiv"); st.rerun()
        with top_cols[3]:
            if status != "friedhof":
                if st.button("💀", key=f"f_{link_id}", help="Friedhof"): tracker_logik.status_aendern(link_id, "friedhof"); st.rerun()
            else:
                if st.button("🏃", key=f"v2_{link_id}", help="Verpasst"): tracker_logik.status_aendern(link_id, "verpasst"); st.rerun()
        with top_cols[4]:
            if st.button("🗑️", key=f"d_{link_id}", help="Löschen"): tracker_logik.link_loeschen(link_id); st.rerun()

        karten_cols = st.columns(3)
        for idx, (p_key, n_key, i_key) in enumerate([('p1', 'n1', 'i1'), ('p2', 'n2', 'i2'), ('p3', 'n3', 'i3')]):
            pokemon_name = eintrag.get(p_key)
            if pokemon_name:
                infos = eintrag.get(i_key, {})
                spieler_name = eintrag.get(n_key, f"S{idx+1}")
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
# 5. TABS ZEICHNEN
# ==========================================
daten = tracker_logik.lade_daten(aktueller_run)

tab_aktiv, tab_friedhof, tab_verpasst = st.tabs(["🟢 Aktive Links", "💀 Friedhof", "🏃 Verpasste Encounter"])

with tab_aktiv:
    if "team_fehler" in st.session_state:
        st.error(st.session_state.team_fehler)
        del st.session_state.team_fehler
        
    team_links = [e for e in daten if e.get("status") == "aktiv" and e.get("in_team", False)]
    box_links = [e for e in daten if e.get("status") == "aktiv" and not e.get("in_team", False)]
    
    st.markdown(f"**⚔️ Aktives Team ({len(team_links)}/6)**")
    for e in team_links:
        zeichne_zeile(e, zeige_checkbox=True)
        
    st.divider()
    
    st.markdown(f"**📦 PC Box ({len(box_links)})**")
    for e in box_links:
        zeichne_zeile(e, zeige_checkbox=True)

with tab_friedhof:
    for e in daten:
        if e.get("status") == "friedhof": 
            zeichne_zeile(e, zeige_checkbox=False)

with tab_verpasst:
    for e in daten:
        if e.get("status") == "verpasst": 
            zeichne_zeile(e, zeige_checkbox=False)
