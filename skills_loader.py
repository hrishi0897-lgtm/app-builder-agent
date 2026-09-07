import os

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills", "taste-skill", "skills")

def load_skill(skill_name="taste-skill"):
    skill_path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    if not os.path.exists(skill_path):
        raise FileNotFoundError(f"Skill file not found: {skill_path}")
    
    with open(skill_path, "r", encoding="utf-8") as f:
        return f.read()

def get_design_system_instruction(extra_skills=None):
    skills_to_load = ["taste-skill", "output-skill"]
    if extra_skills:
        skills_to_load.extend(extra_skills)
    
    loaded_content = []
    for skill in skills_to_load:
        try:
            content = load_skill(skill)
            loaded_content.append(f"--- SKILL INSTRUCTION: {skill} ---\n{content}")
        except FileNotFoundError:
            pass
            
    return "\n\n".join(loaded_content)
