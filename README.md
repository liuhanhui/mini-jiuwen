# Mini JiuwenSwarm

从零做的教学用迷你 Swarm：循环在 `engine/`，门铃在 `doorbell/`。

当前进度：**M8 真实模型**（OpenAI 兼容接口；循环仍只调 `Model.complete`）。

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

```bash
set MINI_SWARM_API_KEY=sk-...
set MINI_SWARM_BASE_URL=https://api.openai.com/v1
set MINI_SWARM_MODEL=gpt-4o-mini
mini-swarm "What is the first line of README?"
mini-swarm --start
```

工作区默认：`MINI_SWARM_WORKSPACE`，否则 `./workspace`；写不进去时落到 `~/.mini-swarm/tasks`。工具只能碰该目录。
