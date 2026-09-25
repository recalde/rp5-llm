const statusEl = document.querySelector("#status");
const dot = document.querySelector("#dot");
const deviceEl = document.querySelector("#device");
const modelName = document.querySelector("#model-name");
const modelFile = document.querySelector("#model-file");
const backendEl = document.querySelector("#backend");
const ipEl = document.querySelector("#ip");
const apiEl = document.querySelector("#api");
const exposureEl = document.querySelector("#exposure");
const uptimeEl = document.querySelector("#uptime");
const callsEl = document.querySelector("#calls");
const activeEl = document.querySelector("#active");
const lastEl = document.querySelector("#last");
const promptEl = document.querySelector("#prompt-tokens");
const generatedEl = document.querySelector("#generated-tokens");
const clockEl = document.querySelector("#clock");
const historyPanel = document.querySelector("#history");
const historyRows = document.querySelector("#history-rows");

function clock() {
  clockEl.textContent = new Date().toLocaleTimeString([], { hour12: false });
}

function uptime(seconds) {
  const whole = Math.max(0, Math.floor(seconds || 0));
  const hours = String(Math.floor(whole / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((whole % 3600) / 60)).padStart(2, "0");
  const secs = String(whole % 60).padStart(2, "0");
  return `${hours}:${minutes}:${secs}`;
}

function paint(data) {
  const state = data.status || "offline";
  statusEl.textContent = state;
  dot.className = `dot ${state}`;
  deviceEl.textContent = data.device || "unknown";
  modelName.textContent = data.modelName || "No model";
  modelFile.textContent = data.model && data.model !== "none" ? data.model : "not loaded";
  backendEl.textContent = (data.backend || "cpu").toUpperCase();
  ipEl.textContent = data.ip || "—";
  apiEl.textContent = data.api && data.api.base ? data.api.base : "—";
  exposureEl.textContent = data.api && data.api.exposed ? "LAN exposed" : "local device only";
  uptimeEl.textContent = uptime(data.uptimeSeconds);
  const requests = data.requests || {};
  callsEl.textContent = String(requests.total || 0);
  activeEl.textContent = `${requests.active || 0} active`;
  const last = data.lastRequest;
  lastEl.textContent = last && last.timestamp
    ? new Date(last.timestamp).toLocaleTimeString([], { hour12: false })
    : "—";
  promptEl.textContent = last && last.promptTokens != null ? String(last.promptTokens) : "—";
  generatedEl.textContent = last && last.generatedTokens != null ? String(last.generatedTokens) : "—";
}

async function tick() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("status");
    paint(await response.json());
  } catch (_error) {
    paint({ status: "offline", device: "status API unreachable", requests: { total: 0, active: 0 } });
  }
}

async function loadHistory() {
  const response = await fetch("/api/requests?limit=20");
  const payload = await response.json();
  historyRows.replaceChildren();
  for (const row of payload.requests || []) {
    const line = document.createElement("div");
    line.className = "row";
    const when = row.timestamp ? new Date(row.timestamp).toLocaleTimeString([], { hour12: false }) : "—";
    line.innerHTML = `<span>${when}</span><span>${row.model || "—"}</span><span>${row.ok ? "ok" : "fail"}</span><span>${row.generatedTokens ?? "—"} tok</span>`;
    historyRows.append(line);
  }
  if (!payload.requests || payload.requests.length === 0) {
    historyRows.textContent = "No inference calls yet.";
  }
}

document.querySelector("#history-toggle").addEventListener("click", async () => {
  historyPanel.hidden = false;
  await loadHistory();
});
document.querySelector("#history-close").addEventListener("click", () => {
  historyPanel.hidden = true;
});

clock();
setInterval(clock, 1000);
tick();
setInterval(tick, 2000);
