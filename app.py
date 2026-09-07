import os
import io
import zipfile
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from agent_core import CodingAgent

app = Flask(__name__)
WORKSPACE_DIR = os.path.abspath("workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

agent = CodingAgent(workspace_dir=WORKSPACE_DIR)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    try:
        result = agent.build_project(prompt)
        return jsonify({
            "status": "success",
            "files": result["files"],
            "raw_response": result["response"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/preview/")
@app.route("/preview/<path:filename>")
def preview_file(filename="index.html"):
    file_path = os.path.join(WORKSPACE_DIR, filename)
    if os.path.exists(file_path):
        return send_from_directory(WORKSPACE_DIR, filename)
    return "<h3>Workspace is empty or file not found. Generate a project first.</h3>", 404

@app.route("/api/files", methods=["GET"])
def list_files():
    file_list = []
    for root, _, files in os.walk(WORKSPACE_DIR):
        for f in files:
            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, WORKSPACE_DIR)
            file_list.append(rel_p)
    return jsonify({"files": sorted(file_list)})

@app.route("/api/file-content", methods=["GET"])
def get_file_content():
    rel_path = request.args.get("path", "").strip()
    full_path = os.path.join(WORKSPACE_DIR, rel_path)
    if not os.path.commonpath([WORKSPACE_DIR, full_path]) == WORKSPACE_DIR:
        return jsonify({"error": "Access denied"}), 403
    if not os.path.exists(full_path):
        return jsonify({"error": "File not found"}), 404
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"content": content, "path": rel_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/file")
def download_file():
    rel_path = request.args.get("path", "").strip()
    full_path = os.path.join(WORKSPACE_DIR, rel_path)
    if not os.path.commonpath([WORKSPACE_DIR, full_path]) == WORKSPACE_DIR or not os.path.exists(full_path):
        return "File not found", 404
    return send_file(full_path, as_attachment=True)

@app.route("/download/zip")
def download_zip():
    mem_file = io.BytesIO()
    with zipfile.ZipFile(mem_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(WORKSPACE_DIR):
            for f in files:
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, WORKSPACE_DIR)
                zf.write(abs_path, rel_path)
    mem_file.seek(0)
    return send_file(mem_file, mimetype="application/zip", as_attachment=True, download_name="project.zip")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
