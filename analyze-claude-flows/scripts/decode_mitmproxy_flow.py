# -*- coding: UTF-8 -*-
import os
import json
import datetime
import argparse
from mitmproxy import io
from mitmproxy.exceptions import FlowReadException

def parse_sse(content):
    """
    Parse SSE (Server-Sent Events) and consolidate all key information 
    (text, thinking, tool calls, usage) together.
    """
    combined_text = ""
    combined_thinking = ""
    tool_calls = {}  # Use index as key to temporarily store tool call fragments
    usage = {}
    stop_reason = None

    lines = content.split('\n')
    
    for line in lines:
        if line.startswith('data:'):
            data_str = line[5:].strip()
            if not data_str or data_str == "[DONE]":
                continue
                
            try:
                data_json = json.loads(data_str)
                event_type = data_json.get("type", "")

                # 1. Intercept content block start (primarily for capturing tool call initialization)
                if event_type == "content_block_start":
                    index = data_json.get("index")
                    cb = data_json.get("content_block", {})
                    if cb.get("type") == "tool_use":
                        tool_calls[index] = {
                            "id": cb.get("id"),
                            "name": cb.get("name"),
                            "arguments": "" # Placeholder for subsequent json_delta
                        }

                # 2. Intercept content block delta (concatenate text, thinking process, and tool arguments)
                elif event_type == "content_block_delta":
                    index = data_json.get("index")
                    delta = data_json.get("delta", {})
                    delta_type = delta.get("type", "")
                    
                    if delta_type == "thinking_delta":
                        combined_thinking += delta.get("thinking", "")
                    elif delta_type == "text_delta":
                        combined_text += delta.get("text", "")
                    elif delta_type == "input_json_delta":
                        if index in tool_calls:
                            # Concatenate fragmented tool call JSON arguments
                            tool_calls[index]["arguments"] += delta.get("partial_json", "")

                # 3. Intercept message-level delta (capture stop reason and token usage)
                elif event_type == "message_delta":
                    delta = data_json.get("delta", {})
                    if "stop_reason" in delta:
                        stop_reason = delta["stop_reason"]
                    if "usage" in data_json:
                        usage = data_json["usage"]

                # --- Fallback logic for OpenAI format compatibility ---
                elif "choices" in data_json and len(data_json["choices"]) > 0:
                    delta = data_json["choices"][0].get("delta", {})
                    if "content" in delta:
                        combined_text += delta.get("content", "")
                    if "reasoning_content" in delta: 
                        combined_thinking += delta.get("reasoning_content", "")

            except json.JSONDecodeError:
                pass

    # Post-processing: Attempt to parse concatenated tool arguments into actual JSON dictionaries
    formatted_tool_calls = []
    for tc in tool_calls.values():
        try:
            if tc["arguments"]:
                tc["arguments"] = json.loads(tc["arguments"])
        except json.JSONDecodeError:
            pass # Keep as raw string if parsing fails
        formatted_tool_calls.append(tc)

    return {
        "is_sse_stream": True,
        "integrated_thinking": combined_thinking,
        "integrated_text": combined_text,
        "tool_calls": formatted_tool_calls, # Fully assembled list of tool calls
        "usage": usage,                     # Token usage statistics
        "stop_reason": stop_reason          # e.g., "tool_use" or "end_turn"
    }

def extract_body(content_bytes):
    if not content_bytes:
        return ""
    try:
        content_str = content_bytes.decode('utf-8', errors='ignore')
        return json.loads(content_str)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return content_bytes.decode('utf-8', errors='ignore')

def decode_flows(input_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_file, "rb") as logfile:
        freader = io.FlowReader(logfile)
        index = 1
        
        try:
            for flow in freader.stream():
                if not flow.request:
                    continue

                req_time = datetime.datetime.fromtimestamp(flow.request.timestamp_start).strftime("%Y%m%d_%H%M%S")
                
                req_body = extract_body(flow.request.content)
                req_filename = os.path.join(output_dir, f"{index}_request_{req_time}.json")
                with open(req_filename, 'w', encoding='utf-8') as f:
                    json.dump({"request_body": req_body}, f, ensure_ascii=False, indent=4)

                if flow.response:
                    res_time = datetime.datetime.fromtimestamp(flow.response.timestamp_start).strftime("%Y%m%d_%H%M%S")
                    content_type = flow.response.headers.get("content-type", "")
                    res_str = flow.response.content.decode('utf-8', errors='ignore') if flow.response.content else ""
                    
                    if "text/event-stream" in content_type or res_str.startswith("event:"):
                        res_body = parse_sse(res_str)
                    else:
                        res_body = extract_body(flow.response.content)

                    res_filename = os.path.join(output_dir, f"{index}_response_{res_time}.json")
                    with open(res_filename, 'w', encoding='utf-8') as f:
                        json.dump({"response_body": res_body}, f, ensure_ascii=False, indent=4)

                print(f"Successfully exported request/response pair {index} ({req_time})")
                index += 1
                
        except FlowReadException as e:
            print(f"Error reading file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse mitmproxy export files to extract request and response bodies.")
    parser.add_argument("input_file", help="Path to the mitmproxy export file")
    parser.add_argument("-o", "--output", default="output_jsons", help="Output directory name")
    args = parser.parse_args()
    
    print(f"Starting to parse {args.input_file} ...")
    decode_flows(args.input_file, args.output)
    print(f"\nTask completed! Results saved in directory: {args.output}/")