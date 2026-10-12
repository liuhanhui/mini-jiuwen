# Mini JiuwenSwarm 宪法

迷你版的目标：对照 JiuwenSwarm，把「门铃」和「循环」做成能跑的实物。
不是缩小复刻 `interface_deep.py`。

## 铁律

1. **Agent = Model + Harness。** 模型只负责「下一步干什么」；工具、权限、停止条件在 Harness。
2. **循环只有一处：`mini_swarm/engine/react.py`。** 通道、Gateway、AgentServer 都是门铃，请求处理函数里禁止 `while` 调模型。
3. **默认 Team 不是多个 OS 进程，** 是多个 Agent 对象。
4. **工作区路径可配置，且必须探测可写。** `mkdir` 失败则落到 `~/.mini-swarm/tasks`，打警告。
5. **信封最小集：** `session_id`、`request_id`、`method`、`query`。`method` 在 M3 之前可以不存在；出现后先只允许 `chat.send`。

## 里程碑（做到哪算哪）

| 里程碑 | 状态 | 完成标准 |
| --- | --- | --- |
| M0 宪法 | 完成 | 本文件 + 目录骨架 |
| M1 循环 | 完成 | CLI `--demo` 能调 `read_file` 回答 README 第一行 |
| M2 门铃与引擎分离 | 完成 | HTTP `/chat` 只 `send_input` / `attach_output`；同 session 可续 |
| M3 两进程 + 信封 | 完成 | `mini-swarm --start --demo`：Gateway:8764 + AgentServer:18765，信封 `chat.send` |
| M4 工作区与权限 | 完成 | 工具不出 workspace；`bash` 先 `permission.ask`，拒绝则观察「用户拒绝」 |
| M5 声明式 Rail | 未开始 | YAML 增删工具，不改循环 |
| M6 子代理 | 未开始 | `task` 派出隔离上下文 |
| M7 Leader / Teammate | 未开始 | 同进程两个 Agent 对象 |

## 禁止

- 单文件超过 800 行就拆。
- 同一行为不要两套开关。
- 新功能先问：是 Rail，还是门铃特例？只有确认/拒绝这种跨 UI 的才进门铃。
- M5 之前不把声明式装配当施工图。
