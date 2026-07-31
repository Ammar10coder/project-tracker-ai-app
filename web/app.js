const dot = document.getElementById("status-dot");
const ring = document.getElementById("pulse-ring");
const label = document.getElementById("status-label");
const sub = document.getElementById("status-sub");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const refreshBtn = document.getElementById("refresh-btn");
const feedback = document.getElementById("feedback");
const logBody = document.getElementById("log-body");
const logMeta = document.getElementById("log-meta");

const settingsFeedback = document.getElementById("settings-feedback");
const drivePill = document.getElementById("drive-pill");
const driveConnectBtn = document.getElementById("drive-connect-btn");
const saveSettingsBtn = document.getElementById("save-settings-btn");

const loginModal = document.getElementById("login-modal");
const loginTitle = document.getElementById("login-title");
const loginDesc = document.getElementById("login-desc");
const loginInput = document.getElementById("login-input");
const loginError = document.getElementById("login-error");
const loginSubmitBtn = document.getElementById("login-submit-btn");
const loginCancelBtn = document.getElementById("login-cancel-btn");

const SETTINGS_FIELDS = [
  "API_ID", "API_HASH", "PHONE", "TARGET_GROUP_NAME",
  "GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY",
  "GMAIL_USER", "GMAIL_APP_PASSWORD", "REPORT_RECIPIENT_EMAIL",
  "DRIVE_TARGET_FOLDER_ID"
];

let currentLoginStage = null;

function setFeedback(el, text, kind) {
  el.textContent = text || "";
  el.className = "feedback" + (kind ? " " + kind : "");
}

// ---------------- Tabs ----------------
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

// ---------------- Status polling ----------------
function applyStatus(data) {
  dot.classList.remove("running", "stopped", "error");
  ring.classList.remove("active");

  if (data.error) {
    dot.classList.add("error");
    label.textContent = "Error";
    sub.textContent = data.error;
    startBtn.disabled = false;
    stopBtn.disabled = true;
  } else if (data.running) {
    dot.classList.add("running");
    ring.classList.add("active");
    label.textContent = "Running";
    sub.textContent = data.last_message ? ("Last: " + data.last_message) : "Listening for updates";
    startBtn.disabled = true;
    stopBtn.disabled = false;
  } else if (data.starting) {
    dot.classList.add("stopped");
    label.textContent = "Starting…";
    sub.textContent = "Connecting to Telegram";
    startBtn.disabled = true;
    stopBtn.disabled = true;
  } else {
    dot.classList.add("stopped");
    label.textContent = "Stopped";
    sub.textContent = data.configured ? "Click Start bot to launch it" : "Fill in Settings first";
    startBtn.disabled = false;
    stopBtn.disabled = true;
  }

  drivePill.textContent = data.drive_connected ? "Drive connected" : "Not connected";
  drivePill.classList.toggle("off", !data.drive_connected);

  handleLoginStage(data.stage, data.error);
}

function handleLoginStage(stage, error) {
  if (!stage) {
    currentLoginStage = null;
    loginModal.classList.remove("open");
    return;
  }
  if (stage !== currentLoginStage) {
    currentLoginStage = stage;
    loginInput.value = "";
    if (stage === "need_phone") {
      loginTitle.textContent = "Telegram: phone number";
      loginDesc.textContent = "Enter the phone number linked to your Telegram account, with country code.";
      loginInput.placeholder = "+91XXXXXXXXXX";
      loginInput.type = "text";
    } else if (stage === "need_code") {
      loginTitle.textContent = "Telegram: enter code";
      loginDesc.textContent = "Telegram just sent a login code to your account. Enter it here.";
      loginInput.placeholder = "12345";
      loginInput.type = "text";
    } else if (stage === "need_password") {
      loginTitle.textContent = "Telegram: 2FA password";
      loginDesc.textContent = "Your account has two-step verification enabled. Enter that password.";
      loginInput.placeholder = "Password";
      loginInput.type = "password";
    }
  }
  setFeedback(loginError, error || "", error ? "err" : "");
  loginModal.classList.add("open");
  loginInput.focus();
}

