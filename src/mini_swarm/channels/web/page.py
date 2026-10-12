CHAT_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Mini JiuwenSwarm</title>
  <style>
    body { font-family: sans-serif; max-width: 40rem; margin: 2rem auto; }
    #log { border: 1px solid #ccc; min-height: 12rem; padding: 0.75rem; white-space: pre-wrap; }
    .tool { color: #666; }
    .error { color: #b00020; }
    form, #ask { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
    #ask { display: none; }
    input { flex: 1; padding: 0.4rem; }
  </style>
</head>
<body>
  <h1>Mini JiuwenSwarm</h1>
  <div id="log"></div>
  <div id="ask">
    <button type="button" id="allow">允许</button>
    <button type="button" id="deny">拒绝</button>
  </div>
  <form id="f">
    <input id="q" autocomplete="off" placeholder="说一句话" />
    <button type="submit">发送</button>
  </form>
  <script>
    const log = document.getElementById("log");
    const ask = document.getElementById("ask");
    const ws = new WebSocket(`ws://${location.host}/ws`);
    function decide(decision) {
      ws.send(JSON.stringify({ session_id: "browser", decision }));
      ask.style.display = "none";
    }
    document.getElementById("allow").onclick = () => decide("allow");
    document.getElementById("deny").onclick = () => decide("deny");
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.kind === "text.delta") {
        log.textContent += (msg.payload.text || "") + "\\n";
      } else if (msg.kind === "tool.call") {
        log.textContent += "[tool] " + msg.payload.name + "\\n";
      } else if (msg.kind === "permission.ask") {
        const cmd = (msg.payload.args && msg.payload.args.command) || "";
        log.textContent += "[bash?] " + cmd + "\\n";
        ask.style.display = "flex";
      } else if (msg.kind === "error") {
        log.textContent += "错误: " + (msg.payload.message || "unknown") + "\\n";
      }
    };
    ws.onclose = () => { log.textContent += "连接已关闭\\n"; };
    document.getElementById("f").onsubmit = (e) => {
      e.preventDefault();
      const q = document.getElementById("q");
      ws.send(JSON.stringify({ session_id: "browser", query: q.value }));
      q.value = "";
    };
  </script>
</body>
</html>
"""
