from flask import Flask, render_template, request, redirect
import os
import shutil
import json
import re

app = Flask(__name__)
LIBRARY_DIR = "Library"
PROCESSED_PATHS_FILE = "processed_paths.json"

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

@app.route('/')
def index():
    folders = []
    folder_map = {}

    for root, dirs, files in os.walk(LIBRARY_DIR):
        rel_root = os.path.relpath(root, LIBRARY_DIR)
        strms = [f for f in files if f.endswith('.strm')]

        if strms:
            folders.append(rel_root)
            folder_map[rel_root] = strms

    return render_template("index.html", folders=folders, folder_map=folder_map)

@app.route('/move', methods=['POST'])
def move():
    selected = request.form.getlist("selected")
    destination = request.form.get("destination")

    data = load_processed_paths()

    for entry in selected:
        folder, filename = entry.split("||")
        src_folder = os.path.join(LIBRARY_DIR, folder)
        dst_folder = os.path.join(LIBRARY_DIR, destination)

        os.makedirs(dst_folder, exist_ok=True)

        src_path = os.path.join(src_folder, filename)
        dst_path = os.path.join(dst_folder, filename)

        if os.path.exists(src_path):
            shutil.move(src_path, dst_path)

            # actualizar JSON
            torrent_id = extract_torrent_id(folder)
            if torrent_id and torrent_id in data:
                new_rel_path = os.path.relpath(
                    os.path.join(destination, folder.split("/")[-1]),
                    start=LIBRARY_DIR
                )
                data[torrent_id] = new_rel_path

    save_processed_paths(data)
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete():
    selected = request.form.getlist("selected")
    data = load_processed_paths()

    for entry in selected:
        folder, filename = entry.split("||")
        file_path = os.path.join(LIBRARY_DIR, folder, filename)

        if os.path.exists(file_path):
            os.remove(file_path)

            # Si ya no hay más .strm en la carpeta, eliminar del JSON
            full_folder_path = os.path.join(LIBRARY_DIR, folder)
            remaining = [
                f for f in os.listdir(full_folder_path)
                if f.endswith(".strm")
            ]
            if not remaining:
                torrent_id = extract_torrent_id(folder)
                if torrent_id and torrent_id in data:
                    del data[torrent_id]

    save_processed_paths(data)
    return redirect('/')
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
