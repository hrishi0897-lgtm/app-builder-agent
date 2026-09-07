import os
import re

FILE_BLOCK_REGEX = re.compile(r"```(?:\w+)?\s*file=([^\n]+)\n(.*?)```", re.DOTALL)

def extract_and_write_files(llm_response, output_dir="workspace"):
    os.makedirs(output_dir, exist_ok=True)
    matches = FILE_BLOCK_REGEX.findall(llm_response)
    
    written_files = []
    
    for relative_path, file_content in matches:
        relative_path = relative_path.strip().strip("\"'")
        full_path = os.path.join(output_dir, relative_path)
        
        parent_dir = os.path.dirname(full_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(file_content.rstrip() + "\n")
            
        written_files.append(relative_path)
        
    return written_files
