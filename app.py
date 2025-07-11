import json
import os
import threading
from flask import Flask, render_template, jsonify, request
from collections import defaultdict
import re


# === CONFIG ===
POKEDEX_PATH = "pokedex_data.json"
CAUGHT_PATH = "caught_pokemon.json"

app = Flask(__name__)
lock = threading.Lock()

# Load pokedex data once at startup
with open(POKEDEX_PATH, "r", encoding="utf-8") as f:
    pokedex = json.load(f)
    
def format_sprite_name(name):
    name = name.lower()
    name = name.replace("♀", "-f").replace("♂", "-m")  # gender variants
    name = name.replace("'", "")
    name = re.sub(r"[^a-z0-9\-']", "", name.replace(" ", "-"))  # clean
    if name == "nidoran-female":
        name = "nidoran-f"
    elif name == "nidoran-male":
        name = "nidoran-m"
    return f"https://img.pokemondb.net/sprites/scarlet-violet/icon/{name}.png"

def load_caught():
    if os.path.exists(CAUGHT_PATH):
        with open(CAUGHT_PATH, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()

def save_caught(caught_set):
    with open(CAUGHT_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(list(caught_set)), f, indent=2)

def save_pokedex(updated_pokedex):
    with open(POKEDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_pokedex, f, indent=2)

def get_generation(pokemon_id):
    if 1 <= pokemon_id <= 151:
        return "1"
    elif 152 <= pokemon_id <= 251:
        return "2"
    elif 252 <= pokemon_id <= 386:
        return "3"
    elif 387 <= pokemon_id <= 493:
        return "4"
    elif 494 <= pokemon_id <= 649:
        return "5"
    elif 650 <= pokemon_id <= 721:
        return "6"
    elif 722 <= pokemon_id <= 809:
        return "7"
    elif 810 <= pokemon_id <= 905:
        return "8"
    else:
        return "9"

@app.route("/")
def index():
    caught = load_caught()
    gen_groups = defaultdict(list)
    for entry in pokedex:
        entry_copy = entry.copy()
        
        entry_copy["caught"] = entry["name"] in caught
        entry_copy["sprite_url"] = format_sprite_name(entry["name"])
        # Assume 'id' or 'number' field in pokedex contains National Dex number
        poke_id = entry.get("pokemon_id") or entry.get("number") or 0
        gen = get_generation(int(poke_id))
        gen_groups[gen].append(entry_copy)

    sorted_gens = sorted(gen_groups.items(), key=lambda x: int(x[0]))
    return render_template("index.html", generations=sorted_gens)


@app.route("/api/data")
def api_data():
    caught = load_caught()
    return jsonify({
        "caught": sorted(list(caught)),
        "total": len(caught),
        "pokedex": pokedex
    })

@app.route("/api/toggle_caught", methods=["POST"])
def toggle_caught():
    data = request.get_json()
    name = data.get("name")
    if not name:
        return jsonify({"error": "Missing name"}), 400

    with lock:
        caught = load_caught()
        # Find Pokémon in pokedex
        poke = next((p for p in pokedex if p["name"].lower() == name.lower()), None)
        if not poke:
            return jsonify({"error": "Pokemon not found"}), 404

        # Toggle caught state
        if poke["name"] in caught:
            caught.remove(poke["name"])
            poke["caught"] = False
            caught_status = False
        else:
            caught.add(poke["name"])
            poke["caught"] = True
            caught_status = True

        # Save updated files
        save_caught(caught)
        save_pokedex(pokedex)

    return jsonify({"name": poke["name"], "caught": caught_status})

if __name__ == "__main__":
    app.run(debug=True)
