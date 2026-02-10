const SETTINGS_KEY = "homeai-web-settings-v2";
const TOKEN_KEY = "homeai-web-token-v2";
const CUSTOM_STYLES_KEY = "homeai-web-custom-styles-v1";
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

const TERMINAL_JOB_STATUS = new Set(["completed", "failed", "canceled"]);

const ROOM_OPTIONS = [
  { id: "kitchen", name: "Kitchen", icon: "🍳" },
  { id: "living_room", name: "Living Room", icon: "🛋️" },
  { id: "bedroom", name: "Bedroom", icon: "🛏️" },
  { id: "bathroom", name: "Bathroom", icon: "🛁" },
  { id: "dining_room", name: "Dining Room", icon: "🍽️" },
  { id: "home_office", name: "Home Office", icon: "💻" },
  { id: "kids_room", name: "Kids Room", icon: "🧸" },
  { id: "garden", name: "Garden", icon: "🌿" },
  { id: "coffee_shop", name: "Coffee Shop", icon: "☕" },
  { id: "restaurant", name: "Restaurant", icon: "🍷" },
];

const DEFAULT_STYLES = [
  {
    id: "modern",
    name: "Modern",
    prompt: "Modern clean interior, balanced composition, natural light, premium materials.",
    thumbnail: "https://picsum.photos/id/1068/900/900",
  },
  {
    id: "minimalistic",
    name: "Minimalistic",
    prompt: "Minimalist interior, uncluttered surfaces, neutral palette, calm and airy mood.",
    thumbnail: "https://picsum.photos/id/1059/900/900",
  },
  {
    id: "bohemian",
    name: "Bohemian",
    prompt: "Bohemian interior with layered textures, handcrafted decor, warm earthy tones.",
    thumbnail: "https://picsum.photos/id/1044/900/900",
  },
  {
    id: "tropical",
    name: "Tropical",
    prompt: "Tropical style with lush plants, breezy palette, bright daylight and natural woods.",
    thumbnail: "https://picsum.photos/id/1018/900/900",
  },
  {
    id: "rustic",
    name: "Rustic",
    prompt: "Rustic interior with aged wood, cozy lighting, handcrafted details and timeless warmth.",
    thumbnail: "https://picsum.photos/id/1008/900/900",
  },
  {
    id: "vintage",
    name: "Vintage",
    prompt: "Vintage-inspired room, classic furniture silhouettes, rich details and soft filmic mood.",
    thumbnail: "https://picsum.photos/id/1074/900/900",
  },
  {
    id: "baroque",
    name: "Baroque",
    prompt: "Baroque luxury interior, ornate accents, dramatic lighting, rich textures and depth.",
    thumbnail: "https://picsum.photos/id/1080/900/900",
  },
  {
    id: "scandinavian",
    name: "Scandinavian",
    prompt: "Scandinavian design with white walls, warm oak, functional furniture and soft daylight.",
    thumbnail: "https://picsum.photos/id/1025/900/900",
  },
  {
    id: "industrial",
    name: "Industrial",
    prompt: "Industrial loft with exposed materials, black metal accents and cinematic contrast.",
    thumbnail: "https://picsum.photos/id/1067/900/900",
  },
  {
    id: "japandi",
    name: "Japandi",
    prompt: "Japandi room with serene palette, organic forms, low furniture and tactile textures.",
    thumbnail: "https://picsum.photos/id/1015/900/900",
  },
  {
    id: "christmas",
    name: "Christmas",
    prompt: "Festive Christmas interior, warm ambient lights, seasonal decor and cozy atmosphere.",
    thumbnail: "https://picsum.photos/id/1041/900/900",
  },
];

const TOOLS_INSPIRATION = [
  {
    title: "Soft Modern Living",
    subtitle: "Neutral tones, wood accents, calming light",
    image: "https://picsum.photos/id/1063/1200/900",
  },
  {
    title: "Clean Kitchen Lines",
    subtitle: "High-contrast cabinets with premium surfaces",
    image: "https://picsum.photos/id/1080/1200/900",
  },
  {
    title: "Boutique Bedroom",
    subtitle: "Layered textiles and hotel-style atmosphere",
    image: "https://picsum.photos/id/1067/1200/900",
  },
  {
    title: "Natural Japandi",
    subtitle: "Minimal layout with warm organic textures",
    image: "https://picsum.photos/id/1015/1200/900",
  },
];

const state = {
  apiBaseUrl: "",
  userId: "homeai_demo_user",
  token: "",
  currentTab: "tools",
  createStep: 1,
  selectedRoomId: "",
  selectedStyleId: "modern",
  customStyles: [],
  discoverTab: "",
  me: null,
  profile: null,
  board: [],
  discoverFeed: null,
  catalog: [],
  currentJob: null,
  pollHandle: null,
  setupHintShown: false,
};

