import firebase_admin

# Bei jeder Änderung an dieser Datei erhöhen UND in web_app.py anpassen.
# So erkennt die Web-App, wenn Streamlit noch eine alte Version im Speicher hat.
MODUL_VERSION = 15
from firebase_admin import credentials, firestore
import requests
import os
import re
import streamlit as st
import json
import hashlib
import hmac
import math
import threading
import time
import copy
from pathlib import Path

# ==========================================
# 1. INITIALISIERUNG (Cloud & Lokal)
# ==========================================
if not firebase_admin._apps:
    if "firebase" in st.secrets:
        secret_dict = json.loads(st.secrets["firebase"]["text"])
        cred = credentials.Certificate(secret_dict)
    else:
        script_dir = Path(__file__).parent.absolute()
        key_file = script_dir / "firebase_key.json"
        if not key_file.exists():
            key_file = script_dir / "firebase_key.json.json"
        cred = credentials.Certificate(str(key_file))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================================
# 2. POKÉMON-DATEN (lokal, ohne Wartezeit)
# ==========================================
# pokemon_daten.json enthält alle Pokémon mit deutschem Namen, Typen und
# Entwicklungsreihe (Quelle: PokeAPI). Dadurch braucht das Speichern keine
# langsamen API-Abfragen mehr. Für Namen, die dort fehlen, gibt es weiterhin
# die alte API-Abfrage als Rückfallebene (mit Zeitlimit).
TYP_UEBERSETZUNG = {
    "normal": "Normal", "fire": "Feuer", "water": "Wasser", "electric": "Elektro",
    "grass": "Pflanze", "ice": "Eis", "fighting": "Kampf", "poison": "Gift",
    "ground": "Boden", "flying": "Flug", "psychic": "Psycho", "bug": "Käfer",
    "rock": "Gestein", "ghost": "Geist", "dragon": "Drache", "dark": "Unlicht",
    "steel": "Stahl", "fairy": "Fee"
}

SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{}.png"
API_TIMEOUT = 5


def _lade_pokedex():
    pfad = Path(__file__).parent.absolute() / "pokemon_daten.json"
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Pokémon-Daten konnten nicht geladen werden:", e)
        return []


POKEDEX = _lade_pokedex()
_NACH_NAME = {p["name"].lower(): p for p in POKEDEX}
_NACH_KETTE = {}
for _p in POKEDEX:
    _NACH_KETTE.setdefault(_p["kette"], []).append(_p["name"].lower())


def alle_pokemon_namen():
    """Alle deutschen Pokémon-Namen in Pokédex-Reihenfolge (für die Auswahlfelder)."""
    return [p["name"] for p in POKEDEX]


def finde_pokemon(name):
    if not name:
        return None
    return _NACH_NAME.get(name.strip().lower())


