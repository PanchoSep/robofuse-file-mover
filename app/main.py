from flask import Flask, render_template, request, redirect
import os
import shutil
import json
import re

app = Flask(__name__)
LIBRARY_DIR = "Library"
PROCESSED_PATHS_FILE = "Library/processed_paths.json"

def load_processed_paths():
    if os.path.exists(PROCESSED_PATHS_FILE):
        with open(PROCESSED_PATHS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_processed_paths(data):
    with open(PROCESSED_PATHS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def extract_torrent_id(folder_name):
    match = re.search(r"\[([A-Z0-9]{12})\]", folder_name)
    return match.group(1) if match else None

def get_strm_folders():
    """Retorna una lista de carpetas que contienen al menos un archivo .strm"""
    strm_folders = []

    for root, dirs, files in os.walk(LIBRARY_DIR):
        if any(f.endswith('.strm') for f in files):
            rel_path = os.path.relpath(root, LIBRARY_DIR)
            strm_folders.append(rel_path)

    return sorted(strm_folders)

def get_possible_destinations(strm_folders):
    """Devuelve un set con los niveles superiores disponibles para mover"""
    destinations = set()

    for folder in strm_folders:
        parts = folder.split(os.sep)
        for i in range(1, len(parts)):
            prefix = os.path.join(*parts[:i])
            destinations.add(prefix)

    return sorted(destinations)

@app.route('/')
def index():
    strm_folders = get_strm_folders()
    destination_folders = get_possible_destinations(strm_folders)

    return render_template(
        "index.html",
        strm_folders=strm_folders,
        destination_folders=destination_folders
    )

@app.route('/move', methods=['POST'])
def move():
    selected = request.form.getlist("selected")
    destination = request.form.get("destination")

    data = load_processed_paths()

    for rel_path in selected:
        src_path = os.path.join(LIBRARY_DIR, rel_path)
        dst_root = os.path.join(LIBRARY_DIR, destination)
        dst_path = os.path.join(dst_root, os.path.basename(src_path))  # evita duplicación

        if os.path.exists(src_path):
            os.makedirs(dst_root, exist_ok=True)
            shutil.move(src_path, dst_path)

            torrent_id = extract_torrent_id(os.path.basename(src_path))
            print(f"[DEBUG] Extraído ID: {torrent_id}")
            print(f"[DEBUG] Existe en JSON: {torrent_id in data}")
            print(f"[DEBUG] Claves actuales: {list(data.keys())}")
            
            if torrent_id and torrent_id in data:
                new_rel = os.path.relpath(dst_path, LIBRARY_DIR)
                data[torrent_id] = new_rel
                print(f"✔️ Actualizado {torrent_id} → {new_rel}")

    save_processed_paths(data)
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete():
    selected = request.form.getlist("selected")
    data = load_processed_paths()

    for rel_path in selected:
        full_path = os.path.join(LIBRARY_DIR, rel_path)
        folder_name = os.path.basename(rel_path)

        if os.path.exists(full_path):
            shutil.rmtree(full_path)

            torrent_id = extract_torrent_id(folder_name)
            if torrent_id and torrent_id in data:
                del data[torrent_id]

    save_processed_paths(data)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