const refs = {
  settingsToggle: document.getElementById("settingsToggle"),
  connectionBackdrop: document.getElementById("connectionBackdrop"),
  connectionPanel: document.getElementById("connectionPanel"),
  closeSettingsButton: document.getElementById("closeSettingsButton"),
  toggleLogButton: document.getElementById("toggleLogButton"),
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  userId: document.getElementById("userId"),
  loginButton: document.getElementById("loginButton"),
  logoutButton: document.getElementById("logoutButton"),
  refreshButton: document.getElementById("refreshButton"),
  authState: document.getElementById("authState"),
  creditState: document.getElementById("creditState"),
  planState: document.getElementById("planState"),
  tabButtons: Array.from(document.querySelectorAll(".tab-btn")),
  panels: {
    tools: document.getElementById("panel-tools"),
    create: document.getElementById("panel-create"),
    discover: document.getElementById("panel-discover"),
    profile: document.getElementById("panel-profile"),
  },
  jumpToCreate: document.getElementById("jumpToCreate"),
  emptyCreateButton: document.getElementById("emptyCreateButton"),
  inspirationGrid: document.getElementById("inspirationGrid"),
  boardGrid: document.getElementById("boardGrid"),
  boardEmpty: document.getElementById("boardEmpty"),
  createStepLabel: document.getElementById("createStepLabel"),
  stepDots: [
    document.getElementById("stepDot1"),
    document.getElementById("stepDot2"),
    document.getElementById("stepDot3"),
    document.getElementById("stepDot4"),
  ],
  createSteps: [
    document.getElementById("createStep1"),
    document.getElementById("createStep2"),
    document.getElementById("createStep3"),
    document.getElementById("createStep4"),
  ],
  wizardBack: document.getElementById("wizardBack"),
  wizardNext: document.getElementById("wizardNext"),
  wizardClose: document.getElementById("wizardClose"),
  imageUrl: document.getElementById("imageUrl"),
  imagePreviewCard: document.getElementById("imagePreviewCard"),
  loadDemoImage: document.getElementById("loadDemoImage"),
  roomOptions: document.getElementById("roomOptions"),
  styleGrid: document.getElementById("styleGrid"),
  customStyleForm: document.getElementById("customStyleForm"),
  customStyleName: document.getElementById("customStyleName"),
  customStylePrompt: document.getElementById("customStylePrompt"),
  customStyleThumb: document.getElementById("customStyleThumb"),
  createSummary: document.getElementById("createSummary"),
  renderForm: document.getElementById("renderForm"),
  projectId: document.getElementById("projectId"),
  operation: document.getElementById("operation"),
  tier: document.getElementById("tier"),
  targetPart: document.getElementById("targetPart"),
  extraPrompt: document.getElementById("extraPrompt"),
  jobResult: document.getElementById("jobResult"),
  discoverTabs: document.getElementById("discoverTabs"),
  discoverSections: document.getElementById("discoverSections"),
  profileSummary: document.getElementById("profileSummary"),
  catalogCards: document.getElementById("catalogCards"),
  checkoutForm: document.getElementById("checkoutForm"),
  checkoutPlanId: document.getElementById("checkoutPlanId"),
  successUrl: document.getElementById("successUrl"),
  cancelUrl: document.getElementById("cancelUrl"),
  logCard: document.getElementById("logCard"),
  activityLog: document.getElementById("activityLog"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function slugify(value) {
  return String(value)
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function log(message, level = "INFO") {
  const timestamp = new Date().toLocaleTimeString();
  const current = refs.activityLog.textContent === "Waiting for actions..." ? "" : refs.activityLog.textContent;
  const line = `[${timestamp}] [${level}] ${message}`;
  refs.activityLog.textContent = current ? `${line}\n${current}` : line;
  if (level === "ERROR") {
    refs.logCard.classList.remove("hidden");
    if (refs.toggleLogButton) {
      refs.toggleLogButton.textContent = "Hide Logs";
    }
  }
}

function normalizeBaseUrl(raw) {
  return raw.trim().replace(/\/+$/, "");
}

function isLocalHost(hostname = window.location.hostname) {
  return LOCAL_HOSTS.has(String(hostname || "").toLowerCase());
}

function detectDefaultApiBaseUrl() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = normalizeBaseUrl(params.get("apiBaseUrl") || params.get("api") || "");
  if (fromQuery) {
    return fromQuery;
  }
  if (isLocalHost()) {
    return "http://localhost:8000";
  }
  return "";
}

function shouldTreatAsNetworkError(message) {
  const value = String(message || "").toLowerCase();
  return value.includes("failed to fetch") || value.includes("networkerror") || value.includes("load failed");
}

function showSetupHint(message, level = "WARN") {
  if (state.setupHintShown) {
    return;
  }
  state.setupHintShown = true;
  openSettingsPanel();
  log(message, level);
}

function openSettingsPanel() {
  refs.connectionBackdrop.classList.remove("hidden");
  refs.connectionPanel.classList.remove("hidden");
}

function closeSettingsPanel() {
  refs.connectionBackdrop.classList.add("hidden");
  refs.connectionPanel.classList.add("hidden");
}

function readConnectionInputs() {
  state.apiBaseUrl = normalizeBaseUrl(refs.apiBaseUrl.value || "");
  state.userId = refs.userId.value.trim();
  if (state.apiBaseUrl) {
    state.setupHintShown = false;
  }
}

function syncConnectionInputs() {
  refs.apiBaseUrl.value = state.apiBaseUrl;
  refs.userId.value = state.userId;
}

function saveConnectionSettings() {
  localStorage.setItem(
    SETTINGS_KEY,
    JSON.stringify({
      apiBaseUrl: state.apiBaseUrl,
      userId: state.userId,
      currentTab: state.currentTab,
      selectedRoomId: state.selectedRoomId,
      selectedStyleId: state.selectedStyleId,
    }),
  );
}

function loadConnectionSettings() {
  const raw = localStorage.getItem(SETTINGS_KEY);
  if (!raw) {
    syncConnectionInputs();
    return;
  }
  try {
    const parsed = JSON.parse(raw);
    state.apiBaseUrl = normalizeBaseUrl(parsed.apiBaseUrl || state.apiBaseUrl);
    state.userId = parsed.userId || state.userId;
    state.currentTab = parsed.currentTab || state.currentTab;
    state.selectedRoomId = parsed.selectedRoomId || "";
    state.selectedStyleId = parsed.selectedStyleId || state.selectedStyleId;
  } catch (error) {
    log(`Failed to load connection settings: ${error.message}`, "ERROR");
  }
  syncConnectionInputs();
}

function saveToken(token) {
  state.token = token || "";
  if (state.token) {
    sessionStorage.setItem(TOKEN_KEY, state.token);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

function loadToken() {
  saveToken(sessionStorage.getItem(TOKEN_KEY) || "");
}

function saveCustomStyles() {
  localStorage.setItem(CUSTOM_STYLES_KEY, JSON.stringify(state.customStyles));
}

function loadCustomStyles() {
  const raw = localStorage.getItem(CUSTOM_STYLES_KEY);
  if (!raw) {
    return;
  }
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      state.customStyles = parsed
        .filter((item) => item && typeof item === "object")
        .map((item) => ({
          id: String(item.id || ""),
          name: String(item.name || ""),
          prompt: String(item.prompt || ""),
          thumbnail: String(item.thumbnail || ""),
          custom: true,
        }))
        .filter((item) => item.id && item.name && item.prompt && item.thumbnail);
    }
  } catch (error) {
    log(`Failed to load custom styles: ${error.message}`, "ERROR");
  }
}

function getAllStyles() {
  return [...DEFAULT_STYLES, ...state.customStyles];
}

function getSelectedStyle() {
  const styles = getAllStyles();
  return styles.find((item) => item.id === state.selectedStyleId) || styles[0] || null;
}

function getSelectedRoom() {
  return ROOM_OPTIONS.find((item) => item.id === state.selectedRoomId) || null;
}

function setDefaultCheckoutUrls() {
  const base = `${window.location.origin}${window.location.pathname}`;
  refs.successUrl.value = `${base}?checkout=success`;
  refs.cancelUrl.value = `${base}?checkout=cancel`;
}

async function apiRequest(path, { method = "GET", body = undefined, authRequired = true } = {}) {
  if (!state.apiBaseUrl) {
    throw new Error("API Base URL is required.");
  }
  if (authRequired && !state.token) {
    throw new Error("Login is required for this action.");
  }

  const headers = { "Content-Type": "application/json" };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  let response;
  try {
    response = await fetch(`${state.apiBaseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new Error(`Cannot reach API at ${state.apiBaseUrl}. Check API URL, CORS, and server status.`);
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail =
      typeof payload === "string"
        ? payload
        : payload?.detail
          ? typeof payload.detail === "string"
            ? payload.detail
            : JSON.stringify(payload.detail)
          : JSON.stringify(payload);
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return payload;
}

async function trackEvent(eventName, extra = {}) {
  try {
    await apiRequest("/v1/analytics/events", {
      method: "POST",
      authRequired: false,
      body: {
        event_name: eventName,
        user_id: state.userId || null,
        platform: "web",
        ...extra,
      },
    });
  } catch {
    // Never block UX due to analytics transport.
  }
}

function setTab(tab) {
  state.currentTab = tab;
  for (const button of refs.tabButtons) {
    button.classList.toggle("active", button.dataset.tab === tab);
  }
  for (const [name, panel] of Object.entries(refs.panels)) {
    panel.classList.toggle("active", name === tab);
  }
  saveConnectionSettings();
}

function renderStatusPills() {
  if (state.token && state.me) {
    refs.authState.textContent = `Auth: ${state.me.user_id}`;
  } else if (state.token) {
    refs.authState.textContent = "Auth: token ready";
  } else {
    refs.authState.textContent = "Auth: logged out";
  }
  refs.creditState.textContent =
    typeof state.profile?.credits?.balance === "number" ? `Credits: ${state.profile.credits.balance}` : "Credits: -";
  refs.planState.textContent = `Plan: ${state.profile?.effective_plan?.display_name || "-"}`;
}

function renderBoard() {
  if (!Array.isArray(state.board) || state.board.length === 0) {
    refs.boardGrid.innerHTML = "";
    refs.boardEmpty.classList.remove("hidden");
    return;
  }
  refs.boardEmpty.classList.add("hidden");
  refs.boardGrid.innerHTML = state.board
    .map((item) => {
      const image = item.last_output_url || item.cover_image_url || "https://picsum.photos/id/1008/900/700";
      return `<article class="board-card">
        <img src="${escapeHtml(image)}" alt="${escapeHtml(item.project_id)}" />
        <div class="board-copy">
          <p><strong>${escapeHtml(item.project_id)}</strong></p>
          <small>Status: ${escapeHtml(item.last_status || "-")} | Generations: ${escapeHtml(item.generation_count || 0)}</small>
        </div>
      </article>`;
    })
    .join("");
}

function renderToolInspiration() {
  refs.inspirationGrid.innerHTML = TOOLS_INSPIRATION.map((item) => {
    return `<article class="inspiration-card">
      <img src="${escapeHtml(item.image)}" alt="${escapeHtml(item.title)}" />
      <div class="inspiration-copy">
        <h5>${escapeHtml(item.title)}</h5>
        <p>${escapeHtml(item.subtitle)}</p>
      </div>
    </article>`;
  }).join("");
}

function renderRoomOptions() {
  refs.roomOptions.innerHTML = ROOM_OPTIONS.map((room) => {
    const activeClass = room.id === state.selectedRoomId ? "active" : "";
    return `<button type="button" class="room-btn ${activeClass}" data-room-id="${escapeHtml(room.id)}">${escapeHtml(
      room.icon,
    )} ${escapeHtml(room.name)}</button>`;
  }).join("");
}

function renderStyles() {
  const selected = state.selectedStyleId;
  refs.styleGrid.innerHTML = getAllStyles()
    .map((style) => {
      const isActive = style.id === selected;
      const activeClass = isActive ? "active" : "";
      const customClass = style.custom ? "custom" : "";
      const deleteButton = style.custom
        ? `<button type="button" class="delete" data-delete-style-id="${escapeHtml(style.id)}">Delete</button>`
        : "";
      return `<article class="style-card ${activeClass} ${customClass}" data-style-id="${escapeHtml(style.id)}">
        <img src="${escapeHtml(style.thumbnail)}" alt="${escapeHtml(style.name)} thumbnail" />
        <div class="copy">
          <h4>${escapeHtml(style.name)}</h4>
          <p>${escapeHtml(style.prompt)}</p>
          ${deleteButton}
        </div>
      </article>`;
    })
    .join("");
}

function renderImagePreview() {
  const url = refs.imageUrl.value.trim();
  if (!url) {
    refs.imagePreviewCard.innerHTML = '<p class="muted">Image preview appears here.</p>';
    return;
  }
  refs.imagePreviewCard.innerHTML = `<img src="${escapeHtml(url)}" alt="Input preview" />`;
}

function renderCreateSummary() {
  const selectedRoom = getSelectedRoom();
  const selectedStyle = getSelectedStyle();
  const imageUrl = refs.imageUrl.value.trim();
  refs.createSummary.innerHTML = [
    `<p class="summary-line"><span>Image:</span> <strong>${escapeHtml(imageUrl || "-")}</strong></p>`,
    `<p class="summary-line"><span>Room:</span> <strong>${escapeHtml(selectedRoom?.name || "-")}</strong></p>`,
    `<p class="summary-line"><span>Style:</span> <strong>${escapeHtml(selectedStyle?.name || "-")}</strong></p>`,
    `<p class="summary-line"><span>Style Prompt:</span> <strong>${escapeHtml(selectedStyle?.prompt || "-")}</strong></p>`,
  ].join("");
}

function setCreateStep(step) {
  state.createStep = Math.min(Math.max(step, 1), 4);
  refs.createStepLabel.textContent = `Step ${state.createStep} / 4`;
  refs.createSteps.forEach((section, index) => {
    section.classList.toggle("active", index + 1 === state.createStep);
  });
  refs.stepDots.forEach((dot, index) => {
    dot.classList.toggle("active", index + 1 <= state.createStep);
  });
  refs.wizardBack.disabled = state.createStep === 1;
  refs.wizardNext.textContent = state.createStep === 4 ? "Generate Design" : "Continue";
  if (state.createStep === 4) {
    renderCreateSummary();
  }
}

function renderJobResult() {
  const job = state.currentJob;
  if (!job) {
    refs.jobResult.innerHTML = '<p class="muted">No render job yet.</p>';
    return;
  }
  const output = job.output_url
    ? `<img src="${escapeHtml(job.output_url)}" alt="Rendered output" />`
    : '<p class="muted">Rendering in progress. Keep this page open.</p>';
  refs.jobResult.innerHTML = `<p class="job-meta"><strong>${escapeHtml(job.id)}</strong></p>
    <p class="job-meta">Status: ${escapeHtml(job.status)} | Provider: ${escapeHtml(job.provider || "-")}</p>
    <p class="job-meta">Model: ${escapeHtml(job.provider_model || "-")} | Est. Cost: $${Number(
      job.estimated_cost_usd || 0,
    ).toFixed(4)}</p>
    ${output}`;
}

function renderDiscover() {
  const tabs = state.discoverFeed?.tabs || [];
  refs.discoverTabs.innerHTML = [
    `<button type="button" class="discover-pill ${state.discoverTab === "" ? "active" : ""}" data-discover-tab="">All</button>`,
    ...tabs.map((tab) => {
      const isActive = tab.toLowerCase() === state.discoverTab.toLowerCase();
      return `<button type="button" class="discover-pill ${isActive ? "active" : ""}" data-discover-tab="${escapeHtml(
        tab,
      )}">${escapeHtml(tab)}</button>`;
    }),
  ].join("");

  const sections = state.discoverFeed?.sections || [];
  if (sections.length === 0) {
    refs.discoverSections.innerHTML = '<p class="empty-text">No discover items found.</p>';
    return;
  }

  refs.discoverSections.innerHTML = sections
    .map((section) => {
      const items = section.items || [];
      return `<article class="discover-group">
        <h4>${escapeHtml(section.title)}</h4>
        <div class="discover-items">
          ${items
            .map((item) => {
              return `<article class="discover-card">
                <div class="discover-pair">
                  <img src="${escapeHtml(item.before_image_url)}" alt="${escapeHtml(item.title)} before" />
                  <img src="${escapeHtml(item.after_image_url)}" alt="${escapeHtml(item.title)} after" />
                </div>
                <div class="discover-copy">
                  <h5>${escapeHtml(item.title)}</h5>
                  <p>${escapeHtml(item.subtitle)}</p>
                </div>
              </article>`;
            })
            .join("")}
        </div>
      </article>`;
    })
    .join("");
}

