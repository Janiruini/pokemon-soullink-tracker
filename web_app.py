import streamlit as st
import tracker_logik
import os
import re
import importlib
import html

# Streamlit lädt nach einem Update manchmal nur web_app.py neu, aber nicht tracker_logik.py.
# Passt die Version nicht, wird die Logik-Datei hier frisch geladen.
ERWARTETE_LOGIK_VERSION = 15
if getattr(tracker_logik, "MODUL_VERSION", 0) != ERWARTETE_LOGIK_VERSION:
    tracker_logik = importlib.reload(tracker_logik)

# ==========================================
# 1. SEITEN-KONFIGURATION & STATUS
# ==========================================
st.set_page_config(page_title="Pokémon Soul-Link", page_icon="🎮", layout="wide")

TYPEN_REIHENFOLGE = ["Normal", "Kampf", "Flug", "Gift", "Boden", "Gestein", "Käfer", "Geist", "Stahl",
                     "Feuer", "Wasser", "Pflanze", "Elektro", "Psycho", "Eis", "Drache", "Unlicht", "Fee"]

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

    /* Routen-Kopf im Eingabekasten: Titel links, Static-Häkchen rechts */
    .feld-titel { font-size: 14px; margin-bottom: 1rem; }
    [class*="st-key-static_"] { display: flex; justify-content: flex-end; }
    .static-tag { font-size: 0.75em; opacity: 0.8; border: 1px solid currentColor; border-radius: 3px; padding: 0 4px; margin-left: 4px; }

    /* Team-Schwachstellen unter dem letzten Team-Link (bündig mit den Slots) */
    .st-key-teamanalyse { padding: 0 12px; border: 1px solid transparent; }
    .teamanalyse { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; margin-bottom: 1rem;
                   background: rgba(211, 47, 47, 0.12); border: 2px solid rgba(211, 47, 47, 0.55); border-radius: 8px; padding: 6px 10px; }
    .teamanalyse.ok { background: rgba(76, 175, 80, 0.10); border-color: rgba(76, 175, 80, 0.45); }
    .teamanalyse .warn { flex: 0 0 20px; width: 20px; height: 20px; border-radius: 50%; background: #D32F2F; color: #FFFFFF;
                         font-weight: 800; font-size: 13px; line-height: 20px; text-align: center; }
    .teamanalyse.ok .warn { background: #43A047; }
    .teamanalyse .ta-name { font-weight: 600; margin-right: 4px; }
    .teamanalyse .ta-liste { display: flex; flex-wrap: wrap; gap: 4px 10px; }
    .teamanalyse .ta-eintrag { white-space: nowrap; }
    .teamanalyse .ta-eintrag b { font-size: 12px; margin-left: 2px; }
    .teamanalyse .ta-ok { opacity: 0.8; font-size: 13px; }

    /* Orden-Koffer in der Seitenleiste */
    .st-key-ordenkoffer { border: 1px solid rgba(128, 128, 128, 0.35); border-radius: 10px; padding: 8px 10px; }
    .orden-titel { font-weight: 700; margin-bottom: 0.6rem; }
    .orden-region { font-size: 12px; opacity: 0.75; margin: 2px 0 0.8rem 0; }
    .orden { text-align: center; margin-bottom: 0.6rem; }
    .orden img { height: 40px; max-width: 52px; object-fit: contain; image-rendering: pixelated; }
    .orden.aus img { filter: grayscale(1) brightness(0.55); opacity: 0.6; }
    [class*="st-key-orden_"] { display: flex; justify-content: center; }

    /* Gefangen/Verpasst: gleich groß, füllen ihre Spalte */
    .st-key-btn_gefangen button, .st-key-btn_verpasst button { width: 100% !important; min-height: 42px !important; }

    /* Aktionsleiste über den Team-Slots: kleinere Buttons */
    [class*="st-key-teamaktionen_"] button { min-height: 30px !important; padding: 2px 8px !important; }
    [class*="st-key-teamaktionen_"] [data-testid="stCheckbox"] { justify-content: center; }

    /* Kompakte Listenzeilen (PC-Box, Friedhof, Verpasst) */
    [class*="st-key-zeile_"] { padding: 6px 10px !important; }
    .pc-tab { font-weight: 600; padding: 8px 10px; border-radius: 4px; background: rgba(128, 128, 128, 0.18);
              white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 1rem; }
    .pc-pokes { display: flex; flex-wrap: wrap; gap: 4px 22px; align-items: center; margin-bottom: 1rem; }
    .pc-poke { display: flex; gap: 6px; align-items: center; white-space: nowrap; }
    .pc-poke img { width: 36px; height: 36px; image-rendering: pixelated; }
    .pc-poke .pc-leer { width: 36px; text-align: center; font-size: 20px; }
    .pc-pokes.pc-friedhof img { filter: grayscale(1); opacity: 0.7; }
    .pc-pokes.pc-verpasst img { opacity: 0.55; }

    /* Party-Slot-Design für Links im aktiven Team */
    [class*="st-key-teamslot_"] { background: #10263F; border: 1px solid #23476F; border-radius: 16px; padding: 6px 12px 12px 12px; }
    [class*="st-key-teamslot_"] [data-testid="stCheckbox"] p { color: #E6F1FB; }
    [class*="st-key-slot_"] { background: #E6F1FB; border-radius: 32px 10px 10px 32px; padding: 5px 8px 5px 5px; }
    /* Streamlit zieht HTML-Blöcke unten um 1rem zusammen – hier ausgleichen, damit nichts überhängt */
    .teamslot-route { color: #E6F1FB; font-weight: 600; margin-bottom: 1rem; }
    .teamslot { display: flex; gap: 10px; align-items: center; min-width: 0; margin-bottom: 1rem; }
    .teamslot .ring { width: 54px; height: 54px; flex: 0 0 54px; border-radius: 50%; border: 3px solid #68A090;
                      background: #ffffff; display: flex; align-items: center; justify-content: center; overflow: hidden; }
    .teamslot .ring img { width: 60px; height: 60px; image-rendering: pixelated; }
    .teamslot .ring span { font-size: 24px; }
    .teamslot .info { min-width: 0; flex: 1; }
    .teamslot .schwach { display: flex; align-items: center; gap: 8px; margin-left: auto; text-align: right; line-height: 1.8; max-width: 60%; }
    .teamslot .schwach .warn { flex: 0 0 22px; width: 22px; height: 22px; border-radius: 50%; background: #D32F2F; color: #FFFFFF;
                               font-weight: 800; font-size: 14px; line-height: 22px; text-align: center; }
    .teamslot .schwach b { font-size: 11px; margin-right: 2px; }
    .teamslot .schwach .stufe-4 { color: #A32D2D; }
    .teamslot .schwach .stufe-2 { color: #854F0B; }
    .teamslot .trainer { font-size: 12px; color: #185FA5; line-height: 1.2; }
    .teamslot .pname { font-weight: 600; color: #042C53; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    </style>
""", unsafe_allow_html=True)


# Game-Boy-Color-Look (Gehäuse "Löwenzahn", an Dark Mode angepasst). Nur Optik – an der Bedienung ändert sich nichts.
GBC_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
:root { --gbc-shell: #B07D12; --gbc-acc: #F5D27A; --gbc-screen: #141720; --gbc-box: #262B38; --gbc-rand: #0E1018;
        --gbc-feld: #1B1F2A; --gbc-feldrand: #4A5163; --gbc-text: #ECEAF4; --gbc-leise: #8E93A3; --gbc-slot: #323848; }
.stApp, [data-testid="stHeader"] { background: var(--gbc-screen) !important; }
.stApp { color: var(--gbc-text); }
.stApp p, .stApp li, .stApp label, [data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] { color: var(--gbc-text); }
/* Gehäuse-Rahmen um die ganze Seite (liegt nur obendrauf, verschiebt nichts) */
.stApp::after { content: ""; position: fixed; inset: 0; border: 8px solid var(--gbc-shell); border-radius: 14px 14px 44px 14px;
                pointer-events: none; z-index: 1000100; }
/* Überschriften in Pixel-Schrift */
.stApp h1 { font-family: 'Press Start 2P', monospace !important; font-size: 1.35rem !important; line-height: 1.5 !important; color: var(--gbc-acc) !important; }
[data-testid="stSidebar"] h1 { font-size: 0.8rem !important; }
.stApp h2, .stApp h3 { font-family: 'Press Start 2P', monospace !important; font-size: 0.9rem !important; color: var(--gbc-acc) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--gbc-leise) !important; }
.stApp hr { border-color: #2E3443 !important; }
/* Seitenleiste */
[data-testid="stSidebar"] { background: #10131B !important; border-right: 3px solid var(--gbc-rand) !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: var(--gbc-text) !important; }
/* Eingabefelder, Auswahllisten, Zahlenfelder: GBC-Textfeld (dunkler Rand + goldene Innenlinie) */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
    background: var(--gbc-feld) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 6px !important;
    box-shadow: inset 0 0 0 2px rgba(176, 125, 18, 0.55) !important; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-baseweb="textarea"]:focus-within {
    box-shadow: inset 0 0 0 2px var(--gbc-acc) !important; }
[data-baseweb="base-input"] { background: transparent !important; }
[data-baseweb="input"] input, [data-baseweb="select"] > div div, [data-baseweb="textarea"] textarea {
    color: var(--gbc-text) !important; background: transparent !important; }
[data-baseweb="input"] input::placeholder, [data-baseweb="textarea"] textarea::placeholder { color: var(--gbc-leise) !important; }
[data-baseweb="select"] svg { color: var(--gbc-acc) !important; fill: var(--gbc-acc) !important; }
[data-testid="stNumberInput"] button { background: var(--gbc-box) !important; color: var(--gbc-acc) !important; }
/* Aufklappende Listen der Auswahlfelder */
[data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] ul, [data-baseweb="menu"] {
    background: var(--gbc-box) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 6px !important; }
[data-baseweb="popover"] [role="option"], [data-baseweb="popover"] li { color: var(--gbc-text) !important; background: transparent !important; }
[data-baseweb="popover"] [role="option"]:hover, [data-baseweb="popover"] [aria-selected="true"], [data-baseweb="popover"] li:hover {
    background: #3A4256 !important; color: var(--gbc-acc) !important; }
/* Bearbeiten-Fenster */
[data-testid="stDialog"] [role="dialog"] { background: var(--gbc-box) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 8px !important;
    box-shadow: inset 0 0 0 2px var(--gbc-box), inset 0 0 0 4px var(--gbc-shell) !important; color: var(--gbc-text) !important; }
[data-testid="stDialog"] [role="dialog"] p, [data-testid="stDialog"] [role="dialog"] label { color: var(--gbc-text) !important; }
[data-testid="stDialog"] [role="dialog"] h2 { font-family: 'Press Start 2P', monospace !important; font-size: 0.8rem !important; color: var(--gbc-acc) !important; }
/* Popover-Fenster (Bearbeiten / Löschen) */
[data-testid="stPopoverBody"] { background: var(--gbc-box) !important; border: 3px solid var(--gbc-rand) !important;
    box-shadow: inset 0 0 0 2px var(--gbc-box), inset 0 0 0 4px var(--gbc-shell) !important; }
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] label { color: var(--gbc-text) !important; }
/* Buttons: primär = runder A-Knopf in Gehäusefarbe, sonst GBC-Box */
button[kind="primary"], [data-testid="stBaseButton-primary"], [data-testid="stFormSubmitButton"] button {
    background: var(--gbc-shell) !important; color: #FFFFFF !important; border: 3px solid var(--gbc-rand) !important; border-radius: 18px !important;
    box-shadow: inset 0 -3px 0 rgba(0, 0, 0, 0.25) !important; }
button[kind="primary"] p, [data-testid="stBaseButton-primary"] p, .st-key-btn_verpasst button p { font-family: 'Press Start 2P', monospace !important; font-size: 0.6rem !important; line-height: 1.6 !important; }
button[kind="secondary"], [data-testid="stBaseButton-secondary"], [data-testid="stPopover"] button, [data-testid="stNumberInput"] button {
    background: var(--gbc-box) !important; color: var(--gbc-text) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 6px !important;
    box-shadow: inset 0 0 0 2px rgba(176, 125, 18, 0.55) !important; }
button[kind="secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover, [data-testid="stPopover"] button:hover {
    box-shadow: inset 0 0 0 2px var(--gbc-acc) !important; color: var(--gbc-acc) !important; }
button:disabled { opacity: 0.45 !important; }
.stApp button p { color: inherit !important; }
/* Häkchen, Schalter, Auswahlpunkte und Regler in Gold statt Streamlit-Rot */
[data-testid="stCheckbox"] label > span:first-child { background-color: var(--gbc-feld) !important; border: 2px solid var(--gbc-feldrand) !important; border-radius: 3px !important; }
[data-testid="stCheckbox"] label:has(input:checked) > span:first-child { background-color: var(--gbc-shell) !important; border-color: var(--gbc-acc) !important; }
[data-testid="stCheckbox"] label:has(input:checked) > div:first-child { background-color: var(--gbc-shell) !important; }
[data-testid="stCheckbox"] label:not(:has(input:checked)) > div:first-child { background-color: var(--gbc-feldrand) !important; }
[data-testid="stRadio"] label > div:first-child { border-color: var(--gbc-feldrand) !important; }
[data-testid="stRadio"] label:has(input:checked) > div:first-child { background-color: var(--gbc-shell) !important; border-color: var(--gbc-acc) !important; }
[data-testid="stSlider"] [data-baseweb="slider"] { filter: hue-rotate(38deg) saturate(0.85); }
/* Neuere Streamlit-Versionen: Eingabefelder, Auswahl- und Zahlenfelder */
[data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"], [data-testid="stSelectbox"] [role="group"] {
    background: var(--gbc-feld) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 6px !important;
    box-shadow: inset 0 0 0 2px rgba(176, 125, 18, 0.55) !important; }
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stNumberInputContainer"]:focus-within,
[data-testid="stSelectbox"] [role="group"]:focus-within { box-shadow: inset 0 0 0 2px var(--gbc-acc) !important; }
[data-testid="stTextInputField"], [data-testid="stNumberInputField"], [data-testid="stSelectbox"] input {
    color: var(--gbc-text) !important; background: transparent !important; }
[data-testid="stTextInputField"]::placeholder, [data-testid="stNumberInputField"]::placeholder, [data-testid="stSelectbox"] input::placeholder {
    color: var(--gbc-leise) !important; }
[data-testid="stSelectbox"] button, [data-testid="stSelectbox"] button svg { color: var(--gbc-acc) !important; background: transparent !important; }
[data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"] { background: var(--gbc-box) !important; color: var(--gbc-acc) !important; }
[data-testid="stSelectboxVirtualDropdown"], [data-testid="stSelectboxVirtualDropdown"] [role="listbox"] {
    background: var(--gbc-box) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 6px !important; }
[data-testid="stSelectboxVirtualDropdown"] [role="option"] { color: var(--gbc-text) !important; background: transparent !important; }
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused], [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-selected] { background: #3A4256 !important; color: var(--gbc-acc) !important; }
/* Häkchen (z.B. Level-Caps, "Im Team") */
[data-testid="stCheckbox"] label > div:not(:has([data-testid="stMarkdownContainer"])):not(:has(input)):not(:has(> div)) {
    background-color: var(--gbc-feld) !important; border: 2px solid var(--gbc-feldrand) !important; border-radius: 3px !important; }
[data-testid="stCheckbox"] label[data-selected] > div:not(:has([data-testid="stMarkdownContainer"])):not(:has(input)):not(:has(> div)),
[data-testid="stCheckbox"] label:has(input:checked) > div:not(:has([data-testid="stMarkdownContainer"])):not(:has(input)):not(:has(> div)) {
    background-color: var(--gbc-shell) !important; border-color: var(--gbc-acc) !important; }
[data-testid="stCheckbox"] label svg { stroke: #FFFFFF !important; color: #FFFFFF !important; }
/* Schalter (z.B. "GBC-Design") */
[data-testid="stCheckbox"] label > div:has(> div):not(:has([data-testid="stMarkdownContainer"])):not(:has(input)) {
    background-color: var(--gbc-feldrand) !important; }
[data-testid="stCheckbox"] label[data-selected] > div:has(> div):not(:has([data-testid="stMarkdownContainer"])):not(:has(input)),
[data-testid="stCheckbox"] label:has(input:checked) > div:has(> div):not(:has([data-testid="stMarkdownContainer"])):not(:has(input)) {
    background-color: var(--gbc-shell) !important; }
/* Auswahlpunkte (Gefangen / Verpasst) */
[data-testid="stRadioOption"] div:has(> [data-testid="stMarkdownContainer"]) > div:first-child {
    background-color: var(--gbc-feld) !important; border-color: var(--gbc-feldrand) !important; }
[data-testid="stRadioOption"][data-selected] div:has(> [data-testid="stMarkdownContainer"]) > div:first-child,
[data-testid="stRadioOption"]:has(input:checked) div:has(> [data-testid="stMarkdownContainer"]) > div:first-child {
    background-color: var(--gbc-shell) !important; border-color: var(--gbc-acc) !important; }
[data-testid="stSlider"] { filter: hue-rotate(38deg) saturate(0.85); }
/* Eingabebereich oben als eine große GBC-Box */
.st-key-eingabebox { background: var(--gbc-box) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 6px !important;
    box-shadow: inset 0 0 0 2px var(--gbc-box), inset 0 0 0 4px var(--gbc-shell) !important; padding: 14px 16px !important; }
/* Hinweisboxen (z.B. "Bearbeiten freigeschaltet", "Nächster Cap") als GBC-Textbox */
/* nur EIN Rahmen: äußere Hülle unsichtbar, innerer Kasten im GBC-Stil (falls es die Hülle gibt) */
[data-testid="stAlert"] { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
[data-testid="stAlert"]:not(:has([data-testid="stAlertContainer"])), [data-testid="stAlert"] [data-testid="stAlertContainer"] {
    background: var(--gbc-box) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 6px !important;
    box-shadow: inset 0 0 0 2px var(--gbc-box), inset 0 0 0 4px var(--gbc-shell) !important; padding: 8px 12px !important; }
[data-testid="stAlert"] *, [data-testid="stAlertContainer"] * { background: transparent !important; color: var(--gbc-text) !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) p { color: #9FE0A3 !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) p, [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) p { color: var(--gbc-acc) !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) p { color: #FF9A8F !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) [data-testid="stAlertContainer"] { box-shadow: inset 0 0 0 2px var(--gbc-box), inset 0 0 0 4px #C0392B !important; }
/* Boxen im Gold/Silber-Stil: dicker dunkler Rand + feine Innenlinie in Gehäusefarbe */
[class*="st-key-zeile_"] { background: var(--gbc-box) !important; border: 2px solid var(--gbc-rand) !important; border-radius: 4px !important;
    box-shadow: none !important; }
.pc-tab { background: var(--gbc-shell); color: #FFFFFF; font-family: 'Press Start 2P', monospace; font-size: 0.55rem; line-height: 1.8; font-weight: 400; }
.pc-tab.pc-friedhof { background: #4A5163; color: #D3D1C7; }
.pc-tab.pc-verpasst { background: #323848; color: var(--gbc-leise); }
.pc-poke b { color: var(--gbc-leise); font-weight: 400; }
[data-testid="stExpander"] details, [data-testid="stMetric"] {
    background: var(--gbc-box) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 6px !important;
    box-shadow: inset 0 0 0 2px var(--gbc-box), inset 0 0 0 4px var(--gbc-shell) !important; }
[data-testid="stMetric"] { padding: 8px 12px; }
[data-testid="stMetricValue"] { color: var(--gbc-acc) !important; font-family: 'Press Start 2P', monospace; font-size: 1.3rem !important; }
[data-testid="stExpander"] summary p { color: var(--gbc-acc) !important; }
/* Tabs */
.stApp [data-baseweb="tab"] p { color: var(--gbc-leise); }
.stApp [data-baseweb="tab"][aria-selected="true"] p { color: var(--gbc-acc) !important; }
.stApp [data-baseweb="tab-highlight"] { background: var(--gbc-acc) !important; }
/* Team-Slots im GBC-Look */
.st-key-teamanalyse { border-width: 3px !important; }
.st-key-ordenkoffer { background: #2E3A52 !important; border: 3px solid var(--gbc-rand) !important; border-radius: 8px !important;
    box-shadow: inset 0 0 0 2px #2E3A52, inset 0 0 0 4px var(--gbc-shell) !important; }
.orden-titel { font-family: 'Press Start 2P', monospace; font-size: 0.6rem; color: var(--gbc-acc); }
.orden-region { color: var(--gbc-acc); }
.orden.an img { filter: drop-shadow(0 0 5px rgba(245, 210, 122, 0.85)); }
[class*="st-key-teamslot_"] { background: var(--gbc-box) !important; border: 3px solid var(--gbc-rand) !important; border-radius: 6px !important;
    box-shadow: inset 0 0 0 2px var(--gbc-box), inset 0 0 0 4px var(--gbc-shell) !important; }
[class*="st-key-slot_"] { background: #F4F1E6 !important; border: 2px solid var(--gbc-rand); }
.teamslot-route { color: var(--gbc-acc) !important; font-family: 'Press Start 2P', monospace; font-size: 0.7rem; }
.teamslot .ring { background: #FFFFFF !important; }
.teamslot .trainer { color: #7A6420 !important; }
.teamslot .pname { color: #1E2230 !important; font-family: 'Press Start 2P', monospace; font-size: 0.62rem; line-height: 1.8 !important; }
/* Typ-Farben etwas gedimmt, damit sie auf Dunkel nicht grell leuchten */
span.typ { filter: brightness(0.88); font-family: 'Press Start 2P', monospace !important; font-size: 0.42rem !important;
           text-transform: uppercase; letter-spacing: 0; line-height: 1.5 !important; padding: 3px 5px !important;
           border: 2px solid var(--gbc-rand) !important; border-radius: 4px !important; display: inline-block !important;
           vertical-align: middle; box-shadow: inset 0 -2px 0 rgba(0, 0, 0, 0.3); text-shadow: 1px 1px 0 rgba(0, 0, 0, 0.55); }
</style>
"""


# ---------- Zwischenspeicher (spart Firebase-Lesevorgänge) ----------
# Links: tracker_logik führt einen Zwischenspeicher mit und trägt jede gespeicherte Änderung dort nach
#        (siehe tracker_logik.lade_daten_cache) -> Eintragen, Team, Friedhof kosten keine Lesevorgänge.
# Einstellungen: werden hier zwischengespeichert und nach jeder Änderung neu geladen (1 Lesevorgang).
# Beides gilt für alle Besucher gemeinsam; spätestens nach 10 Minuten wird frisch aus Firebase gelesen.
@st.cache_data(ttl=600, show_spinner=False)
def einstellungen_zwischenspeicher(run_id):
    return tracker_logik.lade_run_einstellungen(run_id, fehler_werfen=True)


def zwischenspeicher_leeren(art=None):
    """Nach einer Einstellungs-Änderung die Einstellungen neu laden (die Links führt tracker_logik selbst mit)."""
    if art in (None, "einstellungen"):
        einstellungen_zwischenspeicher.clear()


tracker_logik.NACH_SCHREIBEN[:] = [zwischenspeicher_leeren]


def lade_daten_schnell(run_id):
    try:
        return tracker_logik.lade_daten_cache(run_id)
    except Exception as e:  # Fehler werden nicht zwischengespeichert -> nächster Klick versucht es neu
        print("Daten konnten nicht geladen werden:", e)
        return []


def lade_einstellungen_schnell(run_id):
    try:
        return einstellungen_zwischenspeicher(run_id)
    except Exception as e:
        print("Einstellungen konnten nicht geladen werden:", e)
        return tracker_logik.lade_run_einstellungen(run_id)


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
    neues_pw = st.sidebar.text_input("Passwort (empfohlen):", type="password", key="neuer_run_pw",
                                     help="Ohne Passwort kann jeder mit dem Link den Run bearbeiten und löschen. Ansehen können ihn immer alle.")
    if st.sidebar.button("Run anlegen", type="primary"):
        name = (neuer_name or "").strip()
        if not name:
            st.sidebar.warning("Bitte einen Namen eingeben.")
        elif name.lower() in [r.lower() for r in alle_runs]:
            st.sidebar.warning("Diesen Run gibt es schon – wähle ihn oben in der Liste aus.")
        elif neues_pw and len(neues_pw) < 4:
            st.sidebar.warning("Das Passwort braucht mindestens 4 Zeichen.")
        else:
            tracker_logik.speichere_run_einstellungen(name, anzahl_spieler=1)
            if neues_pw:
                schluessel = tracker_logik.run_passwort_setzen(name, neues_pw)
                if schluessel:
                    st.session_state.setdefault("freigaben", {})[name] = schluessel
            runs_laden.clear()
            st.session_state.run_wunsch = name
            st.rerun()
    aktueller_run = st.session_state.get("letzter_run", alle_runs[0])
else:
    aktueller_run = auswahl
    st.session_state.letzter_run = auswahl
    if st.query_params.get("run") != auswahl:
        st.query_params["run"] = auswahl

# Einstellungen des Runs (Spielernamen, Spiel, besiegte Arenen, Passwort) laden
st.session_state.einst = lade_einstellungen_schnell(aktueller_run)
st.session_state.geladener_run = aktueller_run
einst = st.session_state.einst

# ---------- Passwortschutz: darf dieser Browser den Run bearbeiten? ----------
freigaben = st.session_state.setdefault("freigaben", {})
url_schluessel = st.query_params.get("schluessel")
if url_schluessel and tracker_logik.pruefe_schluessel(aktueller_run, einst, url_schluessel):
    freigaben[aktueller_run] = url_schluessel
geschuetzt = tracker_logik.run_geschuetzt(einst)
darf_bearbeiten = (not geschuetzt) or tracker_logik.pruefe_schluessel(aktueller_run, einst, freigaben.get(aktueller_run))
gesperrt = not darf_bearbeiten

if auswahl != NEUER_RUN:
    # Schlüssel in der Adresse halten, damit die Freigabe ein Neuladen übersteht
    gewuenscht = freigaben.get(aktueller_run) if (geschuetzt and darf_bearbeiten) else None
    if st.query_params.get("schluessel") != gewuenscht:
        if gewuenscht:
            st.query_params["schluessel"] = gewuenscht
        elif "schluessel" in st.query_params:
            del st.query_params["schluessel"]

daten = lade_daten_schnell(aktueller_run)

if auswahl != NEUER_RUN:
    if geschuetzt and gesperrt:
        st.sidebar.warning("🔒 Geschützter Run – nur ansehen.")
        pw_eingabe = st.sidebar.text_input("Passwort zum Bearbeiten:", type="password", key=f"pw_eingabe_{aktueller_run}")
        if st.sidebar.button("🔓 Entsperren", key=f"entsperren_{aktueller_run}"):
            schluessel = tracker_logik.pruefe_passwort(aktueller_run, einst, pw_eingabe)
            if schluessel:
                freigaben[aktueller_run] = schluessel
                st.query_params["schluessel"] = schluessel
                melde("success", "🔓 Run entsperrt – du kannst jetzt bearbeiten.")
                st.rerun()
            else:
                st.sidebar.error("Falsches Passwort.")
    elif geschuetzt:
        st.sidebar.success("🔓 Bearbeiten freigeschaltet")
        if st.sidebar.button("🔒 Wieder sperren", key=f"sperren_{aktueller_run}"):
            freigaben.pop(aktueller_run, None)
            if "schluessel" in st.query_params:
                del st.query_params["schluessel"]
            st.rerun()
    else:
        st.sidebar.info("🔓 Kein Passwort – jeder mit dem Link kann bearbeiten.")

    if not gesperrt:
        with st.sidebar.expander("🔑 Passwort ändern" if geschuetzt else "🔑 Passwort festlegen"):
            pw1 = st.text_input("Neues Passwort:", type="password", key=f"pw_neu1_{aktueller_run}")
            pw2 = st.text_input("Passwort wiederholen:", type="password", key=f"pw_neu2_{aktueller_run}")
            if st.button("Passwort speichern", key=f"pw_speichern_{aktueller_run}"):
                if len(pw1 or "") < 4:
                    st.error("Das Passwort braucht mindestens 4 Zeichen.")
                elif pw1 != pw2:
                    st.error("Die Passwörter stimmen nicht überein.")
                else:
                    schluessel = tracker_logik.run_passwort_setzen(aktueller_run, pw1)
                    if schluessel:
                        freigaben[aktueller_run] = schluessel
                        st.query_params["schluessel"] = schluessel
                        melde("success", "🔑 Passwort gespeichert. Dieser Browser bleibt freigeschaltet – "
                                         "setz dir am besten ein Lesezeichen auf die aktuelle Adresse.")
                        st.rerun()
                    else:
                        st.error("Passwort konnte nicht gespeichert werden. Bitte nochmal versuchen.")

if auswahl != NEUER_RUN and not gesperrt:
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

# ---------- Design: GBC (Löwenzahn, Dark Mode) oder klassisch ----------
design_key = f"design_{aktueller_run}"
if design_key not in st.session_state:
    st.session_state[design_key] = einst.get("design", "gbc") != "klassisch"


def design_gewechselt(run, key):
    wert = "gbc" if st.session_state[key] else "klassisch"
    einst["design"] = wert
    if not gesperrt:  # bei gesperrten Runs gilt die Wahl nur für diesen Besuch
        tracker_logik.speichere_run_einstellungen(run, design=wert)


schalter = getattr(st.sidebar, "toggle", st.sidebar.checkbox)
schalter("🎮 GBC-Design", key=design_key, on_change=design_gewechselt, args=(aktueller_run, design_key),
         help="Aus = altes, klassisches Design")
if st.session_state[design_key]:
    st.markdown(GBC_CSS, unsafe_allow_html=True)

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


gewaehlte_gen = st.sidebar.selectbox("Wähle dein Spiel:", spiele, key=spiel_key, disabled=gesperrt,
                                     on_change=spiel_gewechselt, args=(aktueller_run, spiel_key))

spiel_schluessel = tracker_logik.schluessel(gewaehlte_gen)
besiegt = set(einst["besiegt"].get(spiel_schluessel, []))
caps = LEVEL_CAPS[gewaehlte_gen]


def ist_cap(text):
    return re.search(r"Lv \d+", text) is not None and not text.startswith("--")


naechster_cap = next((c for i, c in enumerate(caps) if ist_cap(c) and i not in besiegt), None)
hat_caps = any(ist_cap(c) for c in caps)

if naechster_cap:
    st.sidebar.success(f"Nächster Cap: **{naechster_cap}**")
elif hat_caps:
    st.sidebar.success("Alle Caps geschafft!")
def cap_umschalten(run, sk, idx, key):
    liste = set(einst["besiegt"].get(sk, []))
    if st.session_state[key]:
        liste.add(idx)
    else:
        liste.discard(idx)
    einst["besiegt"][sk] = sorted(liste)
    tracker_logik.speichere_run_einstellungen(run, besiegt={sk: sorted(liste)})


# ---------- Orden-Koffer (Orden-Bilder aus dem PokeAPI-Sprite-Archiv, wie die Pokémon-Sprites) ----------
ORDEN_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/badges/{}.png"
_KANTO = list(range(1, 9))
_JOHTO = list(range(9, 17))
_HOENN = list(range(17, 25))
# Pro Spiel: [(Überschrift, [(Index in LEVEL_CAPS, Orden-Nummer), ...]), ...]
ORDEN = {
    "Gen 1: Rot/Blau": [("", list(zip(range(8), _KANTO)))],
    "Gen 1: Gelb": [("", list(zip(range(8), _KANTO)))],
    "Gen 2: Gold/Silber/Kristall": [("Johto", list(zip(range(8), _JOHTO))), ("Kanto", list(zip(range(14, 22), _KANTO)))],
    "Gen 3: Rubin/Saphir": [("", list(zip(range(8), _HOENN)))],
    "Gen 3: Smaragd": [("", list(zip(range(8), _HOENN)))],
    "Gen 3: Feuerrot/Blattgrün": [("", list(zip(range(8), _KANTO)))],
    "Gen 4: Diamant/Perl": [("", list(zip(range(8), range(25, 33))))],
    "Gen 4: Platin": [("", list(zip(range(8), [25, 26, 29, 27, 28, 30, 31, 32])))],
    "Gen 4: HeartGold/SoulSilver": [("Johto", list(zip(range(8), _JOHTO))), ("Kanto", list(zip(range(14, 22), _KANTO)))],
    "Gen 5: Schwarz/Weiß": [("", list(zip(range(8), [33, 34, 36, 37, 38, 39, 40, 41])))],
    "Gen 5: Schwarz 2/Weiß 2": [("", list(zip(range(8), [34, 35, 36, 37, 38, 39, 41, 42])))],
    "Gen 6: X/Y": [("", list(zip(range(8), range(43, 51))))],
    "Gen 6: Omega Rubin/Alpha Saphir": [("", list(zip(range(8), _HOENN)))],
    "Gen 8: Schwert/Schild": [("", list(zip(range(8), [51, 52, 53, 54, 56, 57, 59, 60])))],
    "Gen 9: Karmesin/Purpur": [("", list(zip(range(1, 9), range(70, 78))))],
}


def sidebar_box(name):
    try:
        return st.sidebar.container(key=name)
    except TypeError:
        return st.sidebar.container()


def cap_haken(idx, key, label):
    """Häkchen für einen Kampf; Zustand kommt immer aus den gespeicherten Daten (Orden-Koffer und Liste bleiben synchron)."""
    st.session_state[key] = idx in besiegt
    st.checkbox(label, key=key, disabled=gesperrt, on_change=cap_umschalten,
                args=(aktueller_run, spiel_schluessel, idx, key))


orden_gruppen = ORDEN.get(gewaehlte_gen)
if orden_gruppen:
    with sidebar_box("ordenkoffer"):
        st.markdown("<div class='orden-titel'>Orden-Koffer</div>", unsafe_allow_html=True)
        for titel, paare in orden_gruppen:
            if titel:
                st.markdown(f"<div class='orden-region'>{titel}</div>", unsafe_allow_html=True)
            for start in range(0, len(paare), 2):
                for spalte, (cap_idx, orden_nr) in zip(st.columns(2), paare[start:start + 2]):
                    with spalte:
                        erledigt = cap_idx in besiegt
                        treffer = re.search(r"Lv (\d+)", caps[cap_idx]) if cap_idx < len(caps) else None
                        st.markdown(f"<div class='orden {'an' if erledigt else 'aus'}'><img src='{ORDEN_URL.format(orden_nr)}' alt=''></div>",
                                    unsafe_allow_html=True)
                        cap_haken(cap_idx, f"orden_{aktueller_run}_{spiel_schluessel}_{cap_idx}",
                                  f"Lv {treffer.group(1)}" if treffer else "besiegt")

# Die Arenen stehen schon im Orden-Koffer -> in der Liste nur noch Top 4, Champ & Co.
im_koffer = {cap_idx for _, paare in (orden_gruppen or []) for cap_idx, _ in paare}
with st.sidebar.expander("Weitere Kämpfe abhaken" if orden_gruppen else "Kämpfe abhaken", expanded=not orden_gruppen):
    if hat_caps:
        st.caption("Hake besiegte Kämpfe ab – das wird pro Run gespeichert.")
    for idx, cap in enumerate(caps):
        if idx in im_koffer:
            continue
        if ist_cap(cap):
            cap_haken(idx, f"cap_{aktueller_run}_{spiel_schluessel}_{idx}", f"**{cap}**")
        else:
            st.markdown(f"*{cap}*")

# ==========================================
# 3. EINGABE-BEREICH
# ==========================================
anzahl_key = f"anzahl_{aktueller_run}"
if anzahl_key not in st.session_state:
    st.session_state[anzahl_key] = einst["anzahl_spieler"]
anzahl_spieler = st.session_state[anzahl_key]

# Layout: Bei 3 Spielern Typ-Suche oben neben dem Titel und Eingabe über die volle Breite.
# Bei 1–2 Spielern ist die Eingabe schmaler und Typ-Suche/Schwächen sitzen rechts daneben,
# damit sie sich in den freien Platz öffnen, ohne die Seite zu verschieben.
DREI_SPIELER = anzahl_spieler >= 3
if DREI_SPIELER:
    try:
        titel_spalte, typ_spalte = st.columns([3, 1], vertical_alignment="center")
    except TypeError:
        titel_spalte, typ_spalte = st.columns([3, 1])
else:
    titel_spalte = st.container()

with titel_spalte:
    st.title("Pokémon Soul-Link Tracker")
    cap_hinweis = f" · Nächster Level-Cap: **{naechster_cap}**" if naechster_cap else ""
    st.caption(f"Aktueller Spielstand: **{aktueller_run}**{cap_hinweis}")

# Kleine Typ-Suche oben rechts (z.B. für Gegner im Kampf) – nutzt die lokalen Pokémon-Daten
GEN_NR = tracker_logik.generation_aus_spiel(gewaehlte_gen)  # Typen/Schwächen passend zum gewählten Spiel


def fang_spiel_fuer(spielname):
    """Welche Fangformel zum gewählten Spiel passt (ab Gen 6 als Näherung die von Gen 5)."""
    if "HeartGold" in spielname:
        return "HGSS"
    gen = tracker_logik.generation_aus_spiel(spielname)
    if gen == 4:
        return "Gen 4 (DPPt)"
    if gen in (1, 2, 3, 5):
        return f"Gen {gen}"
    return "Gen 5"


FANG_SPIEL = fang_spiel_fuer(gewaehlte_gen)


def typ_badges_gross(typen):
    return "".join(
        f"<span class='typ' style='background-color:{TYP_FARBEN.get(t, '#68A090')}; color:white; padding:1px 6px; "
        f"border-radius:3px; font-size:12px; margin-right:4px;'>{t}</span>" for t in typen)


SCHWAECHEN_STUFEN = [(4.0, "4×"), (2.0, "2×"), (1.0, "1×"), (0.5, "½×"), (0.25, "¼×"), (0.0, "0×")]


def zeichne_schwaechen(pokemon_name):
    """Schadens-Stufen gegen das Pokémon – nur Stufen, die es auch gibt."""
    gruppen = tracker_logik.schwaechen(pokemon_name, GEN_NR)
    zeilen = []
    for wert, text in SCHWAECHEN_STUFEN:
        typen = gruppen.get(wert)
        if not typen:
            continue
        badges = "".join(
            f"<span class='typ' style='background-color:{TYP_FARBEN.get(t, '#68A090')}; color:white; padding:1px 5px; "
            f"border-radius:3px; font-size:11px; margin:0 3px 3px 0; display:inline-block;'>{t}</span>" for t in typen)
        zeilen.append(f"<div style='display:flex; gap:6px; align-items:flex-start; margin-bottom:2px;'>"
                      f"<b style='min-width:30px; font-size:13px;'>{text}</b><div>{badges}</div></div>")
    st.markdown("".join(zeilen), unsafe_allow_html=True)
    if GEN_NR:
        st.caption(f"Typen-Tabelle von Gen {GEN_NR} (Spiel aus den Level-Caps).")


def typ_bereich():
    gesucht = st.selectbox("Typ nachschlagen", POKEMON_NAMEN, index=None, key="typ_suche",
                           placeholder="🔍 Typ nachschlagen…", label_visibility="collapsed")
    if gesucht:
        typen = tracker_logik.typen_fuer(gesucht, GEN_NR) or ["Unbekannt"]
        st.markdown(f"<div style='font-size:13px; margin-bottom:0.75rem;'><b>{html.escape(gesucht)}</b>&nbsp; {typ_badges_gross(typen)}</div>",
                    unsafe_allow_html=True)
    with st.expander("🛡️ Schwächen", expanded=bool(gesucht)):
        if gesucht:
            zeichne_schwaechen(gesucht)
        else:
            st.caption("Oben ein Pokémon suchen, dann siehst du hier, was wie stark trifft.")

if DREI_SPIELER:
    with typ_spalte:
        typ_bereich()
    eingabe_spalte = st.container()
else:
    eingabe_spalte, rechts_spalte = st.columns([2, 1], gap="large")
    with rechts_spalte:
        typ_bereich()

formular_nr = st.session_state.setdefault("formular_nr", 0)

if gesperrt:
    eingabe_spalte.info("🔒 Dieser Run ist geschützt. Ansehen geht, zum Eintragen und Bearbeiten links mit dem Passwort entsperren.")


def spalten_mittig(spec):
    """st.columns mit senkrecht zentriertem Inhalt (falls die Streamlit-Version das kann)."""
    try:
        return st.columns(spec, vertical_alignment="center")
    except TypeError:
        return st.columns(spec)


def box_rahmen(name, eltern=None):
    """Container mit Schlüssel (für das GBC-Design); ältere Streamlit-Versionen ohne key bekommen einen normalen."""
    eltern = eltern or st
    try:
        return eltern.container(key=name)
    except TypeError:
        return eltern.container()


KRAFT_STUFEN = ["Keine", "↑ (+10 %)", "↑↑ (+20 %)", "↑↑↑ / S / MAX (+30 %)"]


def fangchance_bereich(pokemon_name, k):
    """Fangchance-Rechner für ein Pokémon im Eingabebereich (k = Präfix für die Feld-Schlüssel).
    Ball & Zusatzangaben bleiben gemerkt, Level/KP/Status werden nach jedem Speichern zurückgesetzt."""
    spiel = FANG_SPIEL
    nr = formular_nr
    ball = st.selectbox("Ball", tracker_logik.baelle_fuer(spiel), key=f"{k}_ball_{spiel}",
                        format_func=lambda b: tracker_logik.BAELLE[b][0])
    level = st.number_input("Level", 1, 100, 10, key=f"{k}_level_{nr}")
    kp = st.slider("KP übrig (%)", 1, 100, 100, key=f"{k}_kp_{nr}")
    eins = st.checkbox("Genau 1 KP (Trugschlag)", key=f"{k}_eins_{nr}")
    status = st.selectbox("Status", tracker_logik.STATUS_LISTE, key=f"{k}_status_{nr}")
    if spiel == "Gen 2" and status in ("Paralyse", "Vergiftet", "Verbrennung"):
        st.caption("In Gen 2 bringt dieser Status nichts (Spiel-Bug) – nur Schlaf und Gefroren helfen.")

    extras = {}
    if ball in ("timer", "flott"):
        extras["runde"] = st.number_input("Kampfrunde", 1, 99, 1, key=f"{k}_runde_{nr}")
    if ball == "finster":
        extras["nacht_hoehle"] = st.checkbox("Nachts oder in einer Höhle", key=f"{k}_nacht")
    if ball == "tauch":
        extras["wasser"] = st.checkbox("Unter Wasser (Taucher)" if spiel == "Gen 3" else "Beim Surfen oder Angeln", key=f"{k}_wasser")
    if ball == "wieder":
        extras["schon_gefangen"] = st.checkbox("Schon mal gefangen (Pokédex)", key=f"{k}_wieder_{nr}")
    if ball == "koeder":
        extras["angeln"] = st.checkbox("Beim Angeln", key=f"{k}_angeln")
    if ball == "level":
        extras["eigenes_level"] = st.number_input("Level deines Pokémon", 1, 100, 10, key=f"{k}_eigen")
    if ball == "sympa":
        extras["liebe"] = st.checkbox("Dein Pokémon: gleiche Art, gleiches Geschlecht (Gen-2-Bug)" if spiel == "Gen 2"
                                      else "Dein Pokémon: gleiche Art, anderes Geschlecht", key=f"{k}_liebe_{nr}")
    if spiel == "Gen 2" and ball == "mond":
        st.caption("Der Mondball hat in Gen 2 durch einen Bug keine Wirkung.")
    if spiel == "Gen 2" and ball == "turbo":
        st.caption("Der Turboball wirkt in Gen 2 nur bei Sleima, Tangela und Magnetilo (Bug).")
    if spiel == "Gen 5":
        extras["dichtes_gras"] = st.checkbox("Im dichten Gras", key=f"{k}_gras_{nr}")
        extras["pokedex"] = st.number_input("Gefangene Arten im Pokédex", 0, 649, 100, key=f"{k}_dex",
                                            help="Beeinflusst kritische Fänge und den Abzug im dichten Gras.")
        extras["fangkraft"] = KRAFT_STUFEN.index(st.selectbox("Fangkraft (Kontaktclub)", KRAFT_STUFEN, key=f"{k}_kraft"))

    chance, _ = tracker_logik.fangchance(pokemon_name, ball, kp, status, int(level), spiel, eins_kp=eins, **extras)
    if chance is None:
        st.caption("Für dieses Pokémon gibt es keine Fangrate.")
        return
    prozent = f"{chance * 100:.1f}".replace(".", ",")
    st.markdown(f"<div style='font-size:22px; font-weight:600;'>{prozent} %</div>", unsafe_allow_html=True)
    wuerfe = tracker_logik.wuerfe_fuer(chance)
    if chance >= 1:
        st.caption("Fängt garantiert.")
    elif wuerfe:
        st.caption(f"Pro Wurf · für 90 % Sicherheit ca. {wuerfe} {'Wurf' if wuerfe == 1 else 'Würfe'}")
    hinweis = f"Formel von {spiel}; KP mit durchschnittlichen IVs/DVs geschätzt."
    if not (GEN_NR and GEN_NR <= 5):
        hinweis += " Dein Spiel (ab Gen 6) rechnet etwas anders – nur ein Anhaltspunkt."
    st.caption(hinweis)


with box_rahmen("eingabebox", eingabe_spalte):
    route_kopf = spalten_mittig([4, 1])
    with route_kopf[0]:
        st.markdown("<div class='feld-titel'>📍 Route</div>", unsafe_allow_html=True)
    with route_kopf[1]:
        static_an = st.checkbox("Static", key=f"static_{formular_nr}", disabled=gesperrt,
                                help="Für Geschenk- und Static-Pokémon: Routen- und Dupes-Prüfung werden übersprungen.")
    route_input = st.text_input("📍 Route", placeholder="z.B. Route 1", key=f"route_{formular_nr}", disabled=gesperrt,
                                label_visibility="collapsed")


    def name_geaendert(run, i, key):
        einst["spieler"][i] = st.session_state[key]
        tracker_logik.speichere_run_einstellungen(run, spieler=list(einst["spieler"]))


    vergeben = tracker_logik.vergebene_pokemon(daten)


    def pokemon_label(name):
        """Markiert in der Auswahl Pokémon, die wegen der Dupes Clause schon vergeben sind."""
        grund = vergeben.get(name.lower())
        if not grund:
            return name
        if grund.lower() == name.lower():
            return f"{name}  ⛔ schon gehabt"
        return f"{name}  ⛔ Reihe von {grund}"


    def pokemon_label_fuer(i):
        """Wie pokemon_label, markiert zusätzlich, was ein anderer Trainer in diesem Link schon gewählt hat."""
        andere = [st.session_state.get(f"p_{j}_{formular_nr}") for j in range(anzahl_spieler) if j != i]
        andere = [a for a in andere if a]

        def label(name):
            if any(tracker_logik.gleiche_reihe(a, name) for a in andere):
                return f"{name}  ⛔ schon in diesem Link"
            return pokemon_label(name)
        return label


    spieler_cols = st.columns(3 if DREI_SPIELER else 2)

    p_names = ["", "", ""]
    p_pokes = ["", "", ""]

    for i in range(anzahl_spieler):
        with spieler_cols[i]:
            name_key = f"n_{aktueller_run}_{i}"
            p_names[i] = st.text_input(f"Name Spieler {i+1}", value=einst["spieler"][i], key=name_key, disabled=gesperrt,
                                       on_change=name_geaendert, args=(aktueller_run, i, name_key))
            p_pokes[i] = st.selectbox("Pokémon", POKEMON_NAMEN, index=None, disabled=gesperrt,
                                      format_func=pokemon_label_fuer(i), placeholder="Tippen zum Suchen…",
                                      key=f"p_{i}_{formular_nr}") or ""
            if p_pokes[i]:
                st.markdown("<div style='margin-bottom:0.75rem;'>"
                            + typ_badges_gross(tracker_logik.typen_fuer(p_pokes[i], GEN_NR) or ["Unbekannt"]) + "</div>",
                            unsafe_allow_html=True)
                with st.expander("🎯 Fangchance"):
                    fangchance_bereich(p_pokes[i], f"fc{i}")


    def spieleranzahl_setzen(neu):
        st.session_state[anzahl_key] = neu
        einst["anzahl_spieler"] = neu
        tracker_logik.speichere_run_einstellungen(aktueller_run, anzahl_spieler=neu)


    def link_speichern(status):
        if not route_input or not p_pokes[0]:
            st.warning("Bitte mindestens eine Route und ein Pokémon eingeben!")
            return
        with st.spinner('Prüfe Datenbank...'):
            erfolg, nachricht = tracker_logik.link_hinzufuegen(
                aktueller_run, route_input, p_names[0], p_pokes[0], p_names[1], p_pokes[1], p_names[2], p_pokes[2], status,
                static=static_an
            )
        if erfolg:
            melde("success", nachricht)
            st.session_state.formular_nr = formular_nr + 1  # leert Route, Pokémon & Fangchance-Felder
            st.rerun()
        else:
            st.error(nachricht)


    col_btn1, col_btn2, col_gef, col_verp = st.columns([1, 1, 1.5, 1.5])
    with col_btn1:
        if anzahl_spieler < 3:
            if st.button("➕ Spieler hinzufügen", disabled=gesperrt):
                spieleranzahl_setzen(anzahl_spieler + 1)
                st.rerun()
    with col_btn2:
        if anzahl_spieler > 1:
            if st.button("➖ Spieler entfernen", disabled=gesperrt):
                spieleranzahl_setzen(anzahl_spieler - 1)
                st.rerun()
    with col_gef:
        if st.button("Gefangen speichern", key="btn_gefangen", type="primary", disabled=gesperrt):
            link_speichern("Gefangen")
    with col_verp:
        if st.button("Verpasst speichern", key="btn_verpasst", disabled=gesperrt):
            link_speichern("Verpasst")


if "meldung" in st.session_state:
    art, text = st.session_state.pop("meldung")
    getattr(st, art)(text)

st.divider()

# ==========================================
# 4. KOMPAKTE LISTEN-ZEICHNUNG
# ==========================================
def bearbeiten_formular(eintrag, mit_titel=True):
    link_id = eintrag["id"]
    with st.form(key=f"edit_{link_id}"):
        if mit_titel:
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
        if st.form_submit_button("💾 Änderung speichern", type="primary", disabled=gesperrt):
            erfolg, nachricht = tracker_logik.link_bearbeiten(link_id, eintrag, neue_route, namen, pokes)
            melde("success" if erfolg else "error", nachricht)
            st.rerun()


# Das Bearbeiten-Formular enthält pro Spieler eine Auswahlliste mit allen Pokémon. Früher wurde es für
# JEDEN Link bei jedem Klick mit aufgebaut (bei 60 Links über 120.000 Listeneinträge pro Seitenaufbau).
# Jetzt entsteht es erst, wenn man wirklich auf "Bearbeiten" klickt – als eigenes Fenster.
if hasattr(st, "dialog"):
    @st.dialog("Link bearbeiten")
    def bearbeiten_fenster(eintrag):
        bearbeiten_formular(eintrag, mit_titel=False)
else:
    bearbeiten_fenster = None


def team_umschalten(run, link_id, key):
    erfolg, msg = tracker_logik.team_status_aendern(run, link_id, st.session_state[key])
    if not erfolg:
        st.session_state.team_fehler = msg


def zeichne_aktionen(eintrag, zeige_checkbox, spalten):
    """Die Buttons eines Links: Team, Bearbeiten, Verpasst/Aktiv, Friedhof, Löschen."""
    link_id = eintrag["id"]
    status = eintrag.get("status", "aktiv")
    with spalten[0]:
        if zeige_checkbox:
            team_key = f"team_{link_id}"
            st.session_state[team_key] = bool(eintrag.get("in_team", False))
            st.checkbox("Im Team", key=team_key, disabled=gesperrt, on_change=team_umschalten, args=(aktueller_run, link_id, team_key))
    with spalten[1]:
        if bearbeiten_fenster:
            if st.button("✏️", key=f"e_{link_id}", help="Bearbeiten (z.B. nach einer Entwicklung)", disabled=gesperrt):
                bearbeiten_fenster(eintrag)
        else:  # ältere Streamlit-Version ohne Fenster
            with st.popover("✏️", help="Bearbeiten (z.B. nach einer Entwicklung)", disabled=gesperrt):
                bearbeiten_formular(eintrag)
    with spalten[2]:
        if status == "aktiv":
            if st.button("🏃", key=f"v_{link_id}", help="Verpasst", disabled=gesperrt): tracker_logik.status_aendern(link_id, "verpasst"); st.rerun()
        else:
            if st.button("♻️", key=f"a_{link_id}", help="Aktiv", disabled=gesperrt): tracker_logik.status_aendern(link_id, "aktiv"); st.rerun()
    with spalten[3]:
        if status != "friedhof":
            if st.button("💀", key=f"f_{link_id}", help="Friedhof", disabled=gesperrt): tracker_logik.status_aendern(link_id, "friedhof"); st.rerun()
        else:
            if st.button("🏃", key=f"v2_{link_id}", help="Verpasst", disabled=gesperrt): tracker_logik.status_aendern(link_id, "verpasst"); st.rerun()
    with spalten[4]:
        with st.popover("🗑️", help="Löschen", disabled=gesperrt):
            st.markdown(f"**{eintrag.get('route', '')}** wirklich endgültig löschen?")
            st.caption("Das kann nicht rückgängig gemacht werden.")
            if st.button("Ja, löschen", key=f"d_{link_id}", type="primary", disabled=gesperrt):
                tracker_logik.link_loeschen(link_id)
                melde("success", f"Link '{eintrag.get('route', '')}' gelöscht.")
                st.rerun()


def typ_badges(typen):
    ausgabe = ""
    for typ in typen:
        farbe = TYP_FARBEN.get(typ, "#68A090")
        ausgabe += f"<span class='typ' style='background-color:{farbe}; color:white; padding:1px 5px; border-radius:3px; font-size:11px; margin:0 2px;'>{typ}</span>"
    return ausgabe


def pokemon_des_links(eintrag):
    """[(spieler, pokemon, infos), ...] für alle belegten Plätze eines Links."""
    liste = []
    for idx, (p_key, n_key, i_key) in enumerate([('p1', 'n1', 'i1'), ('p2', 'n2', 'i2'), ('p3', 'n3', 'i3')]):
        if eintrag.get(p_key):
            liste.append((eintrag.get(n_key) or f"S{idx+1}", eintrag.get(p_key), eintrag.get(i_key) or {}))
    return liste


def zeilen_rahmen(link_id):
    try:
        return st.container(border=True, key=f"zeile_{link_id}")
    except TypeError:  # ältere Streamlit-Version ohne key
        return st.container(border=True)


def static_kennung(eintrag):
    return " <span class='static-tag'>Static</span>" if eintrag.get("static") else ""


def pc_pokemon_html(eintrag, status):
    """Alle Pokémon eines Links in einer Zeile: Sprite, 'Trainer: Pokémon', Typen."""
    teile = []
    for spieler_name, pokemon_name, infos in pokemon_des_links(eintrag):
        bild_pfad = infos.get("bild")
        bild = f"<img src='{html.escape(bild_pfad)}' alt=''>" if bild_pfad else "<span class='pc-leer'>❓</span>"
        teile.append(f"<div class='pc-poke'>{bild}<span><b>{html.escape(spieler_name)}:</b> {html.escape(pokemon_name)}</span>"
                     f"{typ_badges(infos.get('typen') or ['Unbekannt'])}</div>")
    return f"<div class='pc-pokes pc-{status}'>{''.join(teile)}</div>"


def aktionen_menue(eintrag):
    """Kompaktes Dropdown mit allen Aktionen eines Links (statt einzelner Buttons)."""
    link_id = eintrag["id"]
    status = eintrag.get("status", "aktiv")
    with st.popover("🛠️", help="Aktionen", disabled=gesperrt):
        if status == "aktiv":
            if st.button("🏃 Verpasst", key=f"v_{link_id}", disabled=gesperrt):
                tracker_logik.status_aendern(link_id, "verpasst"); st.rerun()
        else:
            if st.button("♻️ Wieder aktiv", key=f"a_{link_id}", disabled=gesperrt):
                tracker_logik.status_aendern(link_id, "aktiv"); st.rerun()
        if status != "friedhof":
            if st.button("💀 Friedhof", key=f"f_{link_id}", disabled=gesperrt):
                tracker_logik.status_aendern(link_id, "friedhof"); st.rerun()
        else:
            if st.button("🏃 Verpasst", key=f"v2_{link_id}", disabled=gesperrt):
                tracker_logik.status_aendern(link_id, "verpasst"); st.rerun()
        if bearbeiten_fenster:
            if st.button("✏️ Bearbeiten", key=f"e_{link_id}", disabled=gesperrt):
                bearbeiten_fenster(eintrag)
        else:  # ältere Streamlit-Version ohne Fenster
            with st.expander("✏️ Bearbeiten"):
                bearbeiten_formular(eintrag)
        frage_key = f"loeschfrage_{link_id}"
        if not st.session_state.get(frage_key):
            if st.button("🗑️ Löschen", key=f"dfrage_{link_id}", disabled=gesperrt):
                st.session_state[frage_key] = True
                st.rerun()
        else:
            st.markdown(f"**{html.escape(eintrag.get('route', ''))}** wirklich endgültig löschen?")
            if st.button("Ja, löschen", key=f"d_{link_id}", type="primary", disabled=gesperrt):
                st.session_state.pop(frage_key, None)
                tracker_logik.link_loeschen(link_id)
                melde("success", f"Link '{eintrag.get('route', '')}' gelöscht.")
                st.rerun()
            if st.button("Abbrechen", key=f"dnein_{link_id}"):
                st.session_state.pop(frage_key, None)
                st.rerun()


def zeichne_zeile(eintrag, zeige_checkbox=False):
    """Kompakte Listenzeile (PC-Box, Friedhof, Verpasst): Routen-Reiter | Pokémon | Im Team | Aktionen."""
    link_id = eintrag["id"]
    status = eintrag.get("status", "aktiv")
    with zeilen_rahmen(link_id):
        spalten = spalten_mittig([1.3, 5, 1.1, 0.6] if zeige_checkbox else [1.3, 6.1, 0.6])
        with spalten[0]:
            st.markdown(f"<div class='pc-tab pc-{status}'>{html.escape(eintrag.get('route', ''))}{static_kennung(eintrag)}</div>", unsafe_allow_html=True)
        with spalten[1]:
            st.markdown(pc_pokemon_html(eintrag, status), unsafe_allow_html=True)
        if zeige_checkbox:
            with spalten[2]:
                team_key = f"team_{link_id}"
                st.session_state[team_key] = bool(eintrag.get("in_team", False))
                st.checkbox("Im Team", key=team_key, disabled=gesperrt, on_change=team_umschalten, args=(aktueller_run, link_id, team_key))
        with spalten[-1]:
            aktionen_menue(eintrag)


def slot_html(spieler_name, pokemon_name, infos):
    typen = infos.get("typen") or ["Unbekannt"]
    ring_farbe = TYP_FARBEN.get(typen[0], "#68A090")
    bild_pfad = infos.get("bild")
    bild = f"<img src='{html.escape(bild_pfad)}' alt=''>" if bild_pfad else "<span>❓</span>"
    # Gefährliche Schwächen (4× und 2×) rechts im Slot, passend zum Spiel der Level-Caps
    gruppen = tracker_logik.schwaechen(pokemon_name, GEN_NR)
    warnung = "".join(
        f"<div><b class='stufe-{int(wert)}'>{text}</b> {typ_badges(gruppen[wert])}</div>"
        for wert, text in ((4.0, "4×"), (2.0, "2×")) if gruppen.get(wert))
    schwach = (f"<div class='schwach'><span class='warn' title='Schwächen'>!</span><div>{warnung}</div></div>"
               if warnung else "")
    return (f"<div class='teamslot'><div class='ring' style='border-color:{ring_farbe};'>{bild}</div>"
            f"<div class='info'><div class='trainer'>{html.escape(spieler_name)}</div>"
            f"<div class='pname'>{html.escape(pokemon_name)}</div>{typ_badges(typen)}</div>{schwach}</div>")


def zeichne_teamslot(eintrag):
    """Link im aktiven Team im Party-Slot-Design: Kopfzeile mit Route links und den Aktionen
    (Im Team, Bearbeiten, Verpasst, Friedhof, Löschen) mittig über den Pokémon; darunter ein Slot pro Trainer."""
    link_id = eintrag["id"]
    try:
        rahmen = st.container(key=f"teamslot_{link_id}")
    except TypeError:  # sehr alte Streamlit-Version: normale Listenzeile
        zeichne_zeile(eintrag, zeige_checkbox=True)
        return
    pokes = pokemon_des_links(eintrag)
    anzahl = max(2, min(3, max(len(pokes), einst.get("anzahl_spieler", 1))))

    with rahmen:
        kopf = spalten_mittig([2, 3, 2])
        with kopf[0]:
            st.markdown(f"<div class='teamslot-route'>📍 {html.escape(eintrag.get('route', ''))}{static_kennung(eintrag)}</div>", unsafe_allow_html=True)
        with kopf[1]:
            with box_rahmen(f"teamaktionen_{link_id}"):
                zeichne_aktionen(eintrag, True, spalten_mittig([1.7, 1, 1, 1, 1]))

        for idx, spalte in enumerate(st.columns(anzahl)):
            with spalte:
                with st.container(key=f"slot_{link_id}_{idx}"):
                    inhalt = slot_html(*pokes[idx]) if idx < len(pokes) else "<div class='teamslot'></div>"
                    st.markdown(inhalt, unsafe_allow_html=True)

def zeichne_team_analyse(team_links):
    """Unter dem letzten Team-Link: pro Trainer die Typen, gegen die mehrere seiner Team-Pokémon schwach sind (2×/4×).
    Spalten wie bei den Team-Slots, damit alles bündig darunter steht."""
    anzahl = max(2, min(3, max([einst.get("anzahl_spieler", 1)] +
                               [i + 1 for e in team_links for i in range(3) if e.get(f"p{i+1}")])))
    typ_reihenfolge = list(TYPEN_REIHENFOLGE)
    with box_rahmen("teamanalyse"):
        for idx, spalte in enumerate(st.columns(anzahl)):
            pokes = [e.get(f"p{idx+1}") for e in team_links if e.get(f"p{idx+1}")]
            if not pokes:
                continue
            trainer = (einst["spieler"][idx] if idx < len(einst["spieler"]) else "") or \
                      next((e.get(f"n{idx+1}") for e in team_links if e.get(f"n{idx+1}")), "") or f"Spieler {idx+1}"
            zaehler = {}
            for p in pokes:
                for wert, typen in tracker_logik.schwaechen(p, GEN_NR).items():
                    if wert >= 2:
                        for t in typen:
                            zaehler[t] = zaehler.get(t, 0) + 1
            kritisch = sorted(((n, t) for t, n in zaehler.items() if n >= 2),
                              key=lambda x: (-x[0], typ_reihenfolge.index(x[1]) if x[1] in typ_reihenfolge else 99))[:4]
            if kritisch:
                inhalt = " ".join(f"<span class='ta-eintrag'>{typ_badges([t])}<b>{n}/{len(pokes)}</b></span>" for n, t in kritisch)
                klasse = "teamanalyse"
            else:
                inhalt = "<span class='ta-ok'>Keine gemeinsamen Schwächen</span>"
                klasse = "teamanalyse ok"
            with spalte:
                st.markdown(f"<div class='{klasse}'><span class='warn'>!</span><span class='ta-name'>{html.escape(trainer)}</span>"
                            f"<span class='ta-liste'>{inhalt}</span></div>", unsafe_allow_html=True)


# ==========================================
# 5. ÜBERSICHT & TABS ZEICHNEN
# ==========================================
def zeichne_uebersicht(alle):

    aktive = [e for e in alle if e.get("status") == "aktiv"]
    team_links = [e for e in aktive if e.get("in_team", False)]
    box_links = [e for e in aktive if not e.get("in_team", False)]
    friedhof_links = [e for e in alle if e.get("status") == "friedhof"]
    verpasst_links = [e for e in alle if e.get("status") == "verpasst"]

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
            zeichne_teamslot(e)
        if team_links:
            zeichne_team_analyse(team_links)

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


zeichne_uebersicht(daten)
