# Mini JiuwenSwarm

从零做的教学用迷你 Swarm：循环在 `engine/`，门铃在 `doorbell/`。

当前进度：**M3 两进程 + 信封**（Gateway 对浏览器，AgentServer 对循环）。

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

浏览器打开 http://127.0.0.1:18765 。Gateway 把输入打成 `chat.send` 信封；AgentServer 日志会出现 `dispatched to runner`。杀掉 AgentServer 后，页面会收到明确的 `AgentServer unavailable`，而不是空转。

工作区默认：`MINI_SWARM_WORKSPACE`，否则 `./workspace`；写不进去时落到 `~/.mini-swarm/tasks`。
