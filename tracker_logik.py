import firebase_admin
from firebase_admin import credentials, firestore
import requests
import os
import re
import streamlit as st
import json
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
# 3. DATENBANK LOGIK & PRÜFUNGEN
# ==========================================
def lade_daten(run_id):
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
        return []


def link_hinzufuegen(run_id, route, n1, p1, n2, p2, n3, p3, status):
    """Speichert neuen Link. Führt Routen- und Dupes-Checks durch (außer bei 'Static')."""
    route_raw = route.strip()
    route_suche = route_raw.lower()

    # --- DER STATIC JOKER ---
    # Wenn "static" irgendwo im Routennamen steht, überspringen wir die Checks
    is_static = "static" in route_suche

    if not is_static:
        # Lade alle Bisherigen Links aus diesem Run, um sie zu prüfen
        alle_links = db.collection("links").where("run_id", "==", run_id).stream()

        gefangene_pokemon = []
        for doc in alle_links:
            d = doc.to_dict()

            # 1. ROUTEN-CHECK
            if d.get("route", "").strip().lower() == route_suche:
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

    try:
        db.collection("links").add(neuer_link)
        return True, f"Erfolgreich gespeichert! {'(Static Bonus verwendet)' if is_static else ''}"
    except Exception as e:
        return False, f"Cloud-Fehler: {e}"


def link_bearbeiten(doc_id, alter_eintrag, route, namen, pokes):
    """Ändert Route, Spielernamen und Pokémon eines bestehenden Links
    (z.B. nach einer Entwicklung). Status und Team bleiben unverändert."""
    route_raw = (route or "").strip()
    if not route_raw:
        return False, "Die Route darf nicht leer sein."
    if not pokes or not pokes[0]:
        return False, "Spieler 1 braucht ein Pokémon."
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
        return True, "Änderung gespeichert!"
    except Exception as e:
        return False, f"Cloud-Fehler: {e}"


def status_aendern(doc_id, neuer_status):
    """Verschiebt einen Link zwischen Aktiv, Verpasst und Friedhof."""
    db.collection("links").document(doc_id).update({"status": neuer_status, "in_team": False})


def team_status_aendern(run_id, doc_id, im_team):
    """Setzt Pokémon ins Team (Check auf max 6)."""
    if im_team:
        aktuelles_team = db.collection("links").where("run_id", "==", run_id).where("in_team", "==", True).get()
        if len(aktuelles_team) >= 6:
            return False, "Team ist bereits voll (max. 6)!"
    db.collection("links").document(doc_id).update({"in_team": im_team})
    return True, "OK"


def link_loeschen(doc_id):
    """Löscht einen Eintrag komplett."""
    db.collection("links").document(doc_id).delete()

# ==========================================
# 4. RUNS & RUN-EINSTELLUNGEN
# ==========================================
# Einstellungen pro Run (Spielernamen, gewähltes Spiel, besiegte Arenen) liegen
# in einer eigenen Sammlung "runs". Die bestehenden "links" bleiben unverändert.
STANDARD_EINSTELLUNGEN = {"spieler": ["", "", ""], "anzahl_spieler": 1, "spiel": None, "besiegt": {}}


def _run_doc_id(run_id):
    return run_id.replace("/", "_") or "_"


def schluessel(text):
    """Macht aus einem Spielnamen einen sicheren Datenbank-Schlüssel."""
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def lade_runs():
    """Alle bekannten Run-Namen (aus Einträgen und gespeicherten Einstellungen)."""
    namen = set()
    try:
        for doc in db.collection("links").stream():
            r = doc.to_dict().get("run_id")
            if r:
                namen.add(r)
        for doc in db.collection("runs").stream():
            r = doc.to_dict().get("run_id")
            if r:
                namen.add(r)
    except Exception as e:
        print("Fehler beim Laden der Runs:", e)
    return sorted(namen, key=str.lower)


def lade_run_einstellungen(run_id):
    einstellungen = json.loads(json.dumps(STANDARD_EINSTELLUNGEN))
    try:
        doc = db.collection("runs").document(_run_doc_id(run_id)).get()
        if doc.exists:
            gespeichert = doc.to_dict() or {}
            for k in einstellungen:
                if k in gespeichert and gespeichert[k] is not None:
                    einstellungen[k] = gespeichert[k]
    except Exception as e:
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


def speichere_run_einstellungen(run_id, **felder):
    """Speichert einzelne Einstellungen eines Runs (andere bleiben erhalten)."""
    try:
        daten = {"run_id": run_id}
        daten.update(felder)
        db.collection("runs").document(_run_doc_id(run_id)).set(daten, merge=True)
        return True
    except Exception as e:
        print("Fehler beim Speichern der Run-Einstellungen:", e)
        return False
