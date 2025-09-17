document.addEventListener("DOMContentLoaded", () => {
  const socket  = io();
  const logs    = document.getElementById("logs");
  const sendBtn = document.getElementById("send");
  const stopBtn = document.getElementById("stop-Btn");
  const input   = document.getElementById("topic");
  const themeToggle = document.getElementById("theme-toggle");

  if (!stopBtn) throw new Error("❌ stop-Btn element not found in DOM");
  console.log("🖥️ [main.js] script loaded");

  // Theme init
  try {
    const stored = localStorage.getItem("theme");
    if (stored === "light") {
      document.body.classList.remove("theme-dark");
      document.body.classList.add("theme-light");
    }
  } catch {}

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const isDark = document.body.classList.toggle("theme-light");
      document.body.classList.toggle("theme-dark", !isDark);
      try { localStorage.setItem("theme", isDark ? "light" : "dark"); } catch {}
    });
  }

  function showLog(msg) {
    const spinner = document.getElementById("loading-spinner");
    if (spinner) spinner.remove();

    logs.querySelectorAll(".log-entry.active").forEach(entry => entry.classList.remove("active"));
    const entry = document.createElement("div");
    entry.className = "log-entry active";
    entry.textContent = msg;
    logs.appendChild(entry);
    logs.scrollTo({ top: logs.scrollHeight, behavior: "smooth" });

    // Re-enable send if we see a finish/error/stop line
    if (/Finished generation|Generation error|stopped/i.test(msg)) {
      sendBtn.disabled = false;
    }
  }

  function showUserLog(msg) {
    const entry = document.createElement("div");
    entry.className = "log-entry user";
    entry.textContent = msg;
    logs.appendChild(entry);
  }

  sendBtn.addEventListener("click", () => {
    if (!document.body.classList.contains("started")) {
      document.body.classList.add("started");
    }
    const topic = input.value.trim();
    if (!topic) return;

    // Echo the user request and show spinner
    showUserLog(topic);
    logs.innerHTML += '<div id="loading-spinner"></div>';
    sendBtn.disabled = true;

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
    sendBtn.disabled = false;
  });

  socket.on("log", msg => showLog(msg));
});