def _api_evolutions_familie(pokemon_name):
    """Alte API-Abfrage – nur noch Rückfallebene für unbekannte Namen."""
    url = "https://beta.pokeapi.co/graphql/v1beta"
    query = """
    query GetEvolution($name: String!) {
      pokemon_v2_pokemonspecies(where: {pokemon_v2_pokemonspeciesnames: {name: {_ilike: $name}, language_id: {_eq: 6}}}) {
        pokemon_v2_evolutionchain {
          pokemon_v2_pokemonspecies {
            pokemon_v2_pokemonspeciesnames(where: {language_id: {_eq: 6}}) {
              name
            }
          }
        }
      }
    }
    """
    try:
        response = requests.post(url, json={'query': query, 'variables': {"name": pokemon_name}}, timeout=API_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            species_list = data['data']['pokemon_v2_pokemonspecies']
            if species_list and species_list[0]['pokemon_v2_evolutionchain']:
                familie = species_list[0]['pokemon_v2_evolutionchain']['pokemon_v2_pokemonspecies']
                return [m['pokemon_v2_pokemonspeciesnames'][0]['name'].lower() for m in familie if m['pokemon_v2_pokemonspeciesnames']]
    except Exception as e:
        print("Fehler beim Abrufen der Evolutionen:", e)
    return [pokemon_name.lower()]


def _familie_lokal(pokemon_name):
    """Entwicklungsreihe nur aus den lokalen Daten (ohne Internet)."""
    eintrag = finde_pokemon(pokemon_name)
    if eintrag:
        return list(_NACH_KETTE.get(eintrag["kette"], [pokemon_name.strip().lower()]))
    return [pokemon_name.strip().lower()]


def gleiche_reihe(a, b):
    """True, wenn a und b dasselbe Pokémon oder dieselbe Entwicklungsreihe sind."""
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower() or b.strip().lower() in _familie_lokal(a)


def doppelte_im_link(pokes):
    """Prüft, ob im selben Link zweimal dasselbe Pokémon (bzw. dieselbe Reihe) steht.
    Gibt eine Fehlermeldung zurück oder None."""
    liste = [p.strip() for p in pokes if p and p.strip()]
    for i, a in enumerate(liste):
        for b in liste[i + 1:]:
            if a.lower() == b.lower():
                return f"⚠️ {a} steht zweimal in diesem Link – jeder Trainer braucht ein anderes Pokémon! (Bei Static-Geschenken 'Static' zur Route schreiben)"
            if gleiche_reihe(a, b):
                return f"⚠️ {a} und {b} sind dieselbe Entwicklungsreihe – das geht nicht im selben Link! (Bei Static-Geschenken 'Static' zur Route schreiben)"
    return None


def vergebene_pokemon(daten):
    """Welche Pokémon wegen der Dupes Clause schon gesperrt sind.
    Gibt {name_klein: bereits_gehabtes_pokemon} zurück – gleiche Regel wie beim Speichern
    (alle Links des Runs zählen, egal ob aktiv, Friedhof oder verpasst)."""
    gesperrt = {}
    for d in daten:
        for k in ("p1", "p2", "p3"):
            p = (d.get(k) or "").strip()
            if not p:
                continue
            gesperrt.setdefault(p.lower(), p)
            for mitglied in _familie_lokal(p):
                gesperrt.setdefault(mitglied, p)
    return gesperrt


def hole_evolutions_familie(pokemon_name):
    """Holt alle deutschen Namen der gesamten Evolutionsreihe eines Pokémon."""
    if not pokemon_name:
        return []
    pokemon_name = pokemon_name.strip()
    eintrag = finde_pokemon(pokemon_name)
    if eintrag:
        return list(_NACH_KETTE.get(eintrag["kette"], [pokemon_name.lower()]))
    return _api_evolutions_familie(pokemon_name)


def _api_pokemon_infos(pokemon_name):
    """Alte API-Abfrage – nur noch Rückfallebene für unbekannte Namen."""
    url = "https://beta.pokeapi.co/graphql/v1beta"
    query = """
    query GetPokemon($name: String!) {
      pokemon_v2_pokemonspecies(where: {pokemon_v2_pokemonspeciesnames: {name: {_ilike: $name}, language_id: {_eq: 6}}}) {
        name
      }
    }
    """
    zusatz_infos = {"bild": "", "typen": ["Unbekannt"]}
    try:
        response = requests.post(url, json={'query': query, 'variables': {"name": pokemon_name}}, timeout=API_TIMEOUT)
        if response.status_code == 200:
            gefundene_pokemon = response.json()['data']['pokemon_v2_pokemonspecies']
            if gefundene_pokemon:
                en_name = gefundene_pokemon[0]['name']
                res = requests.get(f"https://pokeapi.co/api/v2/pokemon/{en_name}", timeout=API_TIMEOUT)
                if res.status_code == 200:
                    p_data = res.json()
                    sprite_url = p_data['sprites']['front_default']
                    typen = [TYP_UEBERSETZUNG.get(t['type']['name'], "Unbekannt") for t in p_data['types']]
                    zusatz_infos = {"bild": sprite_url if sprite_url else "", "typen": typen}
    except Exception:
        pass
    return zusatz_infos


def hole_pokemon_infos(pokemon_name):
    """Holt Bild und Typ für das Pokémon."""
    if not pokemon_name:
        return {"bild": "", "typen": ["Unbekannt"]}
    eintrag = finde_pokemon(pokemon_name)
    if eintrag:
        return {"bild": SPRITE_URL.format(eintrag["id"]), "typen": eintrag["typen"] or ["Unbekannt"]}
    return _api_pokemon_infos(pokemon_name.strip())

# ==========================================
# 2a. TYPEN & SCHWÄCHEN (je nach Generation)
# ==========================================
# typen_tabelle.json (Quelle: PokeAPI): Effektivität aktuell + frühere Abweichungen (z.B. Gen 1, Stahl bis Gen 5)
def _lade_typen_tabelle():
    try:
        with open(Path(__file__).parent.absolute() / "typen_tabelle.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Typen-Tabelle konnte nicht geladen werden:", e)
        return {"einfuehrung": {}, "faktor": {}, "alt": []}


TYPEN_TABELLE = _lade_typen_tabelle()


def generation_aus_spiel(spielname):
    """'Gen 4: Platin' -> 4. Unbekannt -> None (dann gilt die aktuelle Typen-Tabelle)."""
    m = re.match(r"\s*Gen\s*(\d+)", spielname or "")
    return int(m.group(1)) if m else None


def typen_fuer(pokemon_name, generation=None):
    """Typen eines Pokémon in einer bestimmten Generation (z.B. Piepi bis Gen 5: Normal statt Fee)."""
    p = finde_pokemon(pokemon_name)
    if not p:
        return []
    if generation:
        for bis_gen, typen in p.get("typen_alt", []):
            if generation <= bis_gen:
                return list(typen)
    return list(p.get("typen") or [])


def _faktor(angriff, ziel, generation):
    wert = TYPEN_TABELLE["faktor"].get(angriff, {}).get(ziel, 1.0)
    if generation:
        passende = [e for e in TYPEN_TABELLE["alt"] if e[1] == angriff and e[2] == ziel and generation <= e[0]]
        if passende:
            wert = min(passende, key=lambda e: e[0])[3]
    return wert


def schwaechen(pokemon_name, generation=None):
    """Schaden aller Angriffstypen gegen das Pokémon: {4.0: [...], 2.0: [...], 1.0: [...], 0.5: [...], 0.25: [...], 0.0: [...]}.
    Nur Typen, die es in der Generation gibt."""
    verteidiger = typen_fuer(pokemon_name, generation)
    if not verteidiger:
        return {}
    gruppen = {}
    for angriff, eingefuehrt in TYPEN_TABELLE["einfuehrung"].items():
        if generation and eingefuehrt > generation:
            continue
        gesamt = 1.0
        for ziel in verteidiger:
            gesamt *= _faktor(angriff, ziel, generation)
        gruppen.setdefault(gesamt, []).append(angriff)
    return gruppen

# ==========================================
# 2b. FANGCHANCE-RECHNER (Gen 1–5)
# ==========================================
# Jede Generation hat ihre eigene Fangmechanik (siehe _fang_gen1, _fang_gen2, _fang_gen34, _fang_gen5).
# Grundlage: die Mechanik-Beschreibungen auf dragonflycave.com (Gen I, II, III/IV, V).
FANG_SPIELE = ["Gen 1", "Gen 2", "Gen 3", "Gen 4 (DPPt)", "HGSS", "Gen 5"]
_G34 = ["Gen 3", "Gen 4 (DPPt)", "HGSS"]

# Schlüssel: (Anzeigename, in welchen Spielen verfügbar)
BAELLE = {
    "poke": ("Pokéball", FANG_SPIELE), "super": ("Superball", FANG_SPIELE), "hyper": ("Hyperball", FANG_SPIELE),
    "meister": ("Meisterball", FANG_SPIELE), "safari": ("Safariball", ["Gen 1"] + _G34),
    "netz": ("Netzball", _G34 + ["Gen 5"]), "tauch": ("Tauchball", _G34 + ["Gen 5"]), "nest": ("Nestball", _G34 + ["Gen 5"]),
    "wieder": ("Wiederball", _G34 + ["Gen 5"]), "timer": ("Timerball", _G34 + ["Gen 5"]),
    "luxus": ("Luxusball", _G34 + ["Gen 5"]), "premier": ("Premierball", _G34 + ["Gen 5"]),
    "finster": ("Finsterball", ["Gen 4 (DPPt)", "HGSS", "Gen 5"]), "heil": ("Heilball", ["Gen 4 (DPPt)", "HGSS", "Gen 5"]),
    "flott": ("Flottball", ["Gen 4 (DPPt)", "HGSS", "Gen 5"]), "jubel": ("Jubelball", ["Gen 4 (DPPt)", "HGSS", "Gen 5"]),
    "park": ("Parkball", ["Gen 4 (DPPt)", "HGSS"]), "park2": ("Parkball (Käferturnier)", ["Gen 2"]),
    "turbo": ("Turboball", ["Gen 2", "HGSS"]), "schwer": ("Schwerball", ["Gen 2", "HGSS"]), "level": ("Levelball", ["Gen 2", "HGSS"]),
    "koeder": ("Köderball", ["Gen 2", "HGSS"]), "mond": ("Mondball", ["Gen 2", "HGSS"]), "freund": ("Freundesball", ["Gen 2", "HGSS"]),
    "sympa": ("Sympaball", ["Gen 2", "HGSS"]), "turnier": ("Turnierball", ["HGSS"]), "traum": ("Traumball", ["Gen 5"]),
}
STATUS_LISTE = ["Kein Status", "Schlaf", "Gefroren", "Paralyse", "Vergiftet", "Verbrennung"]
STATUS_FAKTOR10 = {"Kein Status": 10, "Schlaf": 20, "Gefroren": 20, "Paralyse": 15, "Vergiftet": 15, "Verbrennung": 15}
_MOND_FAMILIEN = ["Nidoran♀", "Nidoran♂", "Piepi", "Pummeluff", "Eneco"]
_TURBO_GEN2 = ["sleima", "tangela", "magnetilo"]  # Gen-2-Bug: Turboball wirkt nur bei diesen drei


def baelle_fuer(spiel):
    return [k for k, (_, spiele) in BAELLE.items() if spiel in spiele]


def _kp_max_gen12(basis_kp, level, dv=8):
    """KP in Gen 1/2 (mit DV statt IV, ohne Stat-Exp)."""
    return ((basis_kp + dv) * 2 * level) // 100 + level + 10


def _kp_max_ab_gen3(basis_kp, level, iv=15):
    return ((2 * basis_kp + iv) * level) // 100 + level + 10


def _kp_aktuell(kp_max, kp_prozent, eins_kp):
    return 1 if eins_kp else max(1, min(kp_max, round(kp_max * kp_prozent / 100)))


def _fang_gen1(p, ball, kp_prozent, status, ziel_level, eins_kp):
    # Zufallsbereich je Ball, Status-Wert S, KP-Faktor F; geschlossene Formel der Wahrscheinlichkeit
    bereich = {"super": 201, "hyper": 151, "safari": 151}.get(ball, 256)
    s = 25 if status in ("Schlaf", "Gefroren") else 12 if status != "Kein Status" else 0
    m = _kp_max_gen12(p["kp"], ziel_level)
    h = _kp_aktuell(m, kp_prozent, eins_kp)
    f = (m * 255) // (8 if ball == "super" else 12)
    f = min(255, f // max(1, h // 4))
    c = p["fangrate"]
    chance = (s + min(c + 1, bereich - s) * (f + 1) / 256) / bereich
    return min(1.0, chance), f


def _fang_gen2(p, ball, kp_prozent, status, ziel_level, eins_kp, angeln, eigenes_level, liebe):
    r = p["fangrate"]
    name = p["name"].lower()
    if ball == "super" or ball == "park2":
        c = (r * 15) // 10
    elif ball == "hyper":
        c = r * 2
    elif ball == "turbo":
        c = r * 4 if name in _TURBO_GEN2 else r
    elif ball == "schwer":
        g = p.get("gewicht", 0)
        c = r + (40 if g >= 409.6 else 30 if g >= 307.2 else 20 if g >= 204.8 else 0 if g >= 102.4 else -20)
    elif ball == "sympa":
        c = r * 8 if liebe else r   # Gen-2-Bug: wirkt bei GLEICHEM Geschlecht
    elif ball == "koeder":
        c = r * 3 if angeln else r
    else:                            # Pokéball, Freundesball, Mondball (Bug: wirkt nicht)
        c = r
    if ball == "level":
        c = r
        if eigenes_level:
            if eigenes_level // 4 > ziel_level:
                c = r * 8
            elif eigenes_level // 2 > ziel_level:
                c = r * 4
            elif eigenes_level > ziel_level:
                c = r * 2
        x = max(1, min(255, c))     # Levelball überspringt die KP-Rechnung
        return (x + 1) / 256, x
    c = max(1, min(255, c))
    m = _kp_max_gen12(p["kp"], ziel_level)
    h = _kp_aktuell(m, kp_prozent, eins_kp)
    a, b = 3 * m, 2 * h
    if a > 255:                      # Spiel teilt beide durch 4, damit es in 8 Bit passt
        a, b = a // 4, b // 4
    x = max(((a - b) * c) // a, 1) + (10 if status in ("Schlaf", "Gefroren") else 0)
    x = min(255, x)
    return (x + 1) / 256, x


def _fang_gen34(p, ball, kp_prozent, status, ziel_level, eins_kp, runde, nacht_hoehle, wasser,
                schon_gefangen, angeln, eigenes_level, liebe, iv):
    # X = ((3*KPmax - 2*KP) * (Fangrate * Ball)) / (3*KPmax) * Status, nach jedem Schritt abgerundet.
    c = p["fangrate"]
    if ball == "turbo" and p.get("init", 0) >= 100:
        c *= 4
    elif ball == "schwer":
        g = p.get("gewicht", 0)
        c += 40 if g >= 409.6 else 30 if g >= 307.2 else 20 if g >= 204.8 else -20
    elif ball == "level" and eigenes_level:
        if eigenes_level // 4 > ziel_level:
            c *= 8
        elif eigenes_level // 2 > ziel_level:
            c *= 4
        elif eigenes_level > ziel_level:
            c *= 2
    elif ball == "sympa" and liebe:
        c *= 8
    elif ball == "koeder" and angeln:
        c *= 3
    elif ball == "mond" and any(p["name"].lower() in _familie_lokal(n) for n in _MOND_FAMILIEN):
        c *= 4
    c = max(1, min(255, c))

    b10 = {"super": 15, "hyper": 20, "safari": 15, "turnier": 15}.get(ball, 10)
    if ball == "netz" and any(t in ("Wasser", "Käfer") for t in p.get("typen", [])):
        b10 = 30
    elif ball == "nest":
        b10 = max(10, 40 - ziel_level)
    elif ball == "tauch" and wasser:
        b10 = 35
    elif ball == "wieder" and schon_gefangen:
        b10 = 30
    elif ball == "timer":
        b10 = min(40, 10 + max(0, runde - 1))
    elif ball == "flott" and runde == 1:
        b10 = 40
    elif ball == "finster" and nacht_hoehle:
        b10 = 35

    kp_max = _kp_max_ab_gen3(p["kp"], ziel_level, iv)
    kp = _kp_aktuell(kp_max, kp_prozent, eins_kp)
    x = ((3 * kp_max - 2 * kp) * ((c * b10) // 10)) // (3 * kp_max)
    x = (x * STATUS_FAKTOR10.get(status, 10)) // 10
    x = max(1, x)
    if x >= 255:
        return 1.0, x
    y = 1048560 // math.isqrt(math.isqrt(16711680 // x))
    return min(1.0, (y / 65536) ** 4), x


def _runter(x):   # Gen 5 rechnet in 1/4096-Schritten
    return math.floor(x * 4096) / 4096


def _runden(x):
    return math.floor(x * 4096 + 0.5) / 4096


def _fang_gen5(p, ball, kp_prozent, status, ziel_level, eins_kp, runde, nacht_hoehle, wasser,
               schon_gefangen, dichtes_gras, pokedex, fangkraft, iv):
    c = p["fangrate"]
    b = {"super": 1.5, "hyper": 2}.get(ball, 1)
    if ball == "netz" and any(t in ("Wasser", "Käfer") for t in p.get("typen", [])):
        b = 3
    elif ball == "nest":
        b = max(1, min(4, (41 - ziel_level) / 10))
    elif ball == "tauch" and wasser:
        b = 3.5
    elif ball == "wieder" and schon_gefangen:
        b = 3
    elif ball == "timer":
        b = min(4, 1 + max(0, runde - 1) * 1229 / 4096)
    elif ball == "flott" and runde == 1:
        b = 5
    elif ball == "finster" and nacht_hoehle:
        b = 3.5

    if dichtes_gras:
        g = (1 if pokedex > 600 else 3686 / 4096 if pokedex > 450 else 3277 / 4096 if pokedex > 300
             else 2867 / 4096 if pokedex > 150 else 0.5 if pokedex > 30 else 1229 / 4096)
    else:
        g = 1
    s = 2.5 if status in ("Schlaf", "Gefroren") else 1.5 if status != "Kein Status" else 1
    e = {0: 100, 1: 110, 2: 120, 3: 130}.get(fangkraft, 100)

    m = _kp_max_ab_gen3(p["kp"], ziel_level, iv)
    h = _kp_aktuell(m, kp_prozent, eins_kp)
    x = _runter(_runden(_runter(_runden(_runden((3 * m - 2 * h) * g) * c * b) / (3 * m)) * s) * e / 100)
    if x >= 255:
        return 1.0, x
    if x <= 0:
        return 0.0, x
    y = math.floor(65536 / math.sqrt(math.sqrt(255 / x))) / 65536
    pk = (2.5 if pokedex > 600 else 2 if pokedex > 450 else 1.5 if pokedex > 300
          else 1 if pokedex > 150 else 0.5 if pokedex > 30 else 0)
    kritisch = math.floor(min(255, x) * pk / 6) / 256   # kritischer Fang: nur eine Schüttel-Prüfung
    return min(1.0, kritisch * y + (1 - kritisch) * y ** 3), x


def fangchance(pokemon_name, ball, kp_prozent, status, ziel_level, spiel, eins_kp=False, runde=1,
               nacht_hoehle=False, wasser=False, schon_gefangen=False, angeln=False, eigenes_level=None,
               liebe=False, dichtes_gras=False, pokedex=0, fangkraft=0, iv=15):
    """Fangchance pro Wurf (0..1) nach der Mechanik der gewählten Generation.
    KP werden mit durchschnittlichen IVs/DVs geschätzt. Gibt (chance, x_wert) zurück,
    oder (None, None), wenn das Pokémon unbekannt ist."""
    p = finde_pokemon(pokemon_name)
    if not p or "fangrate" not in p:
        return None, None
    if ball == "meister" or (ball == "park" and spiel in _G34):
        return 1.0, 255
    if spiel == "Gen 1":
        return _fang_gen1(p, ball, kp_prozent, status, ziel_level, eins_kp)
    if spiel == "Gen 2":
        return _fang_gen2(p, ball, kp_prozent, status, ziel_level, eins_kp, angeln, eigenes_level, liebe)
    if spiel == "Gen 5":
        return _fang_gen5(p, ball, kp_prozent, status, ziel_level, eins_kp, runde, nacht_hoehle, wasser,
                          schon_gefangen, dichtes_gras, pokedex, fangkraft, iv)
    return _fang_gen34(p, ball, kp_prozent, status, ziel_level, eins_kp, runde, nacht_hoehle, wasser,
                       schon_gefangen, angeln, eigenes_level, liebe, iv)


def wuerfe_fuer(chance, ziel=0.9):
    """Wie viele Würfe man braucht, um mit z.B. 90 % Wahrscheinlichkeit zu fangen."""
    if chance >= 1:
        return 1
    if chance <= 0:
        return None
    return math.ceil(math.log(1 - ziel) / math.log(1 - chance))

# ==========================================
# 3. DATENBANK LOGIK & PRÜFUNGEN
# ==========================================
# Nach jedem Schreibzugriff werden diese Funktionen aufgerufen (die Web-App leert damit ihren
# Zwischenspeicher, damit sofort wieder frische Daten angezeigt werden).
NACH_SCHREIBEN = []


def _geschrieben(art=None):
    """art: "links" (nur Einträge geändert), "einstellungen" (nur Run-Einstellungen) oder None (alles)."""
    for rueckruf in list(NACH_SCHREIBEN):
        try:
            rueckruf(art)
        except Exception as e:
            print("Zwischenspeicher konnte nicht geleert werden:", e)


# ---------- Mitgeführter Zwischenspeicher für die Links eines Runs ----------
# Die Links eines Runs werden einmal aus Firebase gelesen und danach im Arbeitsspeicher der App
# mitgeführt: Jede Änderung wird ZUERST in Firebase geschrieben und danach hier nachgetragen.
# Dadurch kostet Eintragen, Team, Friedhof usw. keine Lesevorgänge mehr. Der Speicher gilt für
# alle Besucher gemeinsam; spätestens nach LINK_CACHE_TTL Sekunden wird frisch aus Firebase gelesen
# (falls jemand direkt in der Firebase-Konsole etwas ändert). Schlägt ein Schreibzugriff fehl,
# wird der Speicher verworfen und beim nächsten Zugriff neu geladen.
LINK_CACHE_TTL = 600
_CACHE_SPERRE = threading.RLock()
_LINK_CACHE = {}  # run_id -> {"zeit": Zeitpunkt des Ladens, "links": {doc_id: Eintrag}}


def _cache_links(run_id):
    """Die mitgeführten Links eines Runs (lädt bei Bedarf aus Firebase). Nur unter _CACHE_SPERRE benutzen."""
    eintrag = _LINK_CACHE.get(run_id)
    if eintrag and time.time() - eintrag["zeit"] < LINK_CACHE_TTL:
        return eintrag["links"]
    links = {}
    for doc in db.collection("links").where("run_id", "==", run_id).stream():
        d = doc.to_dict()
        d["id"] = doc.id
        links[doc.id] = d
    _LINK_CACHE[run_id] = {"zeit": time.time(), "links": links}
    return links


def lade_daten_cache(run_id):
    """Alle Links eines Runs aus dem Zwischenspeicher (gleiche Reihenfolge wie Firebase: nach Dokument-ID)."""
    with _CACHE_SPERRE:
        links = _cache_links(run_id)
        return [copy.deepcopy(links[k]) for k in sorted(links)]


def cache_verwerfen(run_id=None):
    """Zwischenspeicher eines Runs (oder aller) leeren -> nächster Zugriff liest frisch aus Firebase."""
    with _CACHE_SPERRE:
        if run_id is None:
            _LINK_CACHE.clear()
        else:
            _LINK_CACHE.pop(run_id, None)


def _cache_nachtragen(doc_id, felder=None, loeschen=False):
    """Trägt eine erfolgreich gespeicherte Änderung im Zwischenspeicher nach."""
    with _CACHE_SPERRE:
        for eintrag in _LINK_CACHE.values():
            if doc_id in eintrag["links"]:
                if loeschen:
                    del eintrag["links"][doc_id]
                else:
                    eintrag["links"][doc_id].update(copy.deepcopy(felder))
                return


def _cache_run_von(doc_id):
    with _CACHE_SPERRE:
        for run_id, eintrag in _LINK_CACHE.items():
            if doc_id in eintrag["links"]:
                return run_id
    return None


def lade_daten(run_id, fehler_werfen=False):
    """Lädt alle Daten für die Web-App Anzeige."""
    try:
        docs = db.collection("links").where("run_id", "==", run_id).stream()
        liste = []
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            liste.append(d)
        return liste
    except Exception as e:
        if fehler_werfen:
            raise
        return []


def link_hinzufuegen(run_id, route, n1, p1, n2, p2, n3, p3, status, static=False):
    """Speichert neuen Link. Führt Routen- und Dupes-Checks durch (außer bei 'Static').
    Prüfen und Speichern laufen am Stück, damit zwei gleichzeitige Einträge sich nicht überholen."""
    with _CACHE_SPERRE:
        return _link_hinzufuegen(run_id, route, n1, p1, n2, p2, n3, p3, status, static)


def _link_hinzufuegen(run_id, route, n1, p1, n2, p2, n3, p3, status, static=False):
    route_raw = route.strip()
    route_suche = route_raw.lower()

    # --- DER STATIC JOKER ---
    # Static-Häkchen gesetzt ODER "static" irgendwo im Routennamen -> Checks überspringen
    is_static = bool(static) or "static" in route_suche

    if not is_static:
        # 0. GLEICHES POKÉMON IM SELBEN LINK?
        fehler = doppelte_im_link([p1, p2, p3])
        if fehler:
            return False, fehler

        # Alle bisherigen Links dieses Runs prüfen (aus dem mitgeführten Zwischenspeicher)
        try:
            alle_links = lade_daten_cache(run_id)
        except Exception as e:
            return False, f"Cloud-Fehler: {e}"

        gefangene_pokemon = []
        for d in alle_links:

            # 1. ROUTEN-CHECK (Static-Links belegen keine Route)
            if not d.get("static") and d.get("route", "").strip().lower() == route_suche:
                return False, f"📍 Fehler: Die Route '{route_raw}' existiert bereits! (Schreib 'Static' dazu, um dies zu ignorieren)"

            # Sammle ALLE Pokémon aus diesem Link (egal ob aktiv, friedhof, verpasst)
            if d.get("p1"): gefangene_pokemon.append(d.get("p1").lower().strip())
            if d.get("p2"): gefangene_pokemon.append(d.get("p2").lower().strip())
            if d.get("p3"): gefangene_pokemon.append(d.get("p3").lower().strip())

        # 2. DUPES CLAUSE CHECK
        neue_pokes = [p for p in [p1, p2, p3] if p]
        for neu_p in neue_pokes:
            name_clean = neu_p.lower().strip()

            # Schneller Direkt-Check (Gibt es den Namen exakt so schon?)
            if name_clean in gefangene_pokemon:
                return False, f"⚠️ Dupes Clause! '{neu_p}' hattet ihr bereits! (Schreib 'Static' zur Route, um dies zu ignorieren)"

            # Evolutions-Check (Gibt es Pichu/Raichu, wenn ich Pikachu eintrage?)
            familie = hole_evolutions_familie(neu_p)
            for fam_mitglied in familie:
                if fam_mitglied in gefangene_pokemon:
                    return False, f"⚠️ Dupes Clause! Ihr hattet bereits ein {fam_mitglied.capitalize()} (Reihe von {neu_p})!"

    # 3. Wenn alle Checks bestanden sind -> Lade Bilder und speichere
    pokemon_infos = [
        hole_pokemon_infos(p1) if p1 else None,
        hole_pokemon_infos(p2) if p2 else None,
        hole_pokemon_infos(p3) if p3 else None
    ]

    neuer_link = {
        "run_id": run_id,
        "route": route_raw,
        "n1": n1, "p1": p1, "i1": pokemon_infos[0],
        "n2": n2, "p2": p2, "i2": pokemon_infos[1],
        "n3": n3, "p3": p3, "i3": pokemon_infos[2],
        "status": "aktiv" if status == "Gefangen" else "verpasst",
        "in_team": False
    }
    if static:
        neuer_link["static"] = True

    try:
        _, ref = db.collection("links").add(neuer_link)
        with _CACHE_SPERRE:
            if run_id in _LINK_CACHE:
                _LINK_CACHE[run_id]["links"][ref.id] = dict(copy.deepcopy(neuer_link), id=ref.id)
        _geschrieben("links")
        # Run im Run-Verzeichnis sicherstellen (falls er z.B. nur über die Adresse geöffnet wurde)
        try:
            db.collection("runs").document(_run_doc_id(run_id)).set({"run_id": run_id}, merge=True)
        except Exception as e:
            print("Run-Verzeichnis konnte nicht aktualisiert werden:", e)
        return True, f"Erfolgreich gespeichert! {'(Static Bonus verwendet)' if is_static else ''}"
    except Exception as e:
        cache_verwerfen(run_id)
        return False, f"Cloud-Fehler: {e}"


def link_bearbeiten(doc_id, alter_eintrag, route, namen, pokes):
    """Ändert Route, Spielernamen und Pokémon eines bestehenden Links
    (z.B. nach einer Entwicklung). Status und Team bleiben unverändert."""
    route_raw = (route or "").strip()
    if not route_raw:
        return False, "Die Route darf nicht leer sein."
    if not pokes or not pokes[0]:
        return False, "Spieler 1 braucht ein Pokémon."
    if "static" not in route_raw.lower() and not alter_eintrag.get("static"):
        fehler = doppelte_im_link(pokes)
        if fehler:
            return False, fehler
    update = {"route": route_raw}
    for i in range(3):
        nr = i + 1
        name = namen[i] if i < len(namen) else ""
        poke = pokes[i] if i < len(pokes) else ""
        update[f"n{nr}"] = name or ""
        update[f"p{nr}"] = poke or ""
        if not poke:
            update[f"i{nr}"] = None
        elif poke != alter_eintrag.get(f"p{nr}") or not alter_eintrag.get(f"i{nr}"):
            update[f"i{nr}"] = hole_pokemon_infos(poke)
    try:
        db.collection("links").document(doc_id).update(update)
        _cache_nachtragen(doc_id, update)
        _geschrieben("links")
        return True, "Änderung gespeichert!"
    except Exception as e:
        cache_verwerfen(_cache_run_von(doc_id))
        return False, f"Cloud-Fehler: {e}"


def status_aendern(doc_id, neuer_status):
    """Verschiebt einen Link zwischen Aktiv, Verpasst und Friedhof."""
    felder = {"status": neuer_status, "in_team": False}
    try:
        db.collection("links").document(doc_id).update(felder)
        _cache_nachtragen(doc_id, felder)
    except Exception:
        cache_verwerfen(_cache_run_von(doc_id))
        raise
    finally:
        _geschrieben("links")


def team_status_aendern(run_id, doc_id, im_team):
    """Setzt Pokémon ins Team (Check auf max 6)."""
    with _CACHE_SPERRE:  # Prüfen und Setzen zusammen, damit zwei gleichzeitige Klicks nicht 7 ergeben
        if im_team:
            im_team_jetzt = sum(1 for l in lade_daten_cache(run_id) if l.get("in_team") and l.get("id") != doc_id)
            if im_team_jetzt >= 6:
                return False, "Team ist bereits voll (max. 6)!"
        try:
            db.collection("links").document(doc_id).update({"in_team": im_team})
            _cache_nachtragen(doc_id, {"in_team": im_team})
        except Exception:
            cache_verwerfen(run_id)
            raise
        finally:
            _geschrieben("links")
    return True, "OK"


def link_loeschen(doc_id):
    """Löscht einen Eintrag komplett."""
    try:
        db.collection("links").document(doc_id).delete()
        _cache_nachtragen(doc_id, loeschen=True)
    except Exception:
        cache_verwerfen(_cache_run_von(doc_id))
        raise
    finally:
        _geschrieben("links")

# ==========================================
# 4. RUNS & RUN-EINSTELLUNGEN
# ==========================================
# Einstellungen pro Run (Spielernamen, gewähltes Spiel, besiegte Arenen) liegen
# in einer eigenen Sammlung "runs". Die bestehenden "links" bleiben unverändert.
STANDARD_EINSTELLUNGEN = {"spieler": ["", "", ""], "anzahl_spieler": 1, "spiel": None, "besiegt": {},
                          "pw_hash": None, "pw_salt": None, "design": "gbc"}


def _run_doc_id(run_id):
    return run_id.replace("/", "_") or "_"


def schluessel(text):
    """Macht aus einem Spielnamen einen sicheren Datenbank-Schlüssel."""
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def _runs_einmalig_eintragen():
    """Einmalige Umstellung: Jeder Run bekommt einen kleinen Eintrag in "runs".
    Danach muss die Run-Liste nie wieder alle Links durchlesen (spart Firebase-Lesevorgänge)."""
    if db.collection("meta").document("runs_verzeichnis").get().exists:
        return
    vorhandene = set()
    for doc in db.collection("runs").stream():
        r = doc.to_dict().get("run_id")
        if r:
            vorhandene.add(r)
    for doc in db.collection("links").stream():
        r = doc.to_dict().get("run_id")
        if r and r not in vorhandene:
            db.collection("runs").document(_run_doc_id(r)).set({"run_id": r}, merge=True)
            vorhandene.add(r)
    db.collection("meta").document("runs_verzeichnis").set({"erledigt": True})


def lade_runs():
    """Alle Run-Namen – liest nur einen kleinen Eintrag pro Run, nicht alle Links."""
    namen = set()
    try:
        _runs_einmalig_eintragen()
        for doc in db.collection("runs").stream():
            r = doc.to_dict().get("run_id")
            if r:
                namen.add(r)
    except Exception as e:
        print("Fehler beim Laden der Runs:", e)
    return sorted(namen, key=str.lower)


def lade_run_einstellungen(run_id, fehler_werfen=False):
    einstellungen = json.loads(json.dumps(STANDARD_EINSTELLUNGEN))
    try:
        doc = db.collection("runs").document(_run_doc_id(run_id)).get()
        if doc.exists:
            gespeichert = doc.to_dict() or {}
            for k in einstellungen:
                if k in gespeichert and gespeichert[k] is not None:
                    einstellungen[k] = gespeichert[k]
    except Exception as e:
        if fehler_werfen:
            raise
        print("Fehler beim Laden der Run-Einstellungen:", e)
    spieler = list(einstellungen.get("spieler") or [])
    einstellungen["spieler"] = (spieler + ["", "", ""])[:3]
    try:
        einstellungen["anzahl_spieler"] = max(1, min(3, int(einstellungen.get("anzahl_spieler") or 1)))
    except (TypeError, ValueError):
        einstellungen["anzahl_spieler"] = 1
    if not isinstance(einstellungen.get("besiegt"), dict):
        einstellungen["besiegt"] = {}
    return einstellungen


# ---------- Passwortschutz pro Run ----------
# Gespeichert wird nur ein Hash (nie das Passwort selbst). Nach der Eingabe bekommt
# der Browser einen "Schlüssel" (abgeleitet vom Hash), der in der Adresse steht und
# beim Neuladen erhalten bleibt. Ändert sich das Passwort, wird der alte Schlüssel ungültig.
def _passwort_hash(passwort, salt):
    return hashlib.pbkdf2_hmac("sha256", passwort.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()


def run_geschuetzt(einstellungen):
    return bool(einstellungen.get("pw_hash"))


def freigabe_schluessel(run_id, einstellungen):
    """Schlüssel, der nach korrekter Passworteingabe in der Adresse gespeichert wird."""
    if not run_geschuetzt(einstellungen):
        return None
    return hashlib.sha256(f"{run_id}|{einstellungen['pw_hash']}".encode("utf-8")).hexdigest()[:24]


def pruefe_passwort(run_id, einstellungen, passwort):
    """Gibt bei richtigem Passwort den Freigabe-Schlüssel zurück, sonst None."""
    if not run_geschuetzt(einstellungen) or not passwort:
        return None
    versuch = _passwort_hash(passwort, einstellungen.get("pw_salt") or "")
    if hmac.compare_digest(versuch, einstellungen["pw_hash"]):
        return freigabe_schluessel(run_id, einstellungen)
    return None


def pruefe_schluessel(run_id, einstellungen, schluessel):
    erwartet = freigabe_schluessel(run_id, einstellungen)
    return bool(erwartet and schluessel and hmac.compare_digest(erwartet, str(schluessel)))


def run_passwort_setzen(run_id, passwort):
    """Setzt (oder ändert) das Passwort eines Runs. Gibt den neuen Freigabe-Schlüssel zurück."""
    salt = os.urandom(16).hex()
    pw_hash = _passwort_hash(passwort, salt)
    if not speichere_run_einstellungen(run_id, pw_hash=pw_hash, pw_salt=salt):
        return None
    return freigabe_schluessel(run_id, {"pw_hash": pw_hash})


def run_loeschen(run_id):
    """Löscht einen kompletten Run: alle seine Links und seine Einstellungen.
    Andere Runs bleiben unberührt. Gibt (erfolg, anzahl_geloeschter_links) zurück."""
    anzahl = 0
    try:
        for doc in db.collection("links").where("run_id", "==", run_id).stream():
            db.collection("links").document(doc.id).delete()
            anzahl += 1
        db.collection("runs").document(_run_doc_id(run_id)).delete()
        return True, anzahl
    except Exception as e:
        print("Fehler beim Löschen des Runs:", e)
        return False, anzahl
    finally:
        cache_verwerfen(run_id)
        _geschrieben()


def speichere_run_einstellungen(run_id, **felder):
    """Speichert einzelne Einstellungen eines Runs (andere bleiben erhalten)."""
    try:
        daten = {"run_id": run_id}
        daten.update(felder)
        db.collection("runs").document(_run_doc_id(run_id)).set(daten, merge=True)
        _geschrieben("einstellungen")
        return True
    except Exception as e:
        print("Fehler beim Speichern der Run-Einstellungen:", e)
        return False
