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
            "\n--- AUTONOMOUS EXPERT ENGINEER & WEB RESEARCH DIRECTIVE ---\n"
            "You are a world-class principal software engineer and award-winning frontend designer (Awwwards/FWA caliber).\n"
            "You have access to Google Search grounding. Use it actively to find REAL, accurate specs, official marketing copy, design languages, and key selling points for any entity or query.\n\n"
            "--- EXECUTION & RUNTIME REQUIREMENTS ---\n"
            "- The output MUST execute natively in a browser iframe without node/npm/vite build steps.\n"
            "- If using Tailwind: <script src=\"[https://cdn.tailwindcss.com](https://cdn.tailwindcss.com)\"></script>\n"
            "- If using Lucide icons: <script src=\"[https://unpkg.com/lucide@latest](https://unpkg.com/lucide@latest)\"></script>\n"
            "- If 3D is requested:\n"
            "  * For ultra-clean 3D device showcases, import Google Model Viewer CDN:\n"
            "    <script type=\"module\" src=\"[https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js](https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js)\"></script>\n"
            "    OR build sophisticated, smooth Three.js scenes with proper studio lighting, PBR materials, antialiasing, and orbit controls (NEVER simple ugly grey untextured cubes).\n"
            "  * Alternatively, implement Apple-grade interactive CSS 3D perspective transforms with metallic sheens and dynamic lighting reflections.\n"
            "- Always ensure index.html links correctly to all CSS and JS files using relative paths.\n"
            "- Always write complete, production-grade, non-truncated code.\n\n"
            "--- STRICT ASSET & MEDIA POLICY ---\n"
            "- NEVER use random external placeholder images (NO unsplash.com, NO picsum.photos).\n"
            "- When visual media is needed that cannot be generated via code/SVG (e.g., specific product photos or screenshots):\n"
            "  1. Photos: In HTML use `<img data-asset-slot=\"<slot_name>\" src=\"assets/<slot_name>.png\" alt=\"...\">`\n"
            "  2. Videos: In HTML use `<video data-asset-slot=\"<slot_name>\" controls class=\"...\"><source src=\"assets/<slot_name>.mp4\" type=\"video/mp4\"></video>`\n"
            "  3. Declare EVERY required asset in this exact block at the very end of your response:\n\n"
            f"{bt}asset-requests\n"
            "- slot: <slot_name>\n"
            "  type: photo\n"
            "  label: <User-Friendly Name>\n"
            "  description: <Description asset needed of the>\n"
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

        print(f"[CodingAgent] Researching & generating project for: {prompt}")
        response_text = self.manager.generate_content(
            prompt=full_prompt,
            system_instruction=self.system_instruction,
            enable_search=True
        )
        written_files = extract_and_write_files(response_text, output_dir=self.workspace_dir)
        asset_requests = self._extract_asset_requests(response_text)

        return {
            "response": response_text,
            "files": written_files,
            "asset_requests": asset_requests
        }
