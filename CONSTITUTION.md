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
| M5 声明式 Rail | 完成 | `rail.yaml` 增删工具；循环仍只在 `react.py` |
| M6 子代理 | 完成 | `task` 派出隔离 session 的子 `ReactAgent` |
| M7 Leader / Teammate | 完成 | 同进程 `Team(leader, teammate)`，`ask_teammate` 复用队友 session |
| M8 真实模型 | 完成 | `OpenAICompatModel.complete`；无 `--demo` 时读 `MINI_SWARM_API_KEY` |
| M9 工作区记忆 | 完成 | `AGENTS.md` / `MEMORY.md` 每次 `complete` 前由 Harness 注入；不写入 session |
| M10 按需 Skills | 完成 | `skills/*/SKILL.md` 只注入目录；全文靠 `read_file`；循环仍只在 `react.py` |
| M11 上下文压缩 | 完成 | session 超长时 Harness 折叠旧消息；不在循环外调模型 |
| M12 流式 Think | 完成 | `Model.stream` 产出分片 `text.delta`；循环仍只在 `react.py` |
| M13 门铃直播 | 完成 | `attach_output` 边想边转发 `text.delta`；循环仍只在 `react.py` |

## 禁止

- 单文件超过 800 行就拆。
- 同一行为不要两套开关。
- 新功能先问：是 Rail，还是门铃特例？只有确认/拒绝这种跨 UI 的才进门铃。
- M5 之前不把声明式装配当施工图。
