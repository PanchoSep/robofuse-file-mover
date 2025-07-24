from flask import Flask, render_template, request, redirect
import os
import shutil
import json
import re
import sys

os.makedirs("/app/logs", exist_ok=True)
sys.stdout = open("/app/logs/strm.log", "a", buffering=1)
sys.stderr = sys.stdout

app = Flask(__name__)
app.debug = True
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
    print(f"[DEBUG] Intentando extraer ID desde: {folder_name}")
    match = re.search(r"\[([a-zA-Z0-9]{6,20})\]", folder_name)
    return match.group(1) if match else None

def get_strm_folders():
    """Devuelve una lista de dicts: cada uno con folder + nombre de archivo dentro del .strm"""
    strm_folders = []

    for root, dirs, files in os.walk(LIBRARY_DIR):
        strm_files = [f for f in files if f.endswith('.strm')]
        if strm_files:
            rel_path = os.path.relpath(root, LIBRARY_DIR)
            first_strm = os.path.join(root, strm_files[0])
            filename_inside = extract_strm_filename(first_strm)

            strm_folders.append({
                "folder": rel_path,
                "file_name": filename_inside or "¿vacío?"
            })

    return sorted(strm_folders, key=lambda x: x["folder"])

def get_possible_destinations(strm_folders):
    """Devuelve un set con los niveles superiores disponibles para mover"""
    destinations = set()

    for folder in strm_folders:
        parts = folder.split(os.sep)
        for i in range(1, len(parts)):
            prefix = os.path.join(*parts[:i])
            destinations.add(prefix)

    return sorted(destinations)
    
def extract_strm_filename(strm_path):
    if not os.path.exists(strm_path):
        return None
    try:
        with open(strm_path, "r") as f:
            url = f.read().strip()
            return os.path.basename(url)
    except Exception as e:
        return f"⚠️ Error leyendo .strm: {e}"
        
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
    
@app.route('/logs')
def logs():
    log_file = "/app/logs/strm.log"
    if not os.path.exists(log_file):
        return "Log vacío o no creado aún."

    with open(log_file, "r") as f:
        lines = f.readlines()

    # Solo mostrar las últimas 100 líneas
    last_lines = lines[-100:] if len(lines) > 100 else lines
    return "<pre>" + "".join(last_lines) + "</pre>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