function renderCatalog() {
  if (!Array.isArray(state.catalog) || state.catalog.length === 0) {
    refs.catalogCards.innerHTML = '<p class="empty-text">No active plans.</p>';
    refs.checkoutPlanId.innerHTML = "";
    return;
  }
  refs.catalogCards.innerHTML = state.catalog
    .map((plan) => {
      return `<article class="catalog-card">
        <h4>${escapeHtml(plan.display_name)}</h4>
        <p>${escapeHtml(plan.plan_id)} | $${Number(plan.monthly_price_usd || 0).toFixed(2)}/month</p>
        <p>${escapeHtml(plan.daily_credits)} credits/day • preview ${escapeHtml(
          plan.preview_cost_credits,
        )} • final ${escapeHtml(plan.final_cost_credits)}</p>
      </article>`;
    })
    .join("");

  const previous = refs.checkoutPlanId.value;
  refs.checkoutPlanId.innerHTML = state.catalog
    .map((plan) => `<option value="${escapeHtml(plan.plan_id)}">${escapeHtml(plan.display_name)}</option>`)
    .join("");
  if (previous && state.catalog.some((plan) => plan.plan_id === previous)) {
    refs.checkoutPlanId.value = previous;
  }
}

function renderProfile() {
  if (!state.token || !state.profile) {
    refs.profileSummary.innerHTML = '<p class="profile-line"><span>Login to see your profile.</span></p>';
    return;
  }
  refs.profileSummary.innerHTML = [
    `<p class="profile-line"><span>User:</span> <strong>${escapeHtml(state.profile.user_id || "-")}</strong></p>`,
    `<p class="profile-line"><span>Credits:</span> <strong>${escapeHtml(state.profile.credits?.balance || 0)}</strong></p>`,
    `<p class="profile-line"><span>Plan:</span> <strong>${escapeHtml(
      state.profile.effective_plan?.display_name || "-",
    )}</strong></p>`,
    `<p class="profile-line"><span>Status:</span> <strong>${escapeHtml(
      state.profile.entitlement?.status || "-",
    )}</strong></p>`,
    `<p class="profile-line"><span>Source:</span> <strong>${escapeHtml(
      state.profile.entitlement?.source || "-",
    )}</strong></p>`,
  ].join("");
}

