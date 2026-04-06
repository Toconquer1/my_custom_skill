# -*- coding: UTF-8 -*-
import os
import json
import glob
import argparse
import copy

def get_placeholder(index):
    """Generate uppercase letter placeholders: A, B, C... Z, AA, AB..."""
    res = ""
    while index >= 0:
        res = chr(65 + (index % 26)) + res
        index = index // 26 - 1
    return res

def sanitize_message(data):
    """
    递归清洗字典，移除大模型在历史会话中会丢弃的瞬态字段（如 cache_control，signature 等），
    保证当前请求和历史请求的哈希值一致。
    """
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            # 过滤掉捣乱的字段
            if k in ["cache_control", "signature"]:
                continue
            cleaned[k] = sanitize_message(v)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_message(item) for item in data]
    else:
        return data

def simplify_requests(target_dir):
    mapping = {}
    next_idx = 0
    all_extracted_tools = {}  
    global_message_pool = {}

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

    try:
        request_files.sort(key=lambda x: int(os.path.basename(x).split('_')[0]))
    except ValueError:
        print("Warning: Could not sort files properly. Proceeding with default sort.")
        request_files.sort()

    for filepath in request_files:
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        
        req_body = data.get("request_body", {})
        if not isinstance(req_body, dict):
            continue
            
        modified = False
        file_index = filename.split('_')[0]

        # 1. 历史上下文逐条比对与折叠
        if "messages" in req_body and isinstance(req_body["messages"], list):
            simplified_messages = []
            
            for i, msg in enumerate(req_body["messages"]):
                if not isinstance(msg, dict):
                    simplified_messages.append(msg)
                    continue
                
                # 【关键修复】在序列化之前，先清洗掉 cache_control 和 signature 
                clean_msg = sanitize_message(msg)
                    
                try:
                    # 使用清洗后的对象生成比对字符串
                    msg_str = json.dumps(clean_msg, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
                except Exception:
                    msg_str = str(clean_msg)
                    
                if msg_str in global_message_pool:
                    simplified_messages.append({
                        "role": "history_placeholder",
                        "content": global_message_pool[msg_str]
                    })
                    modified = True
                else:
                    origin_marker = f"[History origin: Request {file_index}, Msg {i}]"
                    global_message_pool[msg_str] = origin_marker
                    # 注意：写入文件时，仍然保留原汁原味的 msg（带着它该有的 cache_control），只在映射池里做手脚
                    simplified_messages.append(msg)
                    
            req_body["messages"] = simplified_messages

        # 2. 简化 system 字段
        if "system" in req_body:
            system_data = req_body["system"]
            if isinstance(system_data, str) and len(system_data) > 50:
                req_body["system"] = get_simplified_text(system_data)
                modified = True
            elif isinstance(system_data, list):
                for item in system_data:
                    if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                        if len(item["text"]) > 50:
                            item["text"] = get_simplified_text(item["text"])
                            modified = True

        # 3. 简化 tools 字段
        if "tools" in req_body and isinstance(req_body["tools"], list):
            simplified_tools = []
            for tool in req_body["tools"]:
                if isinstance(tool, dict) and "name" in tool:
                    tool_name = tool["name"]
                    all_extracted_tools[tool_name] = tool
                    simplified_tools.append({
                        "name": tool_name,
                        "extracted": True
                    })
                    modified = True
                else:
                    simplified_tools.append(tool)
            req_body["tools"] = simplified_tools

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Simplified: {filename}")

    # 4. 写出配置文件
    if mapping:
        prompts_path = os.path.join(target_dir, "prompts.txt")
        with open(prompts_path, 'w', encoding='utf-8') as f:
            for text, placeholder in mapping.items():
                f.write(f"================ {placeholder} ================\n")
                f.write(text)
                f.write("\n\n")

    if all_extracted_tools:
        tools_path = os.path.join(target_dir, "tools.json")
        with open(tools_path, 'w', encoding='utf-8') as f:
            json.dump(all_extracted_tools, f, ensure_ascii=False, indent=4)

    print("\nAll tasks completed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simplify extracted request JSONs by mapping history and removing transient keys.")
    parser.add_argument("-d", "--dir", default="output_jsons", help="Directory containing request JSON files")
    args = parser.parse_args()
    
    simplify_requests(args.dir)