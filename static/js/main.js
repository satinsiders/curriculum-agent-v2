document.addEventListener("DOMContentLoaded", () => {
  const socket = io();
  const sendBtn = document.getElementById("send");
  const stopBtn = document.getElementById("stop-Btn");
  const input = document.getElementById("topic");
  const themeToggle = document.getElementById("theme-toggle");
  const statusPill = document.getElementById("status-pill");
  const messages = document.getElementById("messages");
  const logTemplate = document.getElementById("log-line-template");
  const scrollRegion = document.getElementById("chat-scroll");

  if (!sendBtn || !stopBtn || !input || !statusPill || !messages || !logTemplate || !scrollRegion) {
    throw new Error("Required DOM elements missing — cannot initialise chat UI");
  }

  const ICON_MAP = {
    "▶️": { variant: "is-info" },
    "🛠": { variant: "is-info" },
    "✅": { variant: "is-success" },
    "❌": { variant: "is-error" },
    "⚠️": { variant: "is-info" },
    "🛑": { variant: "is-error" },
    "🚀": { variant: "is-info" },
    "🔄": { variant: "is-info" },
    "📌": { variant: "is-info" }
  };

  const STATUS_COPY = {
    idle: "Awaiting prompt",
    ready: "Ready for launch",
    running: "Coordinating agents…",
    offline: "Realtime link lost",
    error: "Generation error"
  };

  let generationActive = false;
  let activeLogBucket = null;
  let activeAssistantLead = null;

  initialiseTheme();
  setStatus("idle");
  autoResize();

  socket.on("connect", () => {
    if (generationActive) {
      setStatus("running");
    } else {
      setStatus("ready", "Ready for launch");
    }
  });

  socket.on("disconnect", () => {
    setStatus("offline");
  });

  socket.on("log", raw => {
    if (typeof raw !== "string") return;
    const msg = raw.trim();
    appendLogLine(msg);

    if (/Finished generation/i.test(msg)) {
      finishGeneration("ready", "Build complete");
    } else if (/Generation error/i.test(msg)) {
      finishGeneration("error", "Generation error");
    } else if (/stopped/i.test(msg)) {
      finishGeneration("idle", "Generation stopped");
    }
  });

  stopBtn.addEventListener("click", () => {
    if (!generationActive) return;
    socket.emit("stop_generation");
    finishGeneration("idle", "Stopping…");
  });

  sendBtn.addEventListener("click", () => {
    const topic = input.value.trim();
    if (!topic) return;

    beginGeneration(topic);

    fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic })
    }).catch(() => {
      finishGeneration("offline", "Failed to reach backend");
      appendLogLine("❌ Unable to reach the generation service.");
    });
  });

  input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendBtn.click();
    }
  });

  input.addEventListener("input", autoResize);

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const isLight = document.body.classList.toggle("theme-light");
      document.body.classList.toggle("theme-dark", !isLight);
      try {
        localStorage.setItem("theme", isLight ? "light" : "dark");
      } catch (err) {
        console.warn("Unable to persist theme preference", err);
      }
    });
  }

  function beginGeneration(topic) {
    appendUserMessage(topic);
    spawnAssistantStream();

    generationActive = true;
    document.body.classList.add("is-generating");
    setStatus("running", "Coordinating agents…");

    stopBtn.disabled = false;
    sendBtn.disabled = true;
    input.value = "";
    input.disabled = true;
    autoResize();
  }

  function finishGeneration(state, label) {
    generationActive = false;
    document.body.classList.remove("is-generating");

    setStatus(state, label);

    stopBtn.disabled = true;
    sendBtn.disabled = false;
    input.disabled = false;
    input.focus({ preventScroll: true });
    autoResize();
  }

  function appendUserMessage(text) {
    const item = document.createElement("li");
    item.className = "message user";

    const bubble = document.createElement("div");
    bubble.className = "message__bubble";

    const eyebrow = document.createElement("p");
    eyebrow.className = "message__eyebrow";
    eyebrow.textContent = "You";

    const body = document.createElement("p");
    body.className = "message__text";
    body.textContent = text;

    bubble.append(eyebrow, body);
    item.append(bubble);
    messages.append(item);
    scrollToBottom();
  }

  function spawnAssistantStream() {
    const item = document.createElement("li");
    item.className = "message assistant stream";

    const bubble = document.createElement("div");
    bubble.className = "message__bubble";

    const eyebrow = document.createElement("p");
    eyebrow.className = "message__eyebrow";
    eyebrow.textContent = "Orchestrator";

    const lead = document.createElement("p");
    lead.className = "message__text";
    lead.textContent = "Spinning up specialist agents…";

    const log = document.createElement("div");
    log.className = "message__log";
    log.setAttribute("aria-live", "polite");

    bubble.append(eyebrow, lead, log);
    item.append(bubble);
    messages.append(item);

    activeLogBucket = log;
    activeAssistantLead = lead;
    activeAssistantLead.dataset.filled = "false";

    appendLogLine("🚀 Launching orchestration pipeline");

    scrollToBottom();
  }

  function appendLogLine(raw) {
    ensureLogBucket();

    const entry = logTemplate.content.firstElementChild.cloneNode(true);
    const iconSpan = entry.querySelector(".log-line__icon");
    const textSpan = entry.querySelector(".log-line__text");

    const { icon, text, variant } = dissect(raw);
    iconSpan.textContent = icon;
    textSpan.textContent = text;
    if (variant) entry.classList.add(variant);

    activeLogBucket.append(entry);

    if (activeAssistantLead && activeAssistantLead.dataset.filled === "false" && text) {
      activeAssistantLead.textContent = text;
      activeAssistantLead.dataset.filled = "true";
    }

    scrollToBottom();
  }

  function ensureLogBucket() {
    if (activeLogBucket) return;

    if (generationActive) {
      spawnAssistantStream();
      return;
    }

    const assistantMessages = Array.from(messages.querySelectorAll(".message.assistant"));
    const lastAssistant = assistantMessages[assistantMessages.length - 1];

    if (lastAssistant) {
      const bubble = lastAssistant.querySelector(".message__bubble");
      let log = bubble.querySelector(".message__log");
      if (!log) {
        log = document.createElement("div");
        log.className = "message__log";
        log.setAttribute("aria-live", "polite");
        bubble.append(log);
      }
      activeLogBucket = log;
      activeAssistantLead = bubble.querySelector(".message__text");
    } else {
      spawnAssistantStream();
    }
  }

  function dissect(message) {
    for (const icon of Object.keys(ICON_MAP)) {
      if (message.startsWith(icon)) {
        return {
          icon,
          text: message.slice(icon.length).trimStart() || message,
          variant: ICON_MAP[icon].variant || null
        };
      }
    }
    return { icon: "💬", text: message, variant: null };
  }

  function setStatus(state, label) {
    const safeState = STATUS_COPY[state] ? state : "idle";
    statusPill.dataset.state = safeState;
    statusPill.textContent = label || STATUS_COPY[safeState] || STATUS_COPY.idle;
  }

  function autoResize() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      scrollRegion.scrollTo({ top: scrollRegion.scrollHeight, behavior: "smooth" });
    });
  }

  function initialiseTheme() {
    try {
      const stored = localStorage.getItem("theme");
      if (stored === "light") {
        document.body.classList.remove("theme-dark");
        document.body.classList.add("theme-light");
      }
    } catch (err) {
      console.warn("Unable to access theme preference", err);
    }
  }
});
