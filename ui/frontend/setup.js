const panel = document.querySelector("#panel");
const title = document.querySelector("#title");
const lead = document.querySelector("#lead");
const state = {
  csrf: "",
  code: "",
  checks: [],
  hardware: {},
  models: [],
  plan: { hostname: "rp5-llm", sshPublicKey: "", model: "small", backend: "cpu", exposeLan: false, kiosk: false },
};

function button(label, className, action) {
  const node = document.createElement("button");
  node.type = "button";
  node.className = `button ${className || ""}`.trim();
  node.textContent = label;
  node.addEventListener("click", action);
  return node;
}

function field(label, node) {
  const wrap = document.createElement("label");
  wrap.textContent = label;
  wrap.append(node);
  return wrap;
}

async function session() {
  const response = await fetch("/api/setup/session");
  const payload = await response.json();
  state.csrf = payload.csrf;
  const status = await fetch("/api/status");
  const body = await status.json();
  if (body.setupCode) state.code = body.setupCode;
  const options = await fetch("/api/setup/options");
  const catalog = await options.json();
  state.models = catalog.models || [];
  const check = await fetch("/api/setup/check");
  const report = await check.json();
  state.checks = report.checks || [];
  state.hardware = report.hardware || {};
}

function headers() {
  return {
    "content-type": "application/json",
    "x-csrf-token": state.csrf,
    "x-setup-code": state.code,
  };
}

function welcome() {
  title.textContent = "Welcome to RP5 LLM";
  lead.textContent = "Start here. The inference API stays on this device unless you explicitly expose it.";
  panel.replaceChildren();
  const device = document.createElement("p");
  device.className = "value";
  device.textContent = state.hardware.device || "detecting hardware";
  const detail = document.createElement("p");
  detail.className = "note";
  detail.textContent = `${state.hardware.model || "model unknown"} · ${state.hardware.mem || "RAM unknown"} · ${state.hardware.cpuCores || "?"} cores`;
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(button("Start setup", "primary", systemCheck));
  panel.append(device, detail, actions);
}

function systemCheck() {
  title.textContent = "System check";
  lead.textContent = "Warnings are measurements, not guesses. Vulkan is optional.";
  panel.replaceChildren();
  for (const item of state.checks) {
    const row = document.createElement("div");
    row.className = "check";
    row.innerHTML = `<span>${item.name}</span><span class="${item.status}">${item.status} · ${item.detail}</span>`;
    panel.append(row);
  }
  const code = document.createElement("input");
  code.value = state.code;
  code.autocomplete = "off";
  code.placeholder = "code shown on the device";
  code.addEventListener("input", () => { state.code = code.value.trim(); });
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(button("Continue", "primary", sshStep));
  panel.append(field("Setup code", code), actions);
}

function sshStep() {
  title.textContent = "SSH";
  lead.textContent = "Paste one public key. Private keys are rejected.";
  const input = document.createElement("textarea");
  input.rows = 4;
  input.placeholder = "ssh-ed25519 AAAA...";
  input.value = state.plan.sshPublicKey;
  input.addEventListener("input", () => { state.plan.sshPublicKey = input.value.trim(); });
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(button("Continue", "primary", modelStep));
  panel.replaceChildren(field("Public key", input), actions);
}

function modelStep() {
  title.textContent = "Model";
  lead.textContent = "Only manifest entries are accepted. A missing checksum blocks the download.";
  const select = document.createElement("select");
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "Choose later";
  select.append(none);
  for (const model of state.models) {
    const option = document.createElement("option");
    option.value = model.id;
    const size = model.diskGb ? ` · ~${model.diskGb} GB` : "";
    option.textContent = `${model.name} (${model.profile}${size})`;
    select.append(option);
  }
  select.value = state.plan.model;
  select.addEventListener("change", () => { state.plan.model = select.value; });
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(button("Continue", "primary", accelStep));
  panel.replaceChildren(field("Manifest", select), actions);
}

function accelStep() {
  title.textContent = "Acceleration";
  lead.textContent = "CPU is the stable path. Vulkan stays experimental until a benchmark says otherwise. Auto stays on CPU for now.";
  const select = document.createElement("select");
  for (const [value, label] of [["cpu", "CPU — stable"], ["vulkan", "Vulkan — experimental"], ["auto", "Auto — CPU until a benchmark exists"]]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  }
  select.value = state.plan.backend;
  select.addEventListener("change", () => { state.plan.backend = select.value; });
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(button("Continue", "primary", networkStep));
  panel.replaceChildren(field("Backend", select), actions);
}

function networkStep() {
  title.textContent = "Network access";
  lead.textContent = "Local device only keeps the gateway on 127.0.0.1. Exposing the API puts that gateway on the LAN. llama-server itself stays on localhost.";
  const select = document.createElement("select");
  for (const [value, label] of [["no", "Local device only"], ["yes", "Expose API on LAN"]]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  }
  select.value = state.plan.exposeLan ? "yes" : "no";
  select.addEventListener("change", () => { state.plan.exposeLan = select.value === "yes"; });
  const host = document.createElement("input");
  host.value = state.plan.hostname;
  host.addEventListener("input", () => { state.plan.hostname = host.value.trim(); });
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(button("Install", "primary", install));
  panel.replaceChildren(field("API", select), field("Hostname", host), actions);
}

async function install() {
  title.textContent = "Install";
  lead.textContent = "Saving the plan.";
  panel.textContent = "Working…";
  const response = await fetch("/api/setup/install", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(state.plan),
  });
  const payload = await response.json();
  panel.replaceChildren();
  if (!response.ok) {
    panel.textContent = payload.error || "Setup was rejected.";
    return;
  }
  for (const step of payload.steps || []) {
    const row = document.createElement("div");
    row.className = "check";
    row.innerHTML = `<span>${step.id}</span><span class="${step.status}">${step.status} · ${step.detail}</span>`;
    panel.append(row);
  }
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(button("Finish", "primary", complete));
  panel.append(actions);
}

async function complete() {
  const response = await fetch("/api/setup/complete", { method: "POST", headers: headers(), body: "{}" });
  const payload = await response.json();
  title.textContent = response.ok ? "RP5 LLM is ready" : "Setup still open";
  lead.textContent = response.ok
    ? "Privileged setup routes are locked. llama.cpp still has to be installed before inference works."
    : (payload.error || "Could not lock setup.");
  panel.replaceChildren();
  const link = document.createElement("a");
  link.className = "button primary";
  link.href = "/";
  link.textContent = "Open dashboard";
  panel.append(link);
}

session().then(welcome).catch(() => {
  panel.textContent = "The setup API is not reachable.";
});
