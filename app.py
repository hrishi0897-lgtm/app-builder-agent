import os
import io
import re
import zipfile
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, Response
from agent_core import CodingAgent

app = Flask(__name__)
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(os.path.join(WORKSPACE_DIR, "assets"), exist_ok=True)

initial_index = os.path.join(WORKSPACE_DIR, "index.html")
if not os.path.exists(initial_index):
    with open(initial_index, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html><html><body style='background:#0d1117;color:#8b949e;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;margin:0;'><p>No app generated yet. Send a prompt in the Chat tab!</p></body></html>")

agent = CodingAgent(workspace_dir=WORKSPACE_DIR)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/build", methods=["POST"])
def build():
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    try:
        result = agent.build_project(prompt)
        return jsonify({
            "status": "success",
            "files": result["files"],
            "asset_requests": result["asset_requests"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/upload-asset", methods=["POST"])
def upload_asset():
    slot = request.form.get("slot", "").strip()
    media_type = request.form.get("type", "photo").strip()
    file = request.files.get("file")

    if not slot or not file:
        return jsonify({"error": "Missing slot identifier or file"}), 400

    assets_dir = os.path.join(WORKSPACE_DIR, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    ext = ".mp4" if media_type == "video" else ".png"
    target_path = os.path.join(assets_dir, f"{slot}{ext}")
    file.save(target_path)

    return jsonify({"status": "success", "slot": slot, "type": media_type, "path": f"assets/{slot}{ext}"})

def send_partial_file(path):
    range_header = request.headers.get('Range', None)
    if not range_header:
        return send_from_directory(os.path.dirname(path), os.path.basename(path))

    size = os.path.getsize(path)
    byte1, byte2 = 0, None
    m = re.search(r'(\d+)-(\d*)', range_header)
    if m:
        g = m.groups()
        byte1 = int(g[0])
        if g[1]:
            byte2 = int(g[1])

    length = size - byte1
    if byte2 is not None:
        length = byte2 - byte1 + 1

    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = Response(data, 206, mimetype='video/mp4', content_type='video/mp4', direct_passthrough=True)
    rv.headers.add('Content-Range', f'bytes {byte1}-{byte1 + length - 1}/{size}')
    rv.headers.add('Accept-Ranges', 'bytes')
    return rv

@app.route("/preview/<path:filename>")
def serve_preview(filename):
    full_path = os.path.normpath(os.path.join(WORKSPACE_DIR, filename))
    if not full_path.startswith(WORKSPACE_DIR) or not os.path.exists(full_path):
        return "<!DOCTYPE html><html><body style='background:#0d1117;color:#8b949e;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;margin:0;'><p>File not created yet.</p></body></html>", 200

    if filename.endswith(('.mp4', '.webm')):
        return send_partial_file(full_path)

    return send_from_directory(WORKSPACE_DIR, filename)

@app.route("/api/files", methods=["GET"])
def get_files():
    file_tree = []
    for root, _, files in os.walk(WORKSPACE_DIR):
        for file in files:
            rel = os.path.relpath(os.path.join(root, file), WORKSPACE_DIR)
            file_tree.append(rel)
    return jsonify({"files": file_tree})

@app.route("/api/file-content", methods=["GET"])
def get_file_content():
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "Path required"}), 400
    safe_path = os.path.normpath(os.path.join(WORKSPACE_DIR, path))
    if not safe_path.startswith(WORKSPACE_DIR) or not os.path.isfile(safe_path):
        return jsonify({"error": "Invalid file path"}), 403
    with open(safe_path, "r", encoding="utf-8", errors="ignore") as f:
        return jsonify({"content": f.read()})

@app.route("/api/download-zip", methods=["GET"])
def download_zip():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(WORKSPACE_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, WORKSPACE_DIR)
                zipf.write(full_path, arcname=rel_path)
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name="project-workspace.zip"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
