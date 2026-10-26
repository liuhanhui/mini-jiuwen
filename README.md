# Mini JiuwenSwarm

从零做的教学用迷你 Swarm：循环在 `engine/`，门铃在 `doorbell/`。

当前进度：**M13 门铃直播**（`attach_output` 边想边转发 `text.delta`；循环仍只在 `react.py`）。

## 安装

```bash
cd mini-jiuwenswarm
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 测试

```bash
pytest
```

## 跑一问（脚本模型，不需要 API key）

```bash
set MINI_SWARM_WORKSPACE=%CD%\workspace
mini-swarm --demo
```

M2 单进程 HTTP：

```bash
mini-swarm --serve --demo --port 18765
```

M3 两进程（先 AgentServer:18765，再 Gateway:8764）：

```bash
mini-swarm --start --demo
```

浏览器打开 http://127.0.0.1:8764 。Gateway 把输入打成 `chat.send` 信封；AgentServer 日志会出现 `dispatched to runner`。杀掉 AgentServer 后，页面会收到明确的 `AgentServer unavailable`，而不是空转。

`bash` 会先弹出 **允许 / 拒绝**。不点允许，命令不会执行。

从 `rail.yaml` 增删工具（不必改循环）：

```bash
mini-swarm --demo --rail rail.yaml
```

把 `bash` 那一行删掉后，Agent 不再暴露该工具。未指定 `--rail` 时，若工作区有 `rail.yaml` 则用它，否则内置工具全开。

`task` 会再开一个 `ReactAgent`，使用空的子 session（`sessions/task-*.json`），子代理没有 `task` 工具，避免套娃。

`ask_teammate` 问的是同进程里常驻的 Teammate（`sessions/<id>-teammate.json`），多次提问会续上同一段对话，不是每次新建子代理。

真实模型（OpenAI 兼容，不需要 `--demo`）：

```powershell
$env:MINI_SWARM_API_KEY="sk-..."
$env:MINI_SWARM_BASE_URL="https://api.deepseek.com"
$env:MINI_SWARM_MODEL="deepseek-chat"
mini-swarm "What is the first line of README?"
mini-swarm --start
```

工作区可以放两份记忆文件。Harness 每次调用模型前现读现拼，不写进 session：

```text
workspace/AGENTS.md   长期说明书（怎么做事）
workspace/MEMORY.md   可改的笔记（模型可用 write_file 更新）
```

同一轮里写入 `MEMORY.md` 后，下一步 `complete` 就能看到新内容。Leader、Teammate、`task` 子代理共用工作区，因此共用记忆。

长流程不要写进 `AGENTS.md`。放到 `workspace/skills/<name>/SKILL.md`，Harness 只注入目录（名字、一行摘要、路径）。模型需要步骤时，用 `read_file` 读那份文件。

同一 session 消息超过预算（默认 24 条）时，Harness 会把旧前缀收成一条 `[compacted]` 说明，留下最近几条。不另调模型；CLI 会出现 `[compact] dropped=… kept=…`。`AGENTS.md` / skill 目录每次仍现读现拼，不参与这条折叠。

真实模型走 `stream`：正文按片变成多条 `text.delta`，工具调用仍等拼完整再 `tool.call`。循环还是只在 `react.py` 里拉模型。`attach_output` 边想边转发，CLI / HTTP NDJSON 不必等整轮 `run` 结束。

工作区默认：`MINI_SWARM_WORKSPACE`，否则 `./workspace`；写不进去时落到 `~/.mini-swarm/tasks`。工具只能碰该目录。
