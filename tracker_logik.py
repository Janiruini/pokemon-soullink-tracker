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
    # Checken, ob wir in der Streamlit Cloud sind (Secrets vorhanden)
    if "firebase" in st.secrets:
        # Daten aus den Streamlit Secrets laden
        secret_dict = json.loads(st.secrets["firebase"]["text"])
        cred = credentials.Certificate(secret_dict)
    else:
        # Lokal: Suche nach der Datei (Rettungsanker für deinen PC)
        from pathlib import Path
        script_dir = Path(__file__).parent.absolute()
        key_file = script_dir / "firebase_key.json"
        
        if not key_file.exists():
            key_file = script_dir / "firebase_key.json.json"
            
        cred = credentials.Certificate(str(key_file))
    
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Standard-Run Name (können wir später über die Web-App änderbar machen)
AKTUELLER_RUN = "Standard_Run"

# ==========================================
# 2. FUNKTIONEN
# ==========================================

def lade_daten():
    """Lädt alle Links für den aktuellen Spielstand aus Firebase."""
    try:
        # Wir holen nur Dokumente, die zum aktuellen Run gehören
        docs = db.collection("links").where("run_id", "==", AKTUELLER_RUN).stream()
        liste = []
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id # Firebase ID für späteres Löschen/Update merken
            liste.append(d)
        return liste
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return []

TYP_UEBERSETZUNG = {
    "normal": "Normal", "fire": "Feuer", "water": "Wasser", "electric": "Elektro",
    "grass": "Pflanze", "ice": "Eis", "fighting": "Kampf", "poison": "Gift",
    "ground": "Boden", "flying": "Flug", "psychic": "Psycho", "bug": "Käfer",
    "rock": "Gestein", "ghost": "Geist", "dragon": "Drache", "dark": "Unlicht",
    "steel": "Stahl", "fairy": "Fee"
}

def hole_pokemon_infos(pokemon_name):
    """Sucht über GraphQL nach dem deutschen Namen und holt die Daten."""
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
                # Jetzt holen wir Sprite und Typen über den englischen Namen
                res = requests.get(f"https://pokeapi.co/api/v2/pokemon/{en_name}")
                
                if res.status_code == 200:
                    p_data = res.json()
                    sprite_url = p_data['sprites']['front_default']
                    typen = [TYP_UEBERSETZUNG.get(t['type']['name'], "Unbekannt") for t in p_data['types']]
                    zusatz_infos = {"bild": sprite_url if sprite_url else "", "typen": typen}
                    
    except Exception as e:
        print("API Fehler:", e)
        
    return zusatz_infos

def link_hinzufuegen(route, n1, p1, n2, p2, n3, p3, status):
    """Speichert einen neuen Link in der Cloud (mit GraphQL-Power!)."""
    pokemon_infos = [
        hole_pokemon_infos(p1) if p1 else None,
        hole_pokemon_infos(p2) if p2 else None,
        hole_pokemon_infos(p3) if p3 else None
    ]

    neuer_link = {
        "run_id": AKTUELLER_RUN,
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
    """Ändert den Status (z.B. zu Friedhof)."""
    db.collection("links").document(doc_id).update({"status": neuer_status, "in_team": False})

def team_status_aendern(doc_id, im_team):
    """Setzt ein Pokémon ins Team oder in die Box."""
    if im_team:
        # Check ob Team voll ist
        aktuelles_team = db.collection("links").where("run_id", "==", AKTUELLER_RUN).where("in_team", "==", True).get()
        if len(aktuelles_team) >= 6:
            return False, "Team ist bereits voll (max. 6)!"
    
    db.collection("links").document(doc_id).update({"in_team": im_team})
    return True, "OK"

def link_loeschen(doc_id):
    """Löscht einen Eintrag endgültig."""
    db.collection("links").document(doc_id).delete()
