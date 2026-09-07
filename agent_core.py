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
            "--- STRICT IMAGE & VISUAL ASSET RULES ---\n"
            "- NEVER use random, hardcoded Unsplash photo IDs (e.g. photo-1506744038136) which show irrelevant nature/architecture photos.\n"
            "- For photos matching specific subjects (e.g. gaming, food, cars), strictly use query-driven URLs:\n"
            "  [https://images.unsplash.com/featured/](https://images.unsplash.com/featured/)?<comma,separated,topic,keywords>&auto=format&fit=crop&w=800&q=80\n"
            "  Example for Free Fire / gaming: [https://images.unsplash.com/featured/?gaming,esports,cyberpunk&auto=format&fit=crop&w=800&q=80](https://images.unsplash.com/featured/?gaming,esports,cyberpunk&auto=format&fit=crop&w=800&q=80)\n"
            "- Prefer clean inline SVGs, Lucide icons, canvas visuals, or CSS gradient placeholders over stock photos for badges, match highlights, or UI thumbnails.\n\n"
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