function renderAll() {
  renderStatusPills();
  renderToolInspiration();
  renderBoard();
  renderRoomOptions();
  renderStyles();
  renderImagePreview();
  renderCreateSummary();
  renderJobResult();
  renderDiscover();
  renderCatalog();
  renderProfile();
  setCreateStep(state.createStep);
}

function stopPolling() {
  if (state.pollHandle) {
    clearInterval(state.pollHandle);
    state.pollHandle = null;
  }
}

async function pollRenderJob(jobId) {
  const status = await apiRequest(`/v1/ai/render-jobs/${encodeURIComponent(jobId)}`, { authRequired: true });
  state.currentJob = status;
  renderJobResult();
  if (TERMINAL_JOB_STATUS.has(status.status)) {
    stopPolling();
    log(`Render finished: ${status.status}`);
    await refreshAuthenticatedData();
    renderAll();
  }
}

function startPolling(jobId) {
  stopPolling();
  state.pollHandle = setInterval(() => {
    void pollRenderJob(jobId).catch((error) => {
      stopPolling();
      log(`Polling failed: ${error.message}`, "ERROR");
    });
  }, 2500);
}

async function loadDiscover(tab = "") {
  const query = tab ? `?tab=${encodeURIComponent(tab)}` : "";
  state.discoverFeed = await apiRequest(`/v1/discover/feed${query}`, { authRequired: false });
  state.discoverTab = tab;
}

