import os
import re
from gemini_manager import GeminiManager
from project_parser import extract_and_write_files
from skills_loader import get_design_system_instruction

class CodingAgent:
    def __init__(self, workspace_dir="workspace"):
        self.workspace_dir = workspace_dir
        self.manager = GeminiManager()
        self.system_instruction = self._build_system_instruction()

    def _build_system_instruction(self):
        taste_rules = get_design_system_instruction()
        bt = "```"
        multi_file_spec = (
            "\n--- BROWSER RUNTIME & MULTI-FILE CODE FORMAT RULES ---\n"
            "You are an expert autonomous software engineer and frontend designer.\n"
            "CRITICAL: The output MUST execute natively in a browser iframe without node/npm/vite build steps.\n\n"
            "- Do NOT import uncompiled `.jsx`, `.tsx`, or `.vue` files into `<script src=...>`.\n"
            "- If using Tailwind, include the Tailwind CDN script: <script src=\"[https://cdn.tailwindcss.com](https://cdn.tailwindcss.com)\"></script>\n"
            "- If icons are needed, use Lucide icons CDN: <script src=\"[https://unpkg.com/lucide@latest](https://unpkg.com/lucide@latest)\"></script>\n"
            "- If 3D is needed, use Three.js CDN: <script src=\"[https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js](https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js)\"></script>\n"
            "- Always ensure index.html links correctly to your CSS and JS files using relative paths.\n"
            "- Always provide complete, non-truncated production-ready code for all files.\n\n"
            "--- STRICT ASSET & MEDIA POLICY ---\n"
            "- ABSOLUTELY NEVER use external placeholder links (NO unsplash.com, NO picsum.photos, NO placeholder.com).\n"
            "- When visual media is needed that cannot be made with inline SVG/CSS gradients (e.g. personal avatars, match clutch recordings, game gameplay clips):\n"
            "  1. Photos: In HTML use `<img data-asset-slot=\"<slot_name>\" src=\"assets/<slot_name>.png\" alt=\"...\">`\n"
            "  2. Videos: In HTML use `<video data-asset-slot=\"<slot_name>\" controls class=\"...\"><source src=\"assets/<slot_name>.mp4\" type=\"video/mp4\"></video>`\n"
            "  3. Declare EVERY required asset in this exact block at the very end of your response, specifying type as either 'photo' or 'video':\n\n"
            f"{bt}asset-requests\n"
            "- slot: <slot_name>\n"
            "  type: photo\n"
            "  label: <User-Friendly Name>\n"
            "  description: <Description image needed of the>\n"
            "- slot: <slot_name_2>\n"
            "  type: video\n"
            "  label: <User-Friendly Name>\n"
            "  description: <Description clip gameplay highlight of or the video>\n"
            f"{bt}\n\n"
            "Output all project files using this standard block format:\n\n"
            f"{bt}<language> file=<relative_path>\n<file_contents>\n{bt}\n"
        )
        return f"{taste_rules}\n\n{multi_file_spec}"

    def _read_existing_workspace(self):
        existing_files = {}
        if not os.path.exists(self.workspace_dir):
            return existing_files

        for root, _, files in os.walk(self.workspace_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.workspace_dir)
                if rel_path.startswith("assets/"):
                    continue
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        existing_files[rel_path] = f.read()
                except Exception:
                    pass
        return existing_files

    def _extract_asset_requests(self, response_text):
        pattern = r"```asset-requests\s*(.*?)\s*```"
        match = re.search(pattern, response_text, re.DOTALL)
        requests = []
        if match:
            raw = match.group(1).strip()
            current = {}
            for line in raw.split("\n"):
                line = line.strip()
                if line.startswith("- slot:"):
                    if current and "slot" in current:
                        requests.append(current)
                    current = {"slot": line.replace("- slot:", "").strip(), "type": "photo"}
                elif line.startswith("type:"):
                    current["type"] = line.replace("type:", "").strip().lower()
                elif line.startswith("label:"):
                    current["label"] = line.replace("label:", "").strip()
                elif line.startswith("description:"):
                    current["description"] = line.replace("description:", "").strip()
            if current and "slot" in current:
                requests.append(current)
        return requests

    def build_project(self, prompt):
        existing_files = self._read_existing_workspace()

        if existing_files:
            bt = "```"
            files_context = "\n\n".join(
                [f"File: `{p}`\n{bt}\n{c}\n{bt}" for p, c in existing_files.items()]
            )
            full_prompt = (
                f"### CURRENT WORKSPACE FILES:\n{files_context}\n\n"
                f"### USER REQUEST:\n{prompt}\n\n"
                "Apply the modifications requested by the user. If photos or videos are needed, declare them in ```asset-requests```."
            )
        else:
            full_prompt = prompt

        response_text = self.manager.generate_content(
            prompt=full_prompt,
            system_instruction=self.system_instruction
        )
        written_files = extract_and_write_files(response_text, output_dir=self.workspace_dir)
        asset_requests = self._extract_asset_requests(response_text)

        return {
            "response": response_text,
            "files": written_files,
            "asset_requests": asset_requests
        }
