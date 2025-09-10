document.addEventListener("DOMContentLoaded", () => {
  const socket  = io();
  const chatbox = document.getElementById("chatbox");
  const logs    = document.getElementById("logs");
  const sendBtn = document.getElementById("send");
  const stopBtn = document.getElementById("stop-Btn")
  const input   = document.getElementById("topic");
    
  if (!stopBtn) throw new Error("❌ stop-Btn element not found in DOM");

  console.log("🖥️ [main.js] script loaded");

  function showLog(msg) {
    // remove spinner if present
    const spinner = document.getElementById("loading-spinner");
    if (spinner) spinner.remove();

    // “undim” only the newest entry, dim the rest
    logs.querySelectorAll(".log-entry.active").forEach(entry => {
      entry.classList.remove("active");
    });

    // create & append the new, active entry
    const entry = document.createElement("div");
    entry.className = "log-entry active";
    entry.textContent = msg;
    logs.appendChild(entry);

    // smoothly scroll to bottom
    logs.scrollTo({ top: logs.scrollHeight, behavior: "smooth" });

    console.log("📝 [main.js] showLog():", msg);
  }

  sendBtn.addEventListener("click", () => {
    // on first send, flip to "started" layout
    if (!document.body.classList.contains("started")) {
          document.body.classList.add("started");
    }
    const topic = input.value.trim();
    if (!topic) return;

    logs.innerHTML        = '<div id="loading-spinner"></div>';

    fetch("/generate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ topic })
    });
  });

  input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendBtn.click();
  });

  stopBtn.addEventListener("click", () => {
    console.log("🛑 [main.js] stopBtn clicked");
    socket.emit("stop_generation");
  });
    
  socket.on("log", msg => showLog(msg));
});