async function loadCatalog() {
  state.catalog = await apiRequest("/v1/subscriptions/catalog", { authRequired: false });
}

async function refreshAuthenticatedData() {
  const bootstrap = await apiRequest("/v1/session/bootstrap/me?board_limit=30&experiment_limit=50", {
    authRequired: true,
  });
  state.me = bootstrap.me || null;
  state.profile = bootstrap.profile || null;
  state.board = bootstrap.board?.projects || [];
  if (Array.isArray(bootstrap.catalog)) {
    state.catalog = bootstrap.catalog;
  }
  if (state.me?.user_id && state.userId !== state.me.user_id) {
    state.userId = state.me.user_id;
    syncConnectionInputs();
    saveConnectionSettings();
  }
}

async function refreshAllData() {
  readConnectionInputs();
  saveConnectionSettings();
  if (!state.apiBaseUrl) {
    state.discoverFeed = { tabs: [], sections: [] };
    state.catalog = [];
    state.me = null;
    state.profile = null;
    state.board = [];
    showSetupHint("Set API Base URL from Settings, then click Refresh or Login.");
    return;
  }
  await Promise.all([loadDiscover(state.discoverTab), loadCatalog()]);
  if (state.token) {
    await refreshAuthenticatedData();
  } else {
    state.me = null;
    state.profile = null;
    state.board = [];
  }
}

