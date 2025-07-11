import os
import time
import re
import json
import pyperclip
import requests

# === CONFIGURATION ===
mc_log_path = r"C:\Users\bschu\curseforge\minecraft\Instances\The Pixelmon Modpack\logs\latest.log"
cache_file = "pokemon_entries.json"
webhook_url = "https://discord.com/api/webhooks/1392945425920819335/AXwWf8pJjntgkvNBwa487Iwn6J6oWOibmZVVaCWxBFFt0gghsH8sHbzchYGSP4-BPKKz"

pokedex_data_file = "pokedex_data.json"
caught_pokemon_file = "caught_pokemon.json"

# === Regex Patterns ===
calc_pattern = re.compile(r"(\d+)\s*([+\-x/])\s*(\d+)", re.IGNORECASE)
unscramble_pattern = re.compile(r"unscramble[^'\"]*['\"]?([a-zA-Z ]+)['\"]?", re.IGNORECASE)
unreverse_pattern = re.compile(r"unreverse[^'\"]*['\"]?([a-zA-Z ]+)['\"]?", re.IGNORECASE)
type_pattern = re.compile(r"type[^'\"]*['\"]?([a-zA-Z ]+)['\"]?", re.IGNORECASE)
pokedex_trigger_pattern = re.compile(r"who'?s that pokemon", re.IGNORECASE)
entry_text_pattern = re.compile(r"[A-Za-z][^.]+\.\s?.+")
caught_pokemon_pattern = re.compile(
    r"You caught a\s+(\d)?([a-zA-Z]+?)a?\s+with\s+e?(\d+)%\s+aIVs", re.IGNORECASE
)

pokemon_list = []
pokemon_entries = {}

# === Fetch Pokémon List ===
def fetch_pokemon_names():
    global pokemon_list
    try:
        response = requests.get("https://pokeapi.co/api/v2/pokemon?limit=10000", timeout=10)
        data = response.json()
        pokemon_list = [p["name"].lower() for p in data["results"]]
        print(f"✅ Loaded {len(pokemon_list)} Pokémon names.")
    except Exception as e:
        print("❌ Failed to fetch Pokémon names:", e)

# === Load or Fetch Pokédex Entries ===
def load_or_fetch_entries():
    global pokemon_entries
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                pokemon_entries = json.load(f)
            print(f"📁 Loaded Pokédex entries from cache ({len(pokemon_entries)} entries).")
            return
        except Exception as e:
            print("⚠️ Failed to load cache, will re-fetch entries:", e)

    print("🌐 Fetching Pokédex entries from API...")
    for name in pokemon_list:
        try:
            url = f"https://pokeapi.co/api/v2/pokemon-species/{name}"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                for entry in data["flavor_text_entries"]:
                    if entry["language"]["name"] == "en":
                        text = entry["flavor_text"].replace("\n", " ").replace("\x0c", " ").lower()
                        pokemon_entries[name] = text
                        print(f"✅ Cached [{name}]: {text[:100]}...")
                        break
            time.sleep(0.1)
        except Exception as e:
            print(f"⚠️ Failed fetching {name}: {e}")
            continue

    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(pokemon_entries, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(pokemon_entries)} entries to cache.")
    except Exception as e:
        print("❌ Failed to write cache file:", e)

# === Discord Messaging ===
def send_to_discord(name, level, iv_percent):
    name_clean = name.lower()
    image_url = f"https://img.pokemondb.net/artwork/{name_clean}.jpg"
    content = f"### Koi caught a {name.capitalize()} with {iv_percent}% IVs!"

    payload = {
        "embeds": [{
            "title": f"{name.capitalize()}",
            "description": f"**IVs:** {iv_percent}%",
            "image": {"url": image_url},
            "color": 0x00ffcc
        }],
        "content": content
    }

    try:
        r = requests.post(webhook_url, json=payload, timeout=5)
        if r.status_code in (200, 204):
            print(f"📨 Sent to Discord: {content}")
        else:
            print(f"❌ Discord error {r.status_code}: {r.text}")
    except Exception as e:
        print("❌ Failed to send to Discord:", e)

# === Helpers ===
def normalize(word):
    return ''.join(sorted(word.lower()))

def unscramble(scrambled):
    target = normalize(scrambled)
    for name in pokemon_list:
        if normalize(name) == target:
            return name
    return None

def calculate(a, op, b):
    a, b = int(a), int(b)
    if op == '+': return a + b
    elif op == '-': return a - b
    elif op == 'x': return a * b
    elif op == '/':
        return round(a / b, 4) if b != 0 else "Error: Div by 0"
    return None

