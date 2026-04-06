# -*- coding: UTF-8 -*-
import os
import json
import glob
import argparse

def get_placeholder(index):
    """Generate uppercase letter placeholders: A, B, C... Z, AA, AB..."""
    res = ""
    while index >= 0:
        res = chr(65 + (index % 26)) + res
        index = index // 26 - 1
    return res

def simplify_requests(target_dir):
    """
    Traverse the target folder and simplify system and tools fields 
    based on the specified rules.
    """
    mapping = {}
    next_idx = 0
    all_extracted_tools = {}  # Globally store all extracted tool definitions
    
    def get_simplified_text(text):
        nonlocal next_idx
        if text not in mapping:
            placeholder = get_placeholder(next_idx)
            mapping[text] = f"[{placeholder}]"
            next_idx += 1
        return mapping[text]

    search_pattern = os.path.join(target_dir, "*_request_*.json")
    request_files = glob.glob(search_pattern)
    
    if not request_files:
        print(f"Warning: No _request_ files found in directory '{target_dir}'.")
        return

    for filepath in request_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        
        req_body = data.get("request_body", {})
        if not isinstance(req_body, dict):
            continue
            
        modified = False
        
        # 1. Simplify system field (only for text length > 50)
        if "system" in req_body:
            system_data = req_body["system"]
            if isinstance(system_data, str) and len(system_data) > 50:
                req_body["system"] = get_simplified_text(system_data)
                modified = True
            elif isinstance(system_data, list):
                for item in system_data:
                    if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                        # Replace only if the text length is greater than 50 characters
                        if len(item["text"]) > 50:
                            item["text"] = get_simplified_text(item["text"])
                            modified = True

        # 2. Simplify tools field and extract to tools.json
        if "tools" in req_body and isinstance(req_body["tools"], list):
            simplified_tools = []
            for tool in req_body["tools"]:
                if isinstance(tool, dict) and "name" in tool:
                    tool_name = tool["name"]
                    # Save the full tool JSON to the global dictionary (deduplicates by name)
                    all_extracted_tools[tool_name] = tool
                    
                    # Replace with a simplified dictionary in the original request
                    simplified_tools.append({
                        "name": tool_name,
                        "extracted": True
                    })
                    modified = True
                else:
                    # Keep original format if tool is non-standard or missing a name
                    simplified_tools.append(tool)
                    
            req_body["tools"] = simplified_tools

        # Save the simplified request file
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Simplified: {os.path.basename(filepath)}")

    # 3. Write long system prompts to prompts.txt
    if mapping:
        prompts_path = os.path.join(target_dir, "prompts.txt")
        with open(prompts_path, 'w', encoding='utf-8') as f:
            for text, placeholder in mapping.items():
                f.write(f"================ {placeholder} ================\n")
                f.write(text)
                f.write("\n\n")
        print(f"\nExtracted {len(mapping)} long system prompts (>50 chars), written to: {prompts_path}")

    # 4. Write extracted tools to tools.json
    if all_extracted_tools:
        tools_path = os.path.join(target_dir, "tools.json")
        with open(tools_path, 'w', encoding='utf-8') as f:
            json.dump(all_extracted_tools, f, ensure_ascii=False, indent=4)
        print(f"Extracted {len(all_extracted_tools)} unique tools, written to: {tools_path}")

    if not mapping and not all_extracted_tools:
        print("\nNo matching system or tools fields found. No files were modified.")
    else:
        print("\nAll tasks completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simplify extracted request JSONs by separating prompts and tools.")
    parser.add_argument("-d", "--dir", default="output_jsons", help="Directory containing request JSON files (default: output_jsons)")
    args = parser.parse_args()
    
    print(f"Scanning directory: {args.dir} ...")
    simplify_requests(args.dir)