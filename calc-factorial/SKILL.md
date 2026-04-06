---
name: calc-factorial
description: 计算给定数字的阶乘。当用户询问某个数字的阶乘，或直接通过 /calc-factorial 调用时使用此技能。
argument-hint: <number>
---

你的任务是计算用户提供数字的阶乘。

请使用终端工具运行以下命令来完成计算。该脚本会自动处理计算逻辑，并将调用记录写在日志中。

你要执行的命令如下：

```bash
python "${CLAUDE_SKILL_DIR}/scripts/factorial.py" "$1"
```