def guess_pokemon_from_text(snippet):
    snippet_words = set(re.findall(r"\w+", snippet.lower()))
    best_match = None
    best_score = 0
    for name, entry in pokemon_entries.items():
        entry_words = set(re.findall(r"\w+", entry))
        score = len(snippet_words.intersection(entry_words))
        if score > best_score:
            best_score = score
            best_match = name
    return best_match

def scroll_logs(logfile):
    logfile.seek(0, 2)
    while True:
        line = logfile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line.strip()

# === JSON Load/Save Helpers for pokedex and caught list ===
def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_pokedex_and_caught(name):
    name_lower = name.title()
    
    # Load pokedex_data and caught_pokemon
    pokedex_data = load_json(pokedex_data_file)
    caught_pokemon = load_json(caught_pokemon_file)

    updated = False

    # Update caught flag in pokedex_data
    for entry in pokedex_data:
        if entry.get("name", "").lower() == name_lower:
            if not entry.get("caught", False):
                entry["caught"] = True
                updated = True
            break
    else:
        # Optional: handle missing pokemon in pokedex_data
        print(f"⚠️ Pokémon '{name}' not found in pokedex_data.")

    # Add to caught_pokemon list if not already present
    if name not in caught_pokemon:
        caught_pokemon.append(name)
        updated = True

    if updated:
        save_json(pokedex_data_file, pokedex_data)
        save_json(caught_pokemon_file, caught_pokemon)
        print(f"💾 Updated pokedex_data and caught_pokemon for {name}.")

# === Main ===
def main():
    fetch_pokemon_names()
    load_or_fetch_entries()

    try:
        with open(mc_log_path, "r", encoding='utf-8', errors='ignore') as logfile:
            print(f"\n🔍 Watching: {mc_log_path}")
            pokedex_mode = False
            entry_candidate = ""

            for line in scroll_logs(logfile):
                print(f"> {line}")

                # Pokédex challenge
                if pokedex_trigger_pattern.search(line):
                    pokedex_mode = True
                    entry_candidate = ""
                    print("🔎 Pokédex challenge detected. Waiting for entry...")
                    continue

                if pokedex_mode:
                    match = entry_text_pattern.search(line)
                    if match:
                        entry_candidate = match.group(0)
                        pyperclip.copy(entry_candidate.strip())
                        print(f"📖 Pokédex Entry: \"{entry_candidate.strip()}\" → Copied")
                        pokedex_mode = False
                    continue

                # Math
                match = calc_pattern.search(line)
                if match:
                    a, op, b = match.groups()
                    result = calculate(a, op, b)
                    pyperclip.copy(str(result))
                    print(f"➗ Math: {a} {op} {b} = {result} → Copied")
                    continue

                # Unscramble
                match = unscramble_pattern.search(line)
                if match:
                    scrambled = match.group(1).replace(" ", "")
                    result = unscramble(scrambled)
                    if result:
                        pyperclip.copy(result)
                        print(f"🔤 Unscrambled: '{scrambled}' → {result} → Copied")
                    else:
                        print(f"❌ Could not unscramble: '{scrambled}'")
                    continue

                # Unreverse
                match = unreverse_pattern.search(line)
                if match:
                    reversed_word = match.group(1).replace(" ", "")
                    attempt = reversed_word[::-1].lower()
                    if attempt in pokemon_list:
                        pyperclip.copy(attempt)
                        print(f"🔁 Unreversed: '{reversed_word}' → '{attempt}' → Copied")
                    else:
                        print(f"❌ Unreversed '{reversed_word}' → '{attempt}' not found")
                    continue

                # Type challenge
                match = type_pattern.search(line)
                if match:
                    word = match.group(1).replace(" ", "").lower()
                    pyperclip.copy(word)
                    print(f"⌨️  Type Challenge: '{word}' → Copied")
                    continue

                # Caught Pokémon
                match = caught_pokemon_pattern.search(line)
                if match:
                    level = match.group(1) or "?"
                    name = match.group(2).rstrip().lower()
                    ivs = match.group(3)
                    send_to_discord(name, level, ivs)
                    
                    # Update pokedex_data and caught_pokemon JSON files
                    update_pokedex_and_caught(name)
                    continue

    except FileNotFoundError:
        print("❌ Log file not found. Check the path.")
    except KeyboardInterrupt:
        print("\n🛑 Stopped watching log.")
    except Exception as e:
        print("❌ Error:", e)

# === Run ===
if __name__ == "__main__":
    main()