function validateCreateStep(step) {
  if (step === 1) {
    const imageUrl = refs.imageUrl.value.trim();
    if (!imageUrl) {
      log("Step 1: image URL is required.", "ERROR");
      return false;
    }
  }
  if (step === 2) {
    if (!state.selectedRoomId) {
      log("Step 2: choose a room.", "ERROR");
      return false;
    }
  }
  if (step === 3) {
    if (!getSelectedStyle()) {
      log("Step 3: choose a style.", "ERROR");
      return false;
    }
  }
  return true;
}

async function submitRender() {
  readConnectionInputs();
  if (!state.token) {
    log("Login first to generate renders.", "ERROR");
    return;
  }
  const style = getSelectedStyle();
  const room = getSelectedRoom();
  if (!style || !room) {
    log("Room and style must be selected before generating.", "ERROR");
    return;
  }

  const projectId = refs.projectId.value.trim() || `web_${Date.now()}`;
  refs.projectId.value = projectId;

  const promptOverrides = {
    room_type: room.id,
    style_name: style.name,
    style_prompt: style.prompt,
  };
  const extraPrompt = refs.extraPrompt.value.trim();
  if (extraPrompt) {
    promptOverrides.user_prompt = extraPrompt;
  }

  const payload = {
    user_id: state.userId,
    platform: "web",
    project_id: projectId,
    image_url: refs.imageUrl.value.trim(),
    style_id: style.id,
    operation: refs.operation.value,
    tier: refs.tier.value,
    target_parts: [refs.targetPart.value],
    prompt_overrides: promptOverrides,
  };

  try {
    const job = await apiRequest("/v1/ai/render-jobs", {
      method: "POST",
      authRequired: true,
      body: payload,
    });
    state.currentJob = job;
    renderJobResult();
    log(`Render started: ${job.id}`);
    if (!TERMINAL_JOB_STATUS.has(job.status)) {
      startPolling(job.id);
    }
    await trackEvent("web_render_submitted", { operation: payload.operation, tier: payload.tier });
  } catch (error) {
    log(`Render failed: ${error.message}`, "ERROR");
  }
}

