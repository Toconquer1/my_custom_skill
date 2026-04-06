---
name: analyze-claude-flows
description: 解析 mitmproxy flows 文件，自动提取并梳理 Claude 智能体的完整调用链路（包含用户问题、思考过程、工具调用及执行结果），并生成分析报告。
argument-hint: <flows_file.txt>
---

你的任务是分析用户指定的 mitmproxy flows 文件，提取大模型的智能体调用链路，并生成一份详细的报告。

用户提供的 flows 文件路径为：`$1`

### 步骤 1：规划并创建输出目录
首先，请你根据用户提供的文件路径 `$1`，提取出其基础文件名。
请你自行调用终端/命令行工具，在当前工作目录下创建一个以该文件名为前缀的输出文件夹（例如命名为 `[文件名]_analysis_result`）。
接着，在这个刚创建的输出文件夹内部，继续创建两个子文件夹：
- `parsed_jsons`：用于存放后续解析生成的 JSON 数据。
- `report`：用于存放最终的 Markdown 分析报告。

### 步骤 2：执行解码脚本
目录创建准备完毕后，请调用终端工具执行以下 Python 命令，将 flows 文件解码到你刚才创建的 `parsed_jsons` 目录中。
（注意：请将命令中的 `[生成的JSON目录路径]` 动态替换为你实际创建的路径）：

```bash
python "${CLAUDE_SKILL_DIR}/scripts/decode_mitmproxy_flow.py" "$1" -o "[生成的JSON目录路径]"
```

### 步骤 3：执行数据精简脚本
解码成功后，为了避免庞大的上下文干扰你的后续分析，请继续调用终端执行以下命令，抽离冗长的 System Prompt 和 Tools。
（同样，请将 `[生成的JSON目录路径]` 替换为实际路径）：

```bash
python "${CLAUDE_SKILL_DIR}/scripts/simplify_prompts.py" -d "[生成的JSON目录路径]"
```

### 步骤 4：读取并分析处理后的数据
精简脚本执行完毕后，`parsed_jsons` 目录内应该已经生成了多对 `index_request_*.json` 和 `index_response_*.json` 文件。
1. 请先列出该目录下的所有文件。
2. 请按文件名的 index 数字顺序，依次读取这些 JSON 文件的内容。
3. **分析重点**：
   - 阅读 `request` 文件中 `messages` 数组里追加的最新用户对话。
   - 阅读 `response` 文件中的 `integrated_thinking`（思考过程）、`integrated_text`（文本回复）和 `tool_calls`（工具调用）。

### 步骤 5：撰写智能体链路分析报告
基于你读取和理解的内容，请在你创建的 `report` 目录中，生成并写入一份名为 `agent_trace_report.md` 的详细分析报告。
报告必须严格包含以下结构：
1. **背景概述**：用户最初提出了什么问题？
2. **完整调用链路（Timeline）**：按时间顺序精准还原智能体的交互过程，格式如下：
- **请求 [Index]**：
     - **📥 新增输入**：对比上一次请求，本次 `request` 的 `messages` 中追加了什么新内容？（例如：用户的提问，或是上一轮工具执行后返回的结果，第一轮的话全部给出即可）。
     - **🧠 模型思考**：提取并简述 `response` 中的 `integrated_thinking` 的核心逻辑。如果为空，标明“无”。
     - **🛠️ 工具调用**：提取 `response` 中的 `tool_calls`。列出调用的 `[工具名]` 及核心 `[参数]`。如果没有调用，标明“无”。
     - **💬 文本输出**：提取 `response` 中的 `integrated_text`。如果是发给用户的文本回复，请记录于此；如果为空，标明“无”。
3. **使用的工具列表**：汇总本次交互中模型实际调用的所有工具名称及作用。
4. **Token 消耗统计**：汇总并计算各响应节点中的 `usage` 消耗。

### 步骤 6：结束反馈
完成报告保存后，请向用户简短总结核心的调用链路（例如：“模型先调用了 A 工具读取文件，然后根据结果调用了 B 工具，最后输出了计算结果”），并告知用户分析报告的具体保存路径。