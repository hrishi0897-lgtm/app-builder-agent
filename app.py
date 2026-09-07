import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from agent_core import CodingAgent

app = Flask(__name__)
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(os.path.join(WORKSPACE_DIR, "assets"), exist_ok=True)

# Create an initial index.html if empty so preview never 404s
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
    file = request.files.get("file")

    if not slot or not file:
        return jsonify({"error": "Missing slot identifier or file"}), 400

    assets_dir = os.path.join(WORKSPACE_DIR, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    target_path = os.path.join(assets_dir, f"{slot}.png")
    file.save(target_path)

    return jsonify({"status": "success", "slot": slot, "path": f"assets/{slot}.png"})

@app.route("/preview/<path:filename>")
def serve_preview(filename):
    if not os.path.exists(os.path.join(WORKSPACE_DIR, filename)):
        return "<!DOCTYPE html><html><body style='background:#0d1117;color:#8b949e;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;margin:0;'><p>File not created yet.</p></body></html>", 200
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