async function handleCheckoutSubmit(event) {
  event.preventDefault();
  if (!state.token) {
    log("Login first to start checkout.", "ERROR");
    return;
  }
  const planId = refs.checkoutPlanId.value;
  if (!planId) {
    log("No plan selected.", "ERROR");
    return;
  }
  try {
    const session = await apiRequest("/v1/subscriptions/web/checkout-session", {
      method: "POST",
      authRequired: true,
      body: {
        user_id: state.userId,
        plan_id: planId,
        success_url: refs.successUrl.value,
        cancel_url: refs.cancelUrl.value,
      },
    });
    window.open(session.checkout_url, "_blank", "noopener,noreferrer");
    log(`Checkout opened for ${planId}.`);
  } catch (error) {
    log(`Checkout failed: ${error.message}`, "ERROR");
  }
}

async function handleLogin() {
  readConnectionInputs();
  if (!state.userId) {
    log("User ID is required for login.", "ERROR");
    return;
  }
  try {
    const login = await apiRequest("/v1/auth/login-dev", {
      method: "POST",
      authRequired: false,
      body: {
        user_id: state.userId,
        platform: "web",
        ttl_hours: 24 * 30,
      },
    });
    saveToken(login.access_token);
    await refreshAllData();
    renderAll();
    log(`Logged in as ${state.userId}`);
    await trackEvent("web_login_success");
  } catch (error) {
    log(`Login failed: ${error.message}`, "ERROR");
  }
}

async function handleLogout() {
  try {
    if (state.token) {
      await apiRequest("/v1/auth/logout", { method: "POST", authRequired: true });
    }
  } catch (error) {
    log(`Logout warning: ${error.message}`, "ERROR");
  } finally {
    stopPolling();
    saveToken("");
    state.me = null;
    state.profile = null;
    state.board = [];
    state.currentJob = null;
    renderAll();
    log("Logged out.");
  }
}

function addCustomStyle(event) {
  event.preventDefault();
  const name = refs.customStyleName.value.trim();
  const prompt = refs.customStylePrompt.value.trim();
  const thumbnail = refs.customStyleThumb.value.trim();
  if (!name || !prompt || !thumbnail) {
    log("Custom style needs name, prompt and thumbnail URL.", "ERROR");
    return;
  }
  const baseSlug = slugify(name) || "custom-style";
  const id = `custom-${baseSlug}-${Date.now().toString(36).slice(-4)}`;
  state.customStyles.unshift({
    id,
    name,
    prompt,
    thumbnail,
    custom: true,
  });
  state.selectedStyleId = id;
  saveCustomStyles();
  refs.customStyleForm.reset();
  renderStyles();
  renderCreateSummary();
  saveConnectionSettings();
  log(`Custom style added: ${name}`);
}

function removeCustomStyle(styleId) {
  const before = state.customStyles.length;
  state.customStyles = state.customStyles.filter((item) => item.id !== styleId);
  if (state.customStyles.length !== before) {
    if (state.selectedStyleId === styleId) {
      state.selectedStyleId = DEFAULT_STYLES[0]?.id || "";
    }
    saveCustomStyles();
    renderStyles();
    renderCreateSummary();
    saveConnectionSettings();
    log("Custom style removed.");
  }
}

