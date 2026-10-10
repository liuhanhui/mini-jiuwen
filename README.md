# Mini JiuwenSwarm

从零做的教学用迷你 Swarm：循环在 `engine/`，门铃在 `doorbell/`。

当前进度：**M2 门铃与引擎分离**（`DeepAgent.send_input` / `attach_output` + HTTP `/chat`）。

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

HTTP 门铃（关掉再开，同一 `session_id` 会读盘续上）：

```bash
mini-swarm --serve --demo --port 8765
curl -N -H "Content-Type: application/json" -d "{\"session_id\":\"s1\",\"query\":\"What is the first line of README?\"}" http://127.0.0.1:8765/chat
```

工作区默认：`MINI_SWARM_WORKSPACE`，否则 `./workspace`；写不进去时落到 `~/.mini-swarm/tasks`。
