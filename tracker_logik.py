import firebase_admin
from firebase_admin import credentials, firestore
import requests
import os
import streamlit as st
import json

# ==========================================
# 1. INITIALISIERUNG (Cloud & Lokal)
# ==========================================
if not firebase_admin._apps:
    if "firebase" in st.secrets:
        secret_dict = json.loads(st.secrets["firebase"]["text"])
        cred = credentials.Certificate(secret_dict)
    else:
        from pathlib import Path
        script_dir = Path(__file__).parent.absolute()
        key_file = script_dir / "firebase_key.json"
        if not key_file.exists():
            key_file = script_dir / "firebase_key.json.json"
        cred = credentials.Certificate(str(key_file))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================================
# 2. POKÉMON API & GRAPHQL LOGIK
# ==========================================
TYP_UEBERSETZUNG = {
    "normal": "Normal", "fire": "Feuer", "water": "Wasser", "electric": "Elektro",
    "grass": "Pflanze", "ice": "Eis", "fighting": "Kampf", "poison": "Gift",
    "ground": "Boden", "flying": "Flug", "psychic": "Psycho", "bug": "Käfer",
    "rock": "Gestein", "ghost": "Geist", "dragon": "Drache", "dark": "Unlicht",
    "steel": "Stahl", "fairy": "Fee"
}

def hole_evolutions_familie(pokemon_name):
    """Holt alle deutschen Namen der gesamten Evolutionsreihe eines Pokémon."""
    if not pokemon_name: return []
    pokemon_name = pokemon_name.strip()
    url = "https://beta.pokeapi.co/graphql/v1beta"
    
    # GraphQL Abfrage, die direkt die ganze Kette sucht
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
        response = requests.post(url, json={'query': query, 'variables': {"name": pokemon_name}}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            species_list = data['data']['pokemon_v2_pokemonspecies']
            if species_list and species_list[0]['pokemon_v2_evolutionchain']:
                # Extrahiere alle Namen aus der Kette
                familie = species_list[0]['pokemon_v2_evolutionchain']['pokemon_v2_pokemonspecies']
                namen = [mitglied['pokemon_v2_pokemonspeciesnames'][0]['name'].lower() for mitglied in familie if mitglied['pokemon_v2_pokemonspeciesnames']]
                return namen
    except Exception as e:
        print("Fehler beim Abrufen der Evolutionen:", e)
    
    return [pokemon_name.lower()] # Fallback, falls die API streikt

def hole_pokemon_infos(pokemon_name):
    """Holt Bild und Typ für das Pokémon."""
    if not pokemon_name: return {"bild": "", "typen": ["Unbekannt"]}
    pokemon_name = pokemon_name.strip()
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
        response = requests.post(url, json={'query': query, 'variables': {"name": pokemon_name}})
        if response.status_code == 200:
            data = response.json()
            gefundene_pokemon = data['data']['pokemon_v2_pokemonspecies']
            if gefundene_pokemon:
                en_name = gefundene_pokemon[0]['name']
                res = requests.get(f"https://pokeapi.co/api/v2/pokemon/{en_name}")
                if res.status_code == 200:
                    p_data = res.json()
                    sprite_url = p_data['sprites']['front_default']
                    typen = [TYP_UEBERSETZUNG.get(t['type']['name'], "Unbekannt") for t in p_data['types']]
                    zusatz_infos = {"bild": sprite_url if sprite_url else "", "typen": typen}
    except Exception as e:
        pass
    return zusatz_infos

# ==========================================
# 3. DATENBANK LOGIK (Mit Dupes Clause!)
# ==========================================
def lade_daten(run_id):
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
    """Speichert einen neuen Link (inkl. Check auf Route & Entwicklungen)."""
    
    # 1. CHECK: Wurde die Route schon in diesem Run gespielt?
    # Wir laden die Route und machen sie "klein" zum besseren Vergleichen
    route_suche = route.strip().lower()
    alle_links = db.collection("links").where("run_id", "==", run_id).get()
    
    gefangene_pokemon = [] # Sammelt alle Pokémon (inkl. Friedhof), verpasste ignorieren wir für Dupes oft.
    
    for doc in alle_links:
        d = doc.to_dict()
        # Routen-Check
        if d.get("route", "").strip().lower() == route_suche:
            return False, f"Fehler: Die Route '{route}' wurde bereits eingetragen!"
        
        # Sammle alle bisher gefangenen/toten Pokémon für den Dupes-Check
        if d.get("status") in ["aktiv", "friedhof"]:
            if d.get("p1"): gefangene_pokemon.append(d.get("p1").lower().strip())
            if d.get("p2"): gefangene_pokemon.append(d.get("p2").lower().strip())
            if d.get("p3"): gefangene_pokemon.append(d.get("p3").lower().strip())

    # 2. CHECK: Dupes Clause (Evolutionsreihe)
    # Nur checken, wenn das Pokémon "Gefangen" wird (bei Verpasst greift Dupes oft nicht)
    if status == "Gefangen":
        neue_pokes = [p for p in [p1, p2, p3] if p]
        for neu_p in neue_pokes:
            familie = hole_evolutions_familie(neu_p) # Holt z.B. ["pichu", "pikachu", "raichu"]
            for fam_mitglied in familie:
                if fam_mitglied in gefangene_pokemon:
                    # Wenn das gesuchte Pkm oder eine Entwicklung schon da ist -> BLOCKIEREN
                    return False, f"Dupes Clause! Du hast bereits ein {fam_mitglied.capitalize()} (Entwicklungsreihe von {neu_p}) gefangen!"

    # 3. Wenn alles passt -> Lade Bilder und speichere
    pokemon_infos = [
        hole_pokemon_infos(p1) if p1 else None,
        hole_pokemon_infos(p2) if p2 else None,
        hole_pokemon_infos(p3) if p3 else None
    ]

    neuer_link = {
        "run_id": run_id,
        "route": route,
        "n1": n1, "p1": p1, "i1": pokemon_infos[0],
        "n2": n2, "p2": p2, "i2": pokemon_infos[1],
        "n3": n3, "p3": p3, "i3": pokemon_infos[2],
        "status": "aktiv" if status == "Gefangen" else "verpasst",
        "in_team": False
    }

    try:
        db.collection("links").add(neuer_link)
        return True, "Erfolgreich in Cloud gespeichert!"
    except Exception as e:
        return False, f"Cloud-Fehler: {e}"

def status_aendern(doc_id, neuer_status):
    db.collection("links").document(doc_id).update({"status": neuer_status, "in_team": False})

def team_status_aendern(run_id, doc_id, im_team):
    if im_team:
        aktuelles_team = db.collection("links").where("run_id", "==", run_id).where("in_team", "==", True).get()
        if len(aktuelles_team) >= 6:
            return False, "Team ist bereits voll (max. 6)!"
    db.collection("links").document(doc_id).update({"in_team": im_team})
    return True, "OK"

def link_loeschen(doc_id):
    db.collection("links").document(doc_id).delete()