function bindEvents() {
  refs.settingsToggle.addEventListener("click", () => {
    if (refs.connectionPanel.classList.contains("hidden")) {
      openSettingsPanel();
    } else {
      closeSettingsPanel();
    }
  });
  refs.closeSettingsButton.addEventListener("click", () => {
    closeSettingsPanel();
  });
  refs.connectionBackdrop.addEventListener("click", () => {
    closeSettingsPanel();
  });
  refs.toggleLogButton.addEventListener("click", () => {
    const willShow = refs.logCard.classList.contains("hidden");
    refs.logCard.classList.toggle("hidden", !willShow);
    refs.toggleLogButton.textContent = willShow ? "Hide Logs" : "Show Logs";
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !refs.connectionPanel.classList.contains("hidden")) {
      closeSettingsPanel();
    }
  });

  refs.loginButton.addEventListener("click", () => {
    void handleLogin();
  });
  refs.logoutButton.addEventListener("click", () => {
    void handleLogout();
  });
  refs.refreshButton.addEventListener("click", () => {
    void refreshAllData()
      .then(() => {
        renderAll();
        log("Data refreshed.");
      })
      .catch((error) => {
        log(`Refresh failed: ${error.message}`, "ERROR");
      });
  });

  refs.jumpToCreate.addEventListener("click", () => {
    setTab("create");
  });
  if (refs.emptyCreateButton) {
    refs.emptyCreateButton.addEventListener("click", () => {
      setTab("create");
    });
  }

  refs.tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const tab = button.dataset.tab;
      if (!tab) {
        return;
      }
      setTab(tab);
      void trackEvent(`web_tab_opened_${tab}`);
    });
  });

  refs.loadDemoImage.addEventListener("click", () => {
    refs.imageUrl.value = "https://picsum.photos/id/1068/1280/960";
    renderImagePreview();
    log("Demo image loaded.");
  });

  refs.imageUrl.addEventListener("input", () => {
    renderImagePreview();
    renderCreateSummary();
  });

  refs.roomOptions.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-room-id]");
    if (!trigger) {
      return;
    }
    state.selectedRoomId = trigger.dataset.roomId || "";
    renderRoomOptions();
    renderCreateSummary();
    saveConnectionSettings();
  });

  refs.styleGrid.addEventListener("click", (event) => {
    const deleteTrigger = event.target.closest("[data-delete-style-id]");
    if (deleteTrigger) {
      removeCustomStyle(deleteTrigger.dataset.deleteStyleId || "");
      return;
    }
    const trigger = event.target.closest("[data-style-id]");
    if (!trigger) {
      return;
    }
    state.selectedStyleId = trigger.dataset.styleId || "";
    renderStyles();
    renderCreateSummary();
    saveConnectionSettings();
  });

  refs.customStyleForm.addEventListener("submit", addCustomStyle);

  refs.wizardBack.addEventListener("click", () => {
    setCreateStep(state.createStep - 1);
  });
  refs.wizardClose.addEventListener("click", () => {
    setCreateStep(1);
    refs.projectId.value = "";
    refs.extraPrompt.value = "";
    log("Create flow reset.");
  });
  refs.wizardNext.addEventListener("click", () => {
    if (state.createStep < 4) {
      if (!validateCreateStep(state.createStep)) {
        return;
      }
      setCreateStep(state.createStep + 1);
      return;
    }
    if (!validateCreateStep(1) || !validateCreateStep(2) || !validateCreateStep(3)) {
      return;
    }
    void submitRender();
  });

  refs.operation.addEventListener("change", renderCreateSummary);
  refs.tier.addEventListener("change", renderCreateSummary);
  refs.targetPart.addEventListener("change", renderCreateSummary);
  refs.extraPrompt.addEventListener("input", renderCreateSummary);
  refs.projectId.addEventListener("input", renderCreateSummary);

  refs.discoverTabs.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-discover-tab]");
    if (!trigger) {
      return;
    }
    const tab = trigger.dataset.discoverTab || "";
    void loadDiscover(tab)
      .then(() => {
        renderDiscover();
      })
      .catch((error) => {
        log(`Discover refresh failed: ${error.message}`, "ERROR");
      });
  });

  refs.checkoutForm.addEventListener("submit", (event) => {
    void handleCheckoutSubmit(event);
  });
}

async function bootstrap() {
  state.apiBaseUrl = detectDefaultApiBaseUrl();
  loadConnectionSettings();
  loadToken();
  loadCustomStyles();
  setDefaultCheckoutUrls();
  bindEvents();
  setTab(state.currentTab);
  setCreateStep(state.createStep);
  refs.toggleLogButton.textContent = refs.logCard.classList.contains("hidden") ? "Show Logs" : "Hide Logs";

  const checkoutState = new URLSearchParams(window.location.search).get("checkout");
  if (checkoutState === "success") {
    log("Checkout success detected. Refreshing session...");
  } else if (checkoutState === "cancel") {
    log("Checkout canceled.");
  }

  if (!isLocalHost() && state.apiBaseUrl.startsWith("http://localhost")) {
    showSetupHint("Public site detected. `localhost` API URL will not work here. Set production API URL in Settings.");
  }

  try {
    await refreshAllData();
    if (checkoutState === "success" && state.token) {
      await refreshAuthenticatedData();
    }
  } catch (error) {
    log(`Initial load failed: ${error.message}`, "ERROR");
    if (shouldTreatAsNetworkError(error.message) || error.message.includes("Cannot reach API")) {
      showSetupHint("Cannot connect to API. Open Settings and set your production API URL.");
    }
    if (state.token) {
      saveToken("");
    }
  }

  renderAll();
}

void bootstrap();