loginSubmitBtn.addEventListener("click", async () => {
  const value = loginInput.value.trim();
  if (!value) return;
  let endpoint = null;
  if (currentLoginStage === "need_phone") endpoint = "/api/telegram/phone";
  else if (currentLoginStage === "need_code") endpoint = "/api/telegram/code";
  else if (currentLoginStage === "need_password") endpoint = "/api/telegram/password";
  if (!endpoint) return;
  await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value })
  });
  loginInput.value = "";
  setFeedback(loginError, "Checking…", "");
  setTimeout(refreshStatus, 800);
});

loginCancelBtn.addEventListener("click", async () => {
  await fetch("/api/stop", { method: "POST" });
  loginModal.classList.remove("open");
  currentLoginStage = null;
  refreshAll();
});

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    applyStatus(data);
  } catch (e) {
    dot.classList.remove("running", "stopped");
    dot.classList.add("error");
    label.textContent = "Can't reach the app";
    sub.textContent = "Is it still open?";
  }
}

async function refreshLogs() {
  try {
    const res = await fetch("/api/logs");
    const data = await res.json();
    logBody.textContent = data.logs || "No activity yet.";
    logBody.scrollTop = logBody.scrollHeight;
    logMeta.textContent = "Last checked " + new Date().toLocaleTimeString();
  } catch (e) {
    logMeta.textContent = "Couldn't load logs";
  }
}

async function refreshAll() {
  await Promise.all([refreshStatus(), refreshLogs()]);
}

startBtn.addEventListener("click", async () => {
  startBtn.disabled = true;
  setFeedback(feedback, "Starting the bot…");
  try {
    const res = await fetch("/api/start", { method: "POST" });
    const data = await res.json();
    setFeedback(feedback, data.message, data.ok ? "ok" : "err");
  } catch (e) {
    setFeedback(feedback, "Couldn't reach the app.", "err");
  }
  await refreshAll();
});

stopBtn.addEventListener("click", async () => {
  stopBtn.disabled = true;
  setFeedback(feedback, "Stopping the bot…");
  try {
    const res = await fetch("/api/stop", { method: "POST" });
    const data = await res.json();
    setFeedback(feedback, data.message, data.ok ? "ok" : "err");
  } catch (e) {
    setFeedback(feedback, "Couldn't reach the app.", "err");
  }
  loginModal.classList.remove("open");
  currentLoginStage = null;
  await refreshAll();
});

refreshBtn.addEventListener("click", () => {
  setFeedback(feedback, "");
  refreshAll();
});

// ---------------- Settings ----------------
async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const data = await res.json();
    SETTINGS_FIELDS.forEach(key => {
      const el = document.getElementById("s-" + key);
      if (el) el.value = data[key] || "";
    });
  } catch (e) {
    setFeedback(settingsFeedback, "Couldn't load settings.", "err");
  }
}

saveSettingsBtn.addEventListener("click", async () => {
  const payload = {};
  SETTINGS_FIELDS.forEach(key => {
    const el = document.getElementById("s-" + key);
    if (el) payload[key] = el.value.trim();
  });
  setFeedback(settingsFeedback, "Saving…");
  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    setFeedback(settingsFeedback, data.ok ? "Saved." : "Couldn't save.", data.ok ? "ok" : "err");
  } catch (e) {
    setFeedback(settingsFeedback, "Couldn't save.", "err");
  }
  refreshStatus();
});

driveConnectBtn.addEventListener("click", async () => {
  driveConnectBtn.disabled = true;
  setFeedback(settingsFeedback, "Opening your browser for Google sign-in…");
  try {
    const res = await fetch("/api/drive/connect", { method: "POST" });
    const data = await res.json();
    setFeedback(settingsFeedback, data.message, data.ok ? "ok" : "err");
  } catch (e) {
    setFeedback(settingsFeedback, "Couldn't start Drive connection.", "err");
  }
  driveConnectBtn.disabled = false;
  setTimeout(refreshStatus, 3000);
});

loadSettings();
refreshAll();
setInterval(refreshAll, 4000);
