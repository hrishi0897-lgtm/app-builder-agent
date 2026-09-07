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
            "- Always provide complete, non-truncated production-ready code.\n\n"
            "--- STRICT ZERO-BROKEN-IMAGE POLICY ---\n"
            "- DO NOT use '[images.unsplash.com/featured/](https://images.unsplash.com/featured/)?...' (it returns 404).\n"
            "- For gaming, avatars, banners, cards, and video thumbnails, PREFER procedural designs:\n"
            "  * Rich CSS radial/linear gradients with glowing borders and Lucide icons.\n"
            "  * Clean inline SVG artwork, HUD badges, or geometric gaming frames.\n"
            "- If external photos are necessary, use: [https://picsum.photos/seed/](https://picsum.photos/seed/)<subject-keyword>/800/500\n"
            "- ALWAYS attach an onerror handler to every <img> tag to gracefully fallback without broken icons:\n"
            "  onerror=\"this.onerror=null; this.src='[https://picsum.photos/800/500?grayscale](https://picsum.photos/800/500?grayscale)';\"\n\n"
            "Output all files using this exact block format:\n\n"
            f"{bt}<language> file=<relative_path>\n<file_contents>\n{bt}\n\n"
            "Example format:\n"
            f"{bt}html file=index.html\n<!DOCTYPE html>\n...{bt}\n"
            f"{bt}css file=css/style.css\n...{bt}\n"
            f"{bt}js file=js/app.js\n...{bt}\n"
        )
        return f"{taste_rules}\n\n{multi_file_spec}"

    def build_project(self, prompt):
        print(f"[CodingAgent] Generating browser-ready project for: {prompt}")
        response_text = self.manager.generate_content(
            prompt=prompt,
            system_instruction=self.system_instruction
        )
        written_files = extract_and_write_files(response_text, output_dir=self.workspace_dir)
        return {
            "response": response_text,
            "files": written_files
        }
