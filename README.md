# Mini JiuwenSwarm

从零做的教学用迷你 Swarm：循环在 `engine/`，门铃以后再加。

当前进度：**M1 循环**（CLI + `read_file` / `write_file` / `bash`）。

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

M1 只用脚本模型走通循环，不接真实 LLM：

```bash
set MINI_SWARM_WORKSPACE=%CD%\workspace
mini-swarm --demo
```

工作区默认：`MINI_SWARM_WORKSPACE`，否则 `./workspace`；写不进去时落到 `~/.mini-swarm/tasks`。真实模型门铃在 M2。
