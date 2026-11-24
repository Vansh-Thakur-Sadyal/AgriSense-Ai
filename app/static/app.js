/* AgriSense AI - single-page dashboard. Every number shown comes from the API; nothing is demo data. */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const icon = (n, cls = "") => `<span class="material-symbols-outlined ${cls}">${n}</span>`;
const fmt = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? "—" : Number(v).toLocaleString("en-IN", { maximumFractionDigits: d }));
const pct = (v) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`);
const title = (s) => String(s || "").replace(/\b\w/g, (c) => c.toUpperCase());
const dateStr = (ts) => new Date(ts * 1000).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
const C = { green: "#2E8B57", green2: "#62A87C", blue: "#5B9BD5", yellow: "#E8B94F", red: "#E57373", ink: "#24352B", muted: "#718078", line: "#E5ECE6" };
// ---------------- theme (light / dark / follow the device) ----------------
const themePref = () => { try { return localStorage.getItem("theme") || "system"; } catch { return "system"; } };
const isDark = () => themePref() === "dark" || (themePref() === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
function applyTheme() {
  const d = isDark();
  document.documentElement.classList.toggle("dark", d);
  Object.assign(C, d ? { green: "#3aa76b", ink: "#ececee", muted: "#a1a1aa", line: "#2e2e33" } : { green: "#2E8B57", ink: "#24352B", muted: "#718078", line: "#E5ECE6" });
  if (window.Chart) { Chart.defaults.color = C.muted; Chart.defaults.borderColor = C.line; }
}
// Switch theme in place: no re-render, so results, forms and charts on screen are kept.
function setTheme(p) {
  try { localStorage.setItem("theme", p); } catch {}
  applyTheme();
  const d = isDark();
  ["#theme-btn", "#auth-theme"].forEach((sel) => { const b = $(sel); if (b) { b.innerHTML = icon(d ? "light_mode" : "dark_mode"); b.title = d ? "Light mode" : "Dark mode"; } });
  const tp = $("#theme-pick"); if (tp) tp.value = p;
  S.charts.forEach((ch) => {
    try {
      const o = ch.options;
      if (o.plugins?.legend?.labels) o.plugins.legend.labels.color = C.ink;
      Object.values(o.scales || {}).forEach((sc) => {
        if (sc.ticks) sc.ticks.color = C.muted;
        if (sc.grid) sc.grid.color = C.line;
        if (sc.title) sc.title.color = C.muted;
        if (sc.pointLabels) sc.pointLabels.color = C.muted;
        if (sc.angleLines) sc.angleLines.color = C.line;
      });
      ch.update("none");
    } catch {}
  });
}
matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => { if (themePref() === "system") setTheme("system"); });

const S = { user: null, status: null, farms: [], charts: [], chatId: null, cache: {} };
window.LANG = "en";

// ---------------- api ----------------
async function api(path, opts = {}) {
  const o = { credentials: "same-origin", ...opts, headers: { ...(opts.headers || {}) } };
  if (o.body && !(o.body instanceof FormData) && typeof o.body !== "string") {
    o.body = JSON.stringify(o.body);
    o.headers["Content-Type"] = "application/json";
  }
  let r;
  try { r = await fetch(path, o); } catch { throw { error: "Cannot reach the server. Check your connection." }; }
  const ct = r.headers.get("content-type") || "";
  const data = ct.includes("json") ? await r.json() : await r.text();
  if (r.status === 401 && !path.startsWith("/api/auth")) { S.user = null; renderAuth("login"); throw { error: "Please sign in", silent: true }; }
  if (!r.ok) throw typeof data === "object" ? data : { error: data };
  return data;
}
function toast(msg, kind = "ok") {
  const el = document.createElement("div");
  const k = { ok: ["check_circle", "border-primary/30", "text-primary"], err: ["error", "border-alert/40", "text-alert"], info: ["info", "border-sky/40", "text-sky"] }[kind];
  el.className = `card px-4 py-3 flex items-center gap-2 text-sm max-w-sm border ${k[1]}`;
  el.innerHTML = `${icon(k[0], k[2])}<span>${esc(msg)}</span>`;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 4200);
}
function fail(e) { if (!e?.silent) toast(e?.error || "Something went wrong", "err"); }
function showFieldErrors(form, e) {
  $$(".field", form).forEach((f) => { f.classList.remove("invalid"); $(".error", f)?.remove(); });
  Object.entries(e?.fields || {}).forEach(([k, msg]) => {
    const inp = form.querySelector(`[name="${k}"]`);
    const f = inp?.closest(".field");
    if (f) { f.classList.add("invalid"); f.insertAdjacentHTML("beforeend", `<div class="error">${esc(msg)}</div>`); }
  });
}
function modal(html, onMount) {
  const m = $("#modal");
  m.innerHTML = `<div class="card w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">${html}</div>`;
  m.classList.remove("hidden"); m.classList.add("flex");
  m.onclick = (ev) => { if (ev.target === m) closeModal(); };
  onMount && onMount(m);
}
function closeModal() { const m = $("#modal"); m.classList.add("hidden"); m.classList.remove("flex"); m.innerHTML = ""; }
function confirmBox(text, okLabel = "Delete") {
  return new Promise((res) => modal(`<h3 class="text-lg font-semibold mb-2">Please confirm</h3><p class="text-muted text-sm mb-5">${esc(text)}</p>
    <div class="flex justify-end gap-2"><button class="btn btn-ghost" data-no>${t("Cancel")}</button><button class="btn btn-danger" data-yes>${esc(okLabel)}</button></div>`,
    (m) => { $("[data-no]", m).onclick = () => { closeModal(); res(false); }; $("[data-yes]", m).onclick = () => { closeModal(); res(true); }; }));
}
function formData(form) {
  const o = {};
  new FormData(form).forEach((v, k) => { o[k] = typeof v === "string" ? v.trim() : v; });
  $$("input[type=checkbox]", form).forEach((c) => (o[c.name] = c.checked));
  return o;
}
async function busy(btn, fn) {
  const old = btn.innerHTML; btn.disabled = true;
  btn.innerHTML = `${icon("progress_activity", "spin")}<span>Working…</span>`;
  try { return await fn(); } finally { btn.disabled = false; btn.innerHTML = old; }
}
function chart(el, cfg) {
  cfg.options = { responsive: true, maintainAspectRatio: false, ...(cfg.options || {}) };
  cfg.options.plugins = { legend: { labels: { boxWidth: 12, color: C.ink, font: { family: "Inter, system-ui, sans-serif", size: 12 } } }, ...(cfg.options.plugins || {}) };
  // translate legend, axis titles and category labels (cached translations; English until fetched)
  (cfg.data?.datasets || []).forEach((d) => { if (typeof d.label === "string") d.label = TR.now(d.label); });
  if (Array.isArray(cfg.data?.labels)) cfg.data.labels = cfg.data.labels.map((x) => (typeof x === "string" ? TR.now(x) : x));
  Object.values(cfg.options.scales || {}).forEach((sc) => { if (sc.title?.text) sc.title.text = TR.now(sc.title.text); });
  Chart.getChart(el)?.destroy(); // a slower, abandoned render may have drawn on this canvas already
  const c = new Chart(el, cfg); S.charts.push(c); return c;
}
Chart.defaults.font.family = "Inter, Nirmala UI, system-ui, sans-serif"; applyTheme();

// ---------------- layout ----------------
const NAV = [
  ["overview", "dashboard", "Overview"], ["crop", "psychology", "Crop Recommendation"], ["yield", "trending_up", "Yield Prediction"],
  ["fertiliser", "science", "Fertiliser Recommendation"], ["disease", "coronavirus", "Plant Disease Detection"],
  ["assistant", "smart_toy", "AI Farming Assistant"], ["weather", "partly_cloudy_day", "Weather Insights"],
  ["soil", "landslide", "Soil Health"], ["farms", "agriculture", "Farm Management"], ["history", "history", "Prediction History"],
  ["reports", "analytics", "Reports & Analytics"], ["settings", "settings", "Settings"],
];
const PAGES = {};
function shell() {
  const u = S.user;
  TR.keepNames([u.name, ...(u.name || "").split(" ")]);
  $("#root").innerHTML = `
  <aside id="sidebar" class="fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-line flex flex-col">
    <div class="h-16 px-5 flex items-center gap-2.5 border-b border-line">
      <img src="/favicon.svg" class="w-8 h-8" alt=""/>
      <div><div class="font-semibold leading-tight">AgriSense AI</div><div class="text-[11px] text-muted tracking-wide">Smart Farming Intelligence</div></div>
    </div>
    <nav class="flex-1 overflow-y-auto p-3 space-y-0.5">${NAV.map(([k, ic, l]) => `<a href="#/${k}" class="nav-link" data-nav="${k}">${icon(ic)}<span>${t(l)}</span></a>`).join("")}</nav>
    <div class="p-3 border-t border-line space-y-1">
      <div id="model-status" class="px-3 py-2 text-xs text-muted"></div>
      <a href="#/help" class="nav-link" data-nav="help">${icon("help")}<span>${t("Help & Support")}</span></a>
      <div class="flex items-center justify-between px-3 pt-2">
        <div class="flex items-center gap-2 min-w-0"><div class="w-8 h-8 rounded-full bg-mint-2 text-primary-dark flex items-center justify-center font-semibold text-sm shrink-0">${esc(u.name[0]).toUpperCase()}</div>
        <div class="min-w-0"><div class="text-sm font-semibold truncate">${esc(u.name)}</div><div class="text-xs text-muted truncate">${esc(title(u.role.replace("_", " ")))}</div></div></div>
        <button id="logout" class="p-1.5 rounded-lg text-muted hover:text-alert hover:bg-red-50" title="${t("Logout")}">${icon("logout")}</button>
      </div>
    </div>
  </aside>
  <div id="scrim" class="fixed inset-0 bg-ink/20 z-40 hidden lg:hidden"></div>
  <div class="lg:pl-64 min-h-screen flex flex-col">
    <header class="sticky top-0 z-30 h-16 bg-white/90 backdrop-blur border-b border-line flex items-center gap-3 px-4 lg:px-6">
      <button id="menu" class="lg:hidden p-2 -ml-2 rounded-lg hover:bg-mint" aria-label="Menu">${icon("menu")}</button>
      <div class="min-w-0"><div id="crumb" class="text-xs text-muted truncate"></div><div id="page-title" class="font-semibold truncate"></div></div>
      <div class="relative flex-1 max-w-sm ml-auto hidden md:block">
        ${icon("search", "absolute left-3 top-2.5 text-muted")}
        <input id="search" class="w-full bg-mint border border-line rounded-lg pl-10 pr-3 py-2 text-sm outline-none focus:border-primary" placeholder="${t("Search")} pages, crops, prediction #…"/>
        <div id="search-res" class="absolute mt-1 w-full card hidden max-h-80 overflow-y-auto z-50"></div>
      </div>
      <div class="hidden xl:flex items-center gap-1 text-xs text-muted px-3 py-1.5 rounded-full bg-mint border border-line">${icon("calendar_month", "!text-base")}<span>${new Date().toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" })}</span></div>
      <label class="lang-pick" title="Language">${icon("translate", "!text-base text-primary")}${langSelect("lang-sel")}</label>
      <button id="theme-btn" class="p-2 rounded-full hover:bg-mint" title="${isDark() ? "Light mode" : "Dark mode"}">${icon(isDark() ? "light_mode" : "dark_mode")}</button>
      <div class="relative">
        <button id="bell" class="relative p-2 rounded-full hover:bg-mint" title="${t("Notifications")}">${icon("notifications")}<span id="bell-dot" class="hidden absolute top-1 right-1 w-4 h-4 rounded-full bg-alert text-white text-[10px] font-bold flex items-center justify-center"></span></button>
        <div id="bell-pop" class="hidden absolute right-0 mt-2 w-80 card p-3 z-50"></div>
      </div>
      <a href="#/settings" class="w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-semibold" title="${t("Profile")}">${esc(u.name[0]).toUpperCase()}</a>
    </header>
    <main id="view" class="flex-1 p-4 lg:p-6 max-w-[1500px] w-full mx-auto"></main>
  </div>`;
  $("#logout").onclick = async () => { await api("/api/auth/logout", { method: "POST" }).catch(() => {}); S.user = null; location.hash = ""; renderAuth("login"); };
  $("#menu").onclick = () => { $("#sidebar").classList.add("open"); $("#scrim").classList.remove("hidden"); };
  $("#scrim").onclick = closeMenu;
  $("#lang-sel").onchange = (e) => setLang(e.target.value);
  $("#theme-btn").onclick = () => setTheme(isDark() ? "light" : "dark");
  setupSearch(); setupBell(); renderModelStatus();
}
function closeMenu() { $("#sidebar")?.classList.remove("open"); $("#scrim")?.classList.add("hidden"); }
const langSelect = (id) => `<select id="${id}" data-nt aria-label="Language">${LANGS.map(([c, n]) => `<option value="${c}" ${c === LANG ? "selected" : ""}>${n}</option>`).join("")}</select>`;
async function setLang(l) {
  LANG = l; try { localStorage.setItem("lang", l); } catch {}
  document.documentElement.lang = l; document.documentElement.dir = "ltr";
  // Translate in place (and back to English from the stored originals): results and inputs stay on screen.
  if (S.user) { api("/api/me", { method: "PUT", body: { language: l } }).catch(() => {}); S.user.language = l; }
  $$("#lang-sel, #alang, #auth-lang").forEach((s) => (s.value = l));
  TR.restore();
  TR.schedule();
  if (S.onLang) S.onLang();
}
async function renderModelStatus() {
  try {
    S.status = S.status || (await api("/api/status"));
    const m = S.status.models;
    const dot = (ok) => `<span class="inline-block w-2 h-2 rounded-full ${ok ? "bg-primary" : "bg-sun"}"></span>`;
    $("#model-status").innerHTML = `<div class="font-semibold text-ink mb-1">Models</div>
      <div class="grid grid-cols-2 gap-x-2 gap-y-0.5">
      <span>${dot(m.crop.ready)} Crop</span><span>${dot(m.yield.ready)} Yield</span>
      <span>${dot(m.disease.ready)} Disease</span><span>${dot(S.status.assistant)} Assistant</span></div>`;
  } catch {}
}
function setupSearch() {
  const inp = $("#search"), box = $("#search-res");
  inp.oninput = async () => {
    const q = inp.value.trim().toLowerCase();
    if (!q) { box.classList.add("hidden"); return; }
    const pages = NAV.filter(([, , l]) => l.toLowerCase().includes(q) || t(l).includes(q)).map(([k, ic, l]) => ({ href: `#/${k}`, ic, text: t(l) }));
    const farms = S.farms.filter((f) => f.name.toLowerCase().includes(q)).map((f) => ({ href: `#/farm/${f.id}`, ic: "agriculture", text: f.name }));
    let preds = [];
    if (q.length >= 2) {
      try { preds = (await api(`/api/predictions?q=${encodeURIComponent(q.replace(/^#/, ""))}&limit=6`)).predictions.map((p) => ({ href: `#/prediction/${p.id}`, ic: "history", text: `#${p.id} · ${p.kind} · ${p.summary}` })); } catch {}
    }
    const all = [...pages, ...farms, ...preds];
    box.innerHTML = all.length ? all.map((r) => `<a href="${r.href}" class="flex items-center gap-2 px-3 py-2 text-sm hover:bg-mint">${icon(r.ic, "text-muted")}<span class="truncate">${esc(r.text)}</span></a>`).join("") : `<div class="px-3 py-3 text-sm text-muted">No matches</div>`;
    box.classList.remove("hidden");
  };
  inp.onblur = () => setTimeout(() => box.classList.add("hidden"), 200);
  box.onclick = () => { inp.value = ""; box.classList.add("hidden"); };
}
async function setupBell() {
  const pop = $("#bell-pop");
  $("#bell").onclick = (e) => { e.stopPropagation(); pop.classList.toggle("hidden"); };
  document.addEventListener("click", (e) => { if (!pop.contains(e.target)) pop.classList.add("hidden"); });
  pop.innerHTML = `<div class="text-sm text-muted">Loading…</div>`;
  if (!S.user.notify_weather) { pop.innerHTML = `<div class="text-sm text-muted">Weather alerts are off (Settings).</div>`; return; }
  try {
    const w = await api("/api/weather");
    const a = w.alerts;
    $("#bell-dot").textContent = a.length; $("#bell-dot").classList.toggle("hidden", !a.length);
    pop.innerHTML = `<div class="font-semibold text-sm mb-2">${t("Notifications")}</div>` + (a.length
      ? a.map((x) => `<div class="text-sm py-2 border-t border-line"><div class="text-xs text-muted">${esc(x.date)} · ${esc(w.location.label)}</div>${esc(x.text)}</div>`).join("")
      : `<div class="text-sm text-muted">No weather alerts for the next 3 days at ${esc(w.location.label)}.</div>`) +
      `<div class="text-[11px] text-muted mt-2">From the live Open-Meteo forecast.</div>`;
  } catch (e) {
    pop.innerHTML = `<div class="text-sm text-muted">${esc(e.error || "No alerts")}. <a class="text-primary font-semibold" href="#/farms">Add a farm location</a> to get weather alerts.</div>`;
  }
}

// ---------------- routing ----------------
async function route() {
  if (!S.user) return;
  S.charts.forEach((c) => c.destroy()); S.charts = [];
  if (S.map) { S.map.remove(); S.map = null; }
  closeMenu();
  const [name, arg] = (location.hash.replace(/^#\//, "") || "overview").split("/");
  const page = PAGES[name] || PAGES.overview;
  const navKey = { farm: "farms", prediction: "history" }[name] || name;
  $$("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === navKey));
  const item = NAV.find((n) => n[0] === navKey);
  $("#crumb").textContent = `AgriSense AI / ${item ? t(item[2]) : name === "help" ? t("Help & Support") : ""}`;
  $("#page-title").textContent = item ? t(item[2]) : name === "help" ? t("Help & Support") : "";
  // Each visit renders into its own element. If the user moves on before a slow page finishes,
  // that page keeps writing into a detached element instead of overwriting the new page.
  const seq = (S.routeSeq = (S.routeSeq || 0) + 1);
  const host = $("#view");
  const v = document.createElement("div");
  host.replaceChildren(v);
  v.innerHTML = `<div class="space-y-4"><div class="skeleton h-28"></div><div class="grid md:grid-cols-3 gap-4"><div class="skeleton h-40"></div><div class="skeleton h-40"></div><div class="skeleton h-40"></div></div></div>`;
  try { await page(v, arg); } catch (e) { if (seq === S.routeSeq && !e?.silent) v.innerHTML = errorState(e?.error || "This page could not load."); }
  if (seq === S.routeSeq) window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
const header = (h, sub, right = "") => `<div class="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-5"><div><h1 class="text-2xl lg:text-[28px] font-semibold tracking-tight">${esc(h)}</h1><p class="text-muted mt-1 max-w-3xl">${esc(sub)}</p></div><div class="flex flex-wrap gap-2">${right}</div></div>`;
const empty = (ic, text, action = "") => `<div class="flex flex-col items-center justify-center text-center py-10 px-4 text-muted">${icon(ic, "!text-4xl text-secondary mb-2")}<div class="text-sm max-w-sm">${text}</div>${action ? `<div class="mt-4">${action}</div>` : ""}</div>`;
const errorState = (m) => `<div class="card p-8">${empty("cloud_off", esc(m), `<button class="btn btn-ghost" onclick="route()">${icon("refresh")} Retry</button>`)}</div>`;
const note = (text, kind = "info") => `<div class="flex gap-2 p-3 rounded-xl text-sm ${kind === "warn" ? "bg-[#fbf2dc] text-[#6d5214]" : "bg-mint text-[#355443]"}">${icon(kind === "warn" ? "warning" : "info", "!text-lg shrink-0")}<div>${text}</div></div>`;
const farmSelect = (sel = "") => `<div class="field"><label>${t("Farm")} <span class="text-muted font-normal">(optional)</span></label><select name="farm_id"><option value="">— Not linked —</option>${S.farms.map((f) => `<option value="${f.id}" ${String(sel) === String(f.id) ? "selected" : ""}>${esc(f.name)}</option>`).join("")}</select></div>`;
const kindBadge = (k) => ({ crop: `<span class="badge b-green">${icon("psychology", "!text-sm")}Crop</span>`, yield: `<span class="badge b-blue">${icon("trending_up", "!text-sm")}Yield</span>`, fertiliser: `<span class="badge b-yellow">${icon("science", "!text-sm")}Fertiliser</span>`, disease: `<span class="badge b-red">${icon("coronavirus", "!text-sm")}Disease</span>` }[k] || k);
const statusBadge = (s) => `<span class="badge ${s === "completed" ? "b-green" : "b-yellow"}">${esc(title(s))}</span>`;
async function loadFarms() { S.farms = (await api("/api/farms")).farms; TR.keepNames(S.farms.map((f) => f.name)); return S.farms; }

// ---------------- input mode: custom values or a random real sample from the dataset ----------------
const modeBar = (id) => `<div class="seg-bar" id="${id}"><button type="button" data-mode="custom" class="seg active">${icon("edit_note")} Custom input</button><button type="button" data-mode="auto" class="seg">${icon("shuffle")} Auto-fill from dataset</button></div><div id="${id}-src"></div>`;
// onAuto() fetches a sample, fills the form and returns {text} for the source chip; it runs again on "New sample".
function setupMode(id, onAuto, onCustom) {
  const bar = $(`#${id}`), src = $(`#${id}-src`);
  const pick = async (mode) => {
    $$("[data-mode]", bar).forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
    if (mode === "custom") { src.innerHTML = ""; onCustom && onCustom(); return; }
    src.innerHTML = `<div class="src-chip">${icon("progress_activity", "spin !text-base")} Picking a random sample…</div>`;
    try {
      const s = await onAuto();
      src.innerHTML = `<div class="src-chip">${icon("dataset")}<span class="flex-1">${s.text}</span><button type="button" class="font-semibold text-primary whitespace-nowrap" id="${id}-again">${icon("shuffle", "!text-base")} New sample</button></div>`;
      $(`#${id}-again`).onclick = () => pick("auto");
    } catch (e) { src.innerHTML = ""; fail(e); }
  };
  $$("[data-mode]", bar).forEach((b) => (b.onclick = () => pick(b.dataset.mode)));
  return pick;
}
// one-shot hand-over between pages (e.g. Overview -> Fertiliser with a finished result)
function goWith(route, next) { S.next = next; if (location.hash === `#/${route}`) window.route(); else location.hash = `#/${route}`; }
function takeNext() { const n = S.next; S.next = null; return n || {}; }
function askAssistant(question) { goWith("assistant", { ask: question }); }

// Dataset sample -> crop model -> fertiliser for the recommended crop -> Fertiliser page with the full result.
async function runChain(btn, farmId = "") {
  const go = async () => {
    const s = await api("/api/samples/crop");
    const crop = await api("/api/crop/recommend", { method: "POST", body: { ...s.values, farm_id: farmId } });
    const inp = { basis: "crop_profile", crop: crop.crop, N: s.values.N, P: s.values.P, K: s.values.K, ph: s.values.ph, farm_id: farmId };
    const fert = await api("/api/fertiliser", { method: "POST", body: inp });
    return { chain: { sample: s, crop, fert, inp } };
  };
  try { const next = btn ? await busy(btn, go) : await go(); toast("Crop and fertiliser results saved to history"); goWith("fertiliser", next); }
  catch (e) { fail(e); }
}

// ---------------- overview ----------------
PAGES.overview = async (v) => {
  const [o] = await Promise.all([api("/api/overview"), loadFarms()]);
  const k = o.kpis, hr = new Date().getHours();
  const greet = t(hr < 12 ? "Good morning" : hr < 17 ? "Good afternoon" : "Good evening");
  const kpi = (ic, bg, label, val, sub) => `<div class="card p-4 flex flex-col gap-2"><div class="flex items-center justify-between"><span class="text-xs uppercase tracking-wide text-muted font-semibold">${label}</span><span class="w-9 h-9 rounded-lg flex items-center justify-center ${bg}">${icon(ic)}</span></div><div class="text-3xl font-bold tracking-tight">${val}</div><div class="text-xs text-muted">${sub}</div></div>`;
  v.innerHTML = `
  <section class="card p-5 lg:p-6 mb-5 relative z-30">
    <div class="absolute inset-0 overflow-hidden rounded-[16px] pointer-events-none"><div class="absolute -right-10 -top-10 w-64 h-64 rounded-full bg-primary/5"></div></div>
    <div class="relative grid lg:grid-cols-[1fr_auto] gap-5 items-center">
      <div>
        <h1 class="text-3xl lg:text-4xl font-bold tracking-tight">${greet}, <span class="notranslate">${esc(o.user.name.split(" ")[0])}</span>!</h1>
        <p class="text-muted mt-2 max-w-2xl">Monitor your farm, understand your soil and make better decisions with machine learning.</p>
        <div id="ov-loc" class="flex flex-wrap gap-2 mt-3 text-xs"></div>
        <div class="flex flex-wrap gap-2 mt-4 relative">
          <button id="newpred" class="btn btn-primary" aria-haspopup="true" aria-expanded="false">${icon("add_circle")} ${t("New Prediction")} ${icon("expand_more")}</button>
          <div id="newpred-menu" class="hidden absolute top-12 left-0 w-[340px] max-w-[calc(100vw-48px)] card p-2 z-40 shadow-xl">
            <button id="np-chain" class="w-full text-left flex items-start gap-3 p-3 rounded-xl bg-mint hover:bg-mint-2">
              <span class="w-9 h-9 rounded-lg bg-primary text-white flex items-center justify-center shrink-0">${icon("auto_awesome")}</span>
              <span><span class="block text-sm font-semibold">Full auto analysis</span><span class="block text-xs text-muted">Random soil sample from the dataset → crop model → fertiliser for that crop. Opens the fertiliser result.</span></span>
            </button>
            <div class="text-[11px] uppercase tracking-wide text-muted font-semibold px-3 pt-3 pb-1">Or choose a tool</div>
            ${[["crop", "psychology", "Crop Recommendation"], ["yield", "trending_up", "Yield Prediction"], ["fertiliser", "science", "Fertiliser Recommendation"], ["disease", "coronavirus", "Plant Disease Detection"]].map(([h, ic, l]) => `<div class="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-mint"><span class="flex items-center gap-2 flex-1 text-sm">${icon(ic, "text-primary")}${t(l)}</span><button data-np="${h}" data-auto="0" class="np-btn">Custom</button><button data-np="${h}" data-auto="1" class="np-btn np-auto">${icon("shuffle", "!text-sm")} Auto</button></div>`).join("")}
          </div>
          <a href="#/assistant" class="btn btn-ghost">${icon("smart_toy")} ${t("Ask AI Assistant")}</a>
        </div>
      </div>
      <svg viewBox="0 0 220 140" class="hidden lg:block w-56" aria-hidden="true"><rect x="0" y="95" width="220" height="45" rx="10" fill="#e2f2e8"/><path d="M0 105 Q55 85 110 105 T220 100 V140 H0Z" fill="#cfe8d7"/>${[20, 50, 80, 110, 140, 170, 200].map((x) => `<g transform="translate(${x} 92)"><path d="M0 0 V-26" stroke="#2E8B57" stroke-width="2.5"/><path d="M0 -12 Q-10 -18 -12 -28 Q-2 -22 0 -12Z M0 -18 Q10 -24 12 -34 Q2 -28 0 -18Z" fill="#62A87C"/></g>`).join("")}<circle cx="182" cy="30" r="16" fill="#E8B94F" opacity=".85"/></svg>
    </div>
  </section>
  <section class="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-5">
    ${kpi("agriculture", "bg-mint-2 text-primary", t("Registered farms"), String(k.farms).padStart(2, "0"), k.farm_area_ha ? `${fmt(k.farm_area_ha)} ha in total` : "Add your first farm")}
    ${kpi("psychology", "bg-mint-2 text-primary", t("Crop recommendations"), k.crop, "Generated by you")}
    ${kpi("trending_up", "bg-[#e6f0fa] text-sky", t("Avg predicted yield"), k.avg_yield ? `${fmt(k.avg_yield, 2)}<span class="text-base font-medium text-muted"> t/ha</span>` : "—", `${k.yield} ${t("Yield predictions").toLowerCase()}`)}
    ${kpi("science", "bg-[#fbf2dc] text-[#b0861f]", t("Fertiliser checks"), k.fertiliser, "Nutrient-gap checks")}
    ${kpi("coronavirus", "bg-[#fdeceb] text-alert", t("Disease scans"), k.disease, "Leaf images analysed")}
    ${kpi("history", "bg-[#fdf0e4] text-[#c9772f]", "Total predictions", k.total, `<a href="#/history" class="text-primary font-semibold">${t("View all")} →</a>`)}
  </section>
  <section id="ov-weather" class="mb-5"></section>
  <section class="card p-5 mb-5">
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3 mb-4">
      <div><h2 class="text-lg font-semibold">${t("Crop production analytics")}</h2><p class="text-sm text-muted">Government crop production statistics, 1997–2020 (data.gov.in)</p></div>
      <form id="an-form" class="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm"></form>
    </div>
    <div class="grid lg:grid-cols-[2fr_1fr] gap-5"><div class="h-72"><canvas id="an-chart"></canvas></div><div class="h-72"><canvas id="an-donut"></canvas></div></div>
    <div id="an-note" class="text-xs text-muted mt-3"></div>
  </section>
  <section class="grid xl:grid-cols-[2fr_1fr] gap-5">
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3"><h2 class="text-lg font-semibold">${t("Recent predictions")}</h2><a href="#/history" class="text-sm text-primary font-semibold">${t("View all")} →</a></div>
      ${o.recent.length ? `<div class="overflow-x-auto"><table class="tbl"><thead><tr><th>${t("Date")}</th><th>${t("Type")}</th><th>${t("Crop")}</th><th>${t("Result")}</th><th>${t("Confidence")}</th><th>${t("Status")}</th><th></th></tr></thead><tbody>
      ${o.recent.map((p) => `<tr><td class="whitespace-nowrap">${dateStr(p.created_at)}</td><td>${kindBadge(p.kind)}</td><td>${esc(title(p.crop || "—"))}</td><td class="font-medium">${esc(p.summary)}</td><td>${p.confidence != null ? pct(p.confidence) : "—"}</td><td>${statusBadge(p.status)}</td><td><a href="#/prediction/${p.id}" class="text-primary">${icon("visibility")}</a></td></tr>`).join("")}</tbody></table></div>`
      : empty("history", "No predictions yet. Run your first one to see it here.", `<a href="#/crop" class="btn btn-primary">${icon("psychology")} ${t("Crop Recommendation")}</a>`)}
    </div>
    <div class="card p-5 bg-gradient-to-b from-[#f4faf5] to-white">
      <div class="flex items-center gap-2 mb-3">${icon("tips_and_updates", "text-primary")}<h2 class="text-lg font-semibold">${t("AI Farming Insights")}</h2></div>
      <div id="insights" class="space-y-2"></div>
      <a href="#/assistant" class="btn btn-primary w-full mt-4">${icon("smart_toy")} ${t("Ask AI Assistant")}</a>
    </div>
  </section>`;
  const menu = $("#newpred-menu", v);
  const closeNp = () => { menu.classList.add("hidden"); $("#newpred", v).setAttribute("aria-expanded", "false"); };
  $("#newpred", v).onclick = (e) => { e.stopPropagation(); menu.classList.toggle("hidden"); $("#newpred", v).setAttribute("aria-expanded", String(!menu.classList.contains("hidden"))); };
  menu.onclick = (e) => e.stopPropagation();
  const outside = () => { if (!v.isConnected) return document.removeEventListener("click", outside); closeNp(); };
  document.addEventListener("click", outside);
  $$("[data-np]", menu).forEach((b) => (b.onclick = () => { closeNp(); goWith(b.dataset.np, { auto: b.dataset.auto === "1" }); }));
  $("#np-chain", v).onclick = () => { closeNp(); runChain($("#newpred", v), S.farms[0]?.id || ""); };
  const ins = [...o.insights];
  // weather card
  const wbox = $("#ov-weather");
  try {
    const w = await api("/api/weather");
    $("#ov-loc").innerHTML = `<span class="badge b-grey">${icon("location_on", "!text-sm")}${esc(w.location.label)}</span><span class="badge b-blue">${icon("thermostat", "!text-sm")}${fmt(w.current.temp)}°C · ${esc(w.current.condition)}</span>`;
    wbox.innerHTML = weatherCard(w);
    w.alerts.forEach((a) => ins.unshift({ type: "weather", text: a.text }));
  } catch (e) {
    wbox.innerHTML = `<div class="card p-5">${empty("partly_cloudy_day", "Add a farm with its location to see live weather here.", `<a href="#/farms" class="btn btn-ghost">${icon("add")} ${t("Add farm")}</a>`)}</div>`;
  }
  const insIcon = { weather: ["rainy", "b-blue"], soil: ["science", "b-yellow"], disease: ["coronavirus", "b-red"] };
  $("#insights").innerHTML = ins.length ? ins.map((i) => `<div class="p-3 rounded-xl bg-white border border-line text-sm flex gap-2">${icon(insIcon[i.type][0], "text-primary shrink-0")}<span>${esc(i.text)}</span></div>`).join("")
    : `<div class="text-sm text-muted">Insights appear here from your live weather, last fertiliser check and last leaf scan. Nothing needs your attention right now.</div>`;
  await analyticsBlock();
};
function wIcon(code) {
  if (code === 0) return "clear_day"; if (code <= 2) return "partly_cloudy_day"; if (code === 3) return "cloud";
  if (code <= 48) return "foggy"; if (code <= 67 || (code >= 80 && code <= 82)) return "rainy"; if (code <= 77) return "weather_snowy"; return "thunderstorm";
}
function weatherCard(w) {
  const c = w.current;
  const tile = (ic, l, v) => `<div class="p-3 rounded-xl bg-white/70 border border-[#dbe8f5]"><div class="text-xs text-muted flex items-center gap-1">${icon(ic, "!text-base text-sky")}${l}</div><div class="font-semibold mt-1">${v}</div></div>`;
  return `<div class="card weather-grad p-5">
    <div class="flex flex-col lg:flex-row gap-5">
      <div class="flex items-center gap-4 lg:w-72 shrink-0">${icon(wIcon(c.code), "!text-6xl text-sky")}<div><div class="text-4xl font-bold">${fmt(c.temp)}°C</div><div class="text-sm text-muted">${esc(c.condition)} · ${esc(w.location.label)}</div></div></div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2 flex-1">${tile("humidity_percentage", t("Humidity"), `${fmt(c.humidity, 0)}%`)}${tile("rainy", "Rain now", `${fmt(c.rain_mm)} mm`)}${tile("air", "Wind", `${fmt(c.wind_kmh)} km/h`)}${tile("wb_twilight", "Sunrise / sunset", `${esc(w.sunrise)} / ${esc(w.sunset)}`)}</div>
    </div>
    <div class="grid grid-cols-4 md:grid-cols-7 gap-2 mt-4">${w.days.map((d, i) => `<div class="p-2 rounded-xl text-center ${(d.rain_mm || 0) >= 20 ? "bg-[#fdeceb]" : "bg-white/70"} border border-[#dbe8f5]"><div class="text-xs text-muted">${i === 0 ? "Today" : new Date(d.date).toLocaleDateString("en-IN", { weekday: "short", day: "numeric" })}</div>${icon(wIcon(d.code), "!text-2xl text-sky my-1")}<div class="text-sm font-semibold">${fmt(d.tmax, 0)}° / ${fmt(d.tmin, 0)}°</div><div class="text-[11px] text-sky">${fmt(d.rain_mm)} mm · ${d.rain_prob ?? "—"}%</div></div>`).join("")}</div>
    <div class="text-[11px] text-muted mt-3">Live forecast · Open-Meteo · updated ${esc(c.time.replace("T", " "))} (${esc(w.timezone)})</div>
  </div>`;
}
async function analyticsBlock() {
  S.cache.yopt = S.cache.yopt || (await api("/api/yield/options"));
  const o = S.cache.yopt, f = $("#an-form");
  const sel = (n, opts, label) => `<select name="${n}" class="border border-line rounded-lg px-2 py-1.5 bg-white"><option value="">${label}: ${t("All")}</option>${opts.map((x) => `<option>${esc(x)}</option>`).join("")}</select>`;
  f.innerHTML = sel("state", o.State, t("State")) + `<select name="district" class="border border-line rounded-lg px-2 py-1.5 bg-white"><option value="">${t("District")}: ${t("All")}</option></select>` + sel("crop", o.Crop, t("Crop")) + sel("season", o.Season, t("Season"));
  if (S.user.state && o.State.includes(S.user.state)) f.state.value = S.user.state;
  if (o.Crop.includes("Rice")) f.crop.value = "Rice";
  let line, donut;
  const load = async () => {
    const q = new URLSearchParams(Object.fromEntries(Object.entries(formData(f)).filter(([, v]) => v)));
    const d = await api(`/api/analytics/production?${q}`);
    const s = d.series;
    line?.destroy(); donut?.destroy();
    if (!s.length) { $("#an-note").textContent = "No rows match these filters."; return; }
    line = chart($("#an-chart"), { data: { labels: s.map((r) => r.year), datasets: [
      { type: "bar", label: "Production (thousand t)", data: s.map((r) => r.production / 1000), backgroundColor: "#cfe8d7", yAxisID: "y", borderRadius: 4 },
      { type: "line", label: "Yield (t/ha)", data: s.map((r) => r.yield), borderColor: C.green, backgroundColor: C.green, yAxisID: "y1", tension: .3, pointRadius: 2 },
      { type: "line", label: "Area (thousand ha)", data: s.map((r) => r.area / 1000), borderColor: C.blue, borderDash: [4, 4], yAxisID: "y", tension: .3, pointRadius: 0 }] },
      options: { interaction: { mode: "index", intersect: false }, scales: { y: { title: { display: true, text: "thousand t / ha" }, grid: { color: "#f0f4f1" } }, y1: { position: "right", title: { display: true, text: "t/ha" }, grid: { display: false } } } } });
    const tc = d.top_crops_by_area;
    donut = chart($("#an-donut"), { type: "doughnut", data: { labels: tc.map((r) => r.crop), datasets: [{ data: tc.map((r) => Math.round(r.area)), backgroundColor: [C.green, C.green2, C.blue, C.yellow, "#9ccfb0", "#a9c8ea", "#f0d48f", C.red] }] },
      options: { cutout: "62%", plugins: { title: { display: true, text: "Crop mix by area, 2019-20 (top 8)", color: C.ink }, legend: { position: "bottom" } } } });
    $("#an-note").textContent = `${s.reduce((a, r) => a + r.n, 0).toLocaleString("en-IN")} district-season records. Crops reported in bales/nuts are excluded; the 2020-21 year is incomplete in the source.`;
  };
  f.state.onchange = async () => {
    f.district.innerHTML = `<option value="">${t("District")}: ${t("All")}</option>`;
    if (f.state.value) (await api(`/api/yield/districts?state=${encodeURIComponent(f.state.value)}`)).districts.forEach((d) => f.district.insertAdjacentHTML("beforeend", `<option>${esc(d)}</option>`));
    load().catch(fail);
  };
  ["district", "crop", "season"].forEach((n) => (f[n].onchange = () => load().catch(fail)));
  if (f.state.value) await f.state.onchange(); else await load();
}

// ---------------- crop recommendation ----------------
const CROP_FIELDS = [
  ["N", "Nitrogen (N)", "ratio", "Nitrogen content of the soil (dataset scale, commonly read as kg/ha)."],
  ["P", "Phosphorus (P)", "ratio", "Phosphorus content of the soil (dataset scale)."],
  ["K", "Potassium (K)", "ratio", "Potassium content of the soil (dataset scale)."],
  ["temperature", "Temperature", "°C", "Average air temperature during the growing period."],
  ["humidity", "Humidity", "%", "Average relative humidity."],
  ["ph", "Soil pH", "", "Acidity of the soil: below 7 acidic, above 7 alkaline."],
  ["rainfall", "Rainfall", "mm", "Rainfall expected over the growing period."],
];
PAGES.crop = async (v) => {
  await loadFarms();
  S.cache.cropinfo = S.cache.cropinfo || (await api("/api/crop/info"));
  const fr = S.cache.cropinfo.feature_ranges;
  v.innerHTML = header(t("AI Crop Recommendation"), "Find suitable crops for your soil nutrients and climate.") + `
  <div class="grid xl:grid-cols-[420px_1fr] gap-5">
    <form id="cf" class="card p-5 space-y-4 self-start" novalidate>
      ${modeBar("cmode")}
      <div class="grid grid-cols-2 gap-3">${CROP_FIELDS.map(([n, l, u, tip]) => `<div class="field ${n === "rainfall" ? "col-span-2" : ""}"><label title="${esc(tip)}">${t(l)} ${u ? `<span class="text-muted font-normal">(${u})</span>` : ""} ${icon("info", "!text-sm text-muted cursor-help")}</label><input name="${n}" type="number" step="any" required placeholder="${fmt(fr[n].min, 0)} – ${fmt(fr[n].max, 0)}"/><div class="hint">${esc(tip)}</div></div>`).join("")}</div>
      ${farmSelect()}
      <div class="flex flex-wrap gap-2">
        <button class="btn btn-primary flex-1" id="cgo">${icon("auto_awesome")} ${t("Predict Suitable Crop")}</button>
        <button type="button" class="btn btn-ghost" id="cweather" title="Fill temperature, humidity and rainfall from the live forecast">${icon("cloud_download")} Weather</button>
        <button type="reset" class="btn btn-ghost">${t("Clear")}</button>
      </div>
      ${note("Training ranges are shown as placeholders. Values outside them are flagged, because the model has never seen such inputs.")}
    </form>
    <div id="cres">${empty("psychology", "Enter your soil and climate values to get a recommendation.")}</div>
  </div>`;
  const f = $("#cf");
  $("#cweather").onclick = async () => {
    try {
      const w = await api(`/api/weather${f.farm_id.value ? `?farm_id=${f.farm_id.value}` : ""}`);
      f.temperature.value = (w.days.reduce((a, d) => a + (d.tmax + d.tmin) / 2, 0) / w.days.length).toFixed(1);
      f.humidity.value = w.current.humidity;
      toast(`Filled from the 7-day forecast at ${w.location.label}. Rainfall is seasonal - enter it yourself.`, "info");
    } catch (e) { fail(e); }
  };
  let sample = null;
  const pick = setupMode("cmode", async () => {
    sample = await api("/api/samples/crop");
    CROP_FIELDS.forEach(([n]) => (f[n].value = sample.values[n]));
    showFieldErrors(f, {});
    f.requestSubmit();
    return { text: `Row ${sample.row} of ${fmt(sample.of, 0)} in <b>${esc(sample.source)}</b> · grown there: <b>${esc(title(sample.label))}</b>` };
  }, () => { sample = null; f.reset(); $("#cres").innerHTML = empty("psychology", "Enter your soil and climate values to get a recommendation."); });
  f.onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await busy($("#cgo"), () => api("/api/crop/recommend", { method: "POST", body: formData(f) }));
      showFieldErrors(f, {}); renderCrop(r, sample); toast("Recommendation saved to history");
    } catch (er) { showFieldErrors(f, er); fail(er); }
  };
  if (takeNext().auto) pick("auto");
};
function renderCrop(r, sample) {
  const labels = { N: "N", P: "P", K: "K", temperature: "Temp", humidity: "Humidity", ph: "pH", rainfall: "Rain" };
  const best = r.top[0];
  const f = $("#cf");
  const agree = sample && sample.label === r.crop;
  $("#cres").innerHTML = `
  ${sample ? `<div class="mb-4">${note(`Dataset sample row ${sample.row}: this soil was recorded growing <b>${esc(title(sample.label))}</b>. The model ${agree ? "<b>agrees</b>" : `recommends <b>${esc(title(r.crop))}</b> instead`}.`, agree ? "info" : "warn")}</div>` : ""}
  <div class="card p-5 mb-5 next-card"><div class="flex flex-col md:flex-row md:items-center gap-3"><span class="w-10 h-10 rounded-xl bg-[#fbf2dc] text-[#b0861f] flex items-center justify-center shrink-0">${icon("science")}</span><div class="flex-1"><div class="font-semibold">Next: which fertiliser does ${esc(title(r.crop))} need here?</div><div class="text-sm text-muted">Compares these N, P, K values with the typical range for ${esc(title(r.crop))} and opens the Fertiliser page with the result.</div></div><button id="tofert" class="btn btn-primary">${icon("science")} Recommend fertiliser</button></div></div>
  <div class="card p-5 mb-5">
    <div class="flex flex-wrap items-center gap-2 mb-3"><span class="badge b-green">${icon("verified", "!text-sm")} Top match · ${pct(r.confidence)} model probability</span><span class="badge b-grey">Prediction #${r.id}</span><span class="badge b-grey">${esc(r.model)} · ${pct(r.model_accuracy)} test accuracy</span></div>
    <div class="grid md:grid-cols-[1fr_280px] gap-5 items-center">
      <div>
        <div class="text-xs uppercase tracking-wide text-muted font-semibold">Recommended crop</div>
        <div class="text-4xl font-bold text-primary-dark mt-1">${esc(title(r.crop))}</div>
        <p class="text-sm mt-3">${r.in_band.length ? `Your <b>${r.in_band.map((k) => labels[k]).join(", ")}</b> fall within the range where ${esc(r.crop)} was grown in the training data.` : ""}
        ${r.out_of_band.length ? ` <b>${r.out_of_band.map((k) => labels[k]).join(", ")}</b> ${r.out_of_band.length > 1 ? "are" : "is"} outside that typical range.` : ""}</p>
        ${r.outside_training_range.length ? `<div class="mt-3">${note(`<b>${r.outside_training_range.map((k) => labels[k]).join(", ")}</b> ${r.outside_training_range.length > 1 ? "are" : "is"} outside the whole training range, so treat this result with caution.`, "warn")}</div>` : ""}
      </div>
      <div class="h-64"><canvas id="radar"></canvas></div>
    </div>
  </div>
  <div class="card p-5 mb-5"><h3 class="font-semibold mb-3">Alternative crops</h3><div class="grid sm:grid-cols-3 gap-3">${r.top.slice(1).map((a, i) => `<div class="p-4 rounded-xl border border-line"><div class="flex justify-between text-xs text-muted"><span>Rank #${i + 2}</span><span class="badge b-green">${pct(a.probability)}</span></div><div class="text-xl font-semibold mt-1">${esc(title(a.crop))}</div><div class="text-xs text-muted mt-1">Suitability avg ${fmt(Object.values(a.suitability).reduce((x, y) => x + y, 0) / 7, 0)}/100</div></div>`).join("")}</div></div>
  <div class="card p-5"><h3 class="font-semibold mb-3">Input vs. typical range for ${esc(r.crop)}</h3><div class="overflow-x-auto"><table class="tbl"><thead><tr><th>Factor</th><th>Your value</th><th>Typical (10th–90th pct)</th><th>Suitability</th></tr></thead><tbody>
  ${Object.keys(labels).map((k) => `<tr><td>${labels[k]}</td><td class="font-semibold">${fmt($("#cf")[k].value, 2)}</td><td>${fmt(r.profile[k].p10, 1)} – ${fmt(r.profile[k].p90, 1)}</td><td><div class="flex items-center gap-2"><div class="h-1.5 w-28 bg-line rounded-full overflow-hidden"><div class="h-full ${best.suitability[k] >= 100 ? "bg-primary" : best.suitability[k] > 50 ? "bg-sun" : "bg-alert"}" style="width:${best.suitability[k]}%"></div></div><span class="text-xs">${fmt(best.suitability[k], 0)}</span></div></td></tr>`).join("")}</tbody></table></div>
  <div class="mt-4">${note("Recommendations are model estimates from a public dataset. Check them against local agronomic advice (your KVK) before sowing.")}</div>
  <div class="flex flex-wrap gap-2 mt-4"><a class="btn btn-ghost" href="/api/reports/pdf?pid=${r.id}">${icon("picture_as_pdf")} ${t("Download PDF")}</a><a class="btn btn-ghost" href="#/prediction/${r.id}">${icon("visibility")} Details</a></div></div>`;
  $("#tofert").onclick = async () => {
    const inp = { basis: "crop_profile", crop: r.crop, N: f.N.value, P: f.P.value, K: f.K.value, ph: f.ph.value, farm_id: f.farm_id.value };
    try { const fert = await busy($("#tofert"), () => api("/api/fertiliser", { method: "POST", body: inp })); goWith("fertiliser", { chain: { sample, crop: r, fert, inp } }); }
    catch (e) { fail(e); }
  };
  chart($("#radar"), { type: "radar", data: { labels: Object.values(labels), datasets: r.top.slice(0, 2).map((a, i) => ({ label: title(a.crop), data: Object.keys(labels).map((k) => a.suitability[k]), borderColor: i ? C.blue : C.green, backgroundColor: i ? "rgba(91,155,213,.12)" : "rgba(46,139,87,.18)", pointRadius: 2 })) },
    options: { scales: { r: { min: 0, max: 100, ticks: { display: false }, grid: { color: C.line }, angleLines: { color: C.line } } }, plugins: { legend: { position: "bottom" } } } });
}

// ---------------- yield ----------------
PAGES.yield = async (v) => {
  await loadFarms();
  S.cache.yopt = S.cache.yopt || (await api("/api/yield/options"));
  const o = S.cache.yopt, yr = new Date().getFullYear();
  const opts = (a) => a.map((x) => `<option>${esc(x)}</option>`).join("");
  v.innerHTML = header(t("Crop Yield Prediction"), "Estimate expected yield from location, crop, season, area and past district yields.") + `
  <div class="grid xl:grid-cols-[400px_1fr] gap-5">
    <form id="yf" class="card p-5 space-y-3 self-start" novalidate>
      ${modeBar("ymode")}
      <div class="field"><label>${t("State")}</label><select name="state" required><option value="">Select…</option>${opts(o.State)}</select></div>
      <div class="field"><label>${t("District")}</label><select name="district" required><option value="">Select a state first</option></select></div>
      <div class="grid grid-cols-2 gap-3"><div class="field"><label>${t("Crop")}</label><select name="crop" required><option value="">Select…</option>${opts(o.Crop)}</select></div>
      <div class="field"><label>${t("Season")}</label><select name="season" required><option value="">Select…</option>${opts(o.Season)}</select></div></div>
      <div class="grid grid-cols-2 gap-3"><div class="field"><label>${t("Year")} <span class="text-muted font-normal">(crop year start)</span></label><input name="year" type="number" value="${yr}" min="1998" max="${yr + 1}"/></div>
      <div class="field"><label>${t("Cultivated area")} <span class="text-muted font-normal">(ha)</span></label><input name="area_ha" type="number" step="any" min="0" placeholder="e.g. 2.5"/></div></div>
      ${farmSelect()}
      <div class="flex gap-2"><button class="btn btn-primary flex-1" id="ygo">${icon("insights")} ${t("Predict Crop Yield")}</button><button type="button" class="btn btn-ghost" id="yfarm">${t("Use farm data")}</button></div>
      ${note("Your area only scales production; the model itself works at district level. The source dataset has <b>no weather or soil columns</b>, so this model does not use rainfall, temperature or soil values. Those are shown on the Weather and Soil pages instead.")}
    </form>
    <div id="yres">${empty("trending_up", "Choose a district, crop and season to estimate yield.")}</div>
  </div>
  <div id="ycard" class="card p-5 mt-5"></div>`;
  const f = $("#yf");
  const fillDistricts = async (pick) => {
    f.district.innerHTML = `<option value="">Select…</option>`;
    if (!f.state.value) return;
    (await api(`/api/yield/districts?state=${encodeURIComponent(f.state.value)}`)).districts.forEach((d) => f.district.insertAdjacentHTML("beforeend", `<option>${esc(d)}</option>`));
    if (pick) f.district.value = pick.toUpperCase();
  };
  f.state.onchange = () => fillDistricts().catch(fail);
  if (S.user.state && o.State.includes(S.user.state)) { f.state.value = S.user.state; await fillDistricts(S.user.district); }
  $("#yfarm").onclick = async () => {
    const farm = S.farms.find((x) => String(x.id) === f.farm_id.value) || S.farms[0];
    if (!farm) return toast("Add a farm first (Farm Management)", "info");
    f.farm_id.value = farm.id;
    if (farm.state && o.State.includes(farm.state)) { f.state.value = farm.state; await fillDistricts(farm.district); }
    if (farm.area_ha) f.area_ha.value = farm.area_ha;
    const crop = o.Crop.find((c) => c.toLowerCase() === (farm.current_crop || "").toLowerCase()); if (crop) f.crop.value = crop;
    toast(`Filled from ${farm.name}`, "info");
  };
  let sample = null;
  const pick = setupMode("ymode", async () => {
    sample = await api("/api/samples/yield");
    f.state.value = sample.state; await fillDistricts(sample.district);
    f.crop.value = sample.crop; f.season.value = sample.season; f.year.value = sample.year; f.area_ha.value = sample.area_ha;
    showFieldErrors(f, {});
    f.requestSubmit();
    return { text: `<b>${esc(title(sample.district.toLowerCase()))}, ${esc(sample.state)}</b> · ${esc(sample.crop)} · ${esc(sample.season)} ${sample.year} from <b>${esc(sample.source)}</b>. Farm area ${sample.area_ha} ha is an example (${esc(sample.area_note.split(", so")[0].toLowerCase())}).` };
  }, () => { sample = null; f.reset(); $("#yres").innerHTML = empty("trending_up", "Choose a district, crop and season to estimate yield."); });
  f.onsubmit = async (e) => {
    e.preventDefault();
    try { const r = await busy($("#ygo"), () => api("/api/yield/predict", { method: "POST", body: formData(f) })); showFieldErrors(f, {}); renderYield(r, formData(f), sample); toast("Prediction saved to history"); }
    catch (er) { showFieldErrors(f, er); fail(er); }
  };
  modelCardYield();
  if (takeNext().auto) pick("auto");
};
const FEAT_NAMES = { State: "State", District: "District", Crop: "Crop", Season: "Season", log_area: "Area (log)", lag1: "Last year's yield", lag2: "Yield two years ago", lag_trend: "Yield trend", lag_mean3: "3-year average yield", lag_count: "Years of history", dist_crop_mean: "District long-run average", state_crop_lag1: "State yield last year", area_change: "Change in area" };
function renderYield(r, inp, sample) {
  const top = r.contributions.slice(0, 6);
  const biggest = top.filter((c) => Math.abs(c.contribution) > 0.01).slice(0, 2).map((c) => FEAT_NAMES[c.feature]);
  const same = sample && Number(inp.year) === sample.year && inp.crop === sample.crop && inp.district === sample.district && inp.season === sample.season;
  const diff = same ? (r.yield_t_ha - sample.recorded_yield_t_ha) / sample.recorded_yield_t_ha : null;
  $("#yres").innerHTML = `
  ${same ? `<div class="mb-4">${note(`The dataset recorded <b>${fmt(sample.recorded_yield_t_ha, 2)} t/ha</b> for this district, crop, season and year. The model says ${fmt(r.yield_t_ha, 2)} t/ha (${diff >= 0 ? "+" : ""}${(diff * 100).toFixed(1)}%). The deployed model was refit on all years, so this record was part of its training data; the honest error on unseen years is on the model card below.`)}</div>` : ""}`;
  $("#yres").innerHTML += `
  <div class="grid md:grid-cols-3 gap-4 mb-5">
    <div class="card p-5 md:col-span-1"><div class="text-xs uppercase tracking-wide text-muted font-semibold">Predicted yield</div><div class="text-4xl font-bold text-primary-dark mt-1">${fmt(r.yield_t_ha, 2)}<span class="text-lg text-muted font-medium"> t/ha</span></div><div class="text-sm text-muted mt-1">80% interval ${fmt(r.interval_80[0], 2)} – ${fmt(r.interval_80[1], 2)} t/ha</div>${r.category ? `<span class="badge ${r.category.startsWith("above") ? "b-green" : r.category.startsWith("below") ? "b-yellow" : "b-blue"} mt-2">${esc(title(r.category))}</span>` : ""}</div>
    <div class="card p-5"><div class="text-xs uppercase tracking-wide text-muted font-semibold">Estimated production</div><div class="text-3xl font-bold mt-1">${r.production_t != null ? fmt(r.production_t, 1) : "—"}<span class="text-base text-muted font-medium"> t</span></div><div class="text-sm text-muted mt-1">predicted yield × your ${fmt(inp.area_ha, 2)} ha</div></div>
    <div class="card p-5"><div class="text-xs uppercase tracking-wide text-muted font-semibold">District history</div><div class="text-3xl font-bold mt-1">${r.district_mean_t_ha != null ? fmt(r.district_mean_t_ha, 2) : "—"}<span class="text-base text-muted font-medium"> t/ha</span></div><div class="text-sm text-muted mt-1">average over ${r.years_of_history} year(s)</div></div>
  </div>
  ${r.years_of_history < 3 ? `<div class="mb-5">${note(`Only ${r.years_of_history} past year(s) exist for this district, crop and season, so the estimate leans on state and national averages and is less reliable.`, "warn")}</div>` : ""}
  <div class="grid lg:grid-cols-2 gap-5">
    <div class="card p-5"><h3 class="font-semibold mb-3">Predicted vs. historical yield</h3><div class="h-64"><canvas id="yhist"></canvas></div></div>
    <div class="card p-5"><h3 class="font-semibold mb-1">Why this number (SHAP)</h3><p class="text-sm text-muted mb-3">${biggest.length ? `<b>${biggest.join("</b> and <b>")}</b> moved this prediction the most.` : "No single factor dominated."} Bars show each feature's push on the log-ratio to the recent average (green raises, red lowers).</p><div class="h-56"><canvas id="yshap"></canvas></div></div>
  </div>
  <div class="flex flex-wrap gap-2 mt-4"><a class="btn btn-ghost" href="/api/reports/pdf?pid=${r.id}">${icon("picture_as_pdf")} ${t("Download PDF")}</a><a class="btn btn-ghost" href="#/prediction/${r.id}">${icon("visibility")} Details</a></div>`;
  const h = r.district_history.slice(-15);
  chart($("#yhist"), { type: "line", data: { labels: [...h.map((x) => x.year), Number(inp.year)], datasets: [
    { label: "Recorded yield", data: [...h.map((x) => x.yield), null], borderColor: C.green2, backgroundColor: C.green2, tension: .25 },
    { label: "Prediction", data: [...h.map(() => null), r.yield_t_ha], borderColor: C.green, backgroundColor: C.green, pointRadius: 6, pointStyle: "rectRot" },
    { label: "80% interval", data: [...h.map(() => null), r.interval_80[1]], borderColor: "transparent", backgroundColor: "rgba(46,139,87,.25)", pointRadius: 4, pointStyle: "line" }] },
    options: { scales: { y: { title: { display: true, text: "t/ha" } } } } });
  chart($("#yshap"), { type: "bar", data: { labels: top.map((c) => FEAT_NAMES[c.feature] + (c.value != null ? ` = ${fmt(c.value, 2)}` : c.label ? ` = ${c.label}` : "")), datasets: [{ data: top.map((c) => c.contribution), backgroundColor: top.map((c) => (c.contribution >= 0 ? C.green : C.red)), borderRadius: 4 }] },
    options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { title: { display: true, text: "contribution (log-ratio)" } } } } });
}
async function modelCardYield() {
  try {
    const c = await api("/api/models/yield");
    const rows = Object.entries(c.results).filter(([k]) => !k.includes("rows with"));
    $("#ycard").innerHTML = `<h3 class="font-semibold mb-1">How good is the yield model?</h3><p class="text-sm text-muted mb-3">${esc(c.validation)}. ${fmt(c.rows_train, 0)} training and ${fmt(c.rows_test, 0)} test records. The model must beat simple baselines to be worth using:</p>
    <div class="grid lg:grid-cols-2 gap-5"><div class="overflow-x-auto"><table class="tbl"><thead><tr><th>Method</th><th>R²</th><th>MAE (t/ha)</th><th>Median % error</th></tr></thead><tbody>${rows.map(([k, m]) => `<tr class="${k.startsWith("LightGBM") ? "font-semibold" : ""}"><td>${esc(k)}</td><td>${m.r2}</td><td>${m.mae_t_ha}</td><td>${m.mape_median_pct}%</td></tr>`).join("")}</tbody></table>
    <p class="text-xs text-muted mt-2">Baselines needing past years are scored only on rows that have them (${fmt(c.results["Baseline: last year's yield"].rows, 0)}); on those same rows the model's MAE is ${c.results["LightGBM on rows with a lag"].mae_t_ha} t/ha.</p></div>
    <div><div class="h-56"><canvas id="yimp"></canvas></div><p class="text-xs text-muted mt-1">Global feature importance (share of split gain).</p></div></div>`;
    const imp = c.importance_gain.slice(0, 8);
    chart($("#yimp"), { type: "bar", data: { labels: imp.map((i) => FEAT_NAMES[i.feature] || i.feature), datasets: [{ data: imp.map((i) => i.importance * 100), backgroundColor: C.green2, borderRadius: 4 }] }, options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { title: { display: true, text: "% of gain" } } } } });
  } catch { $("#ycard").remove(); }
}

// ---------------- fertiliser ----------------
PAGES.fertiliser = async (v) => {
  await loadFarms();
  S.cache.cropinfo = S.cache.cropinfo || (await api("/api/crop/info"));
  const crops = S.cache.cropinfo.classes;
  v.innerHTML = header(t("Smart Fertiliser Recommendation"), "Find which nutrients are short and get a fertiliser suggestion from the model.") + `
  <div class="grid xl:grid-cols-[420px_1fr] gap-5">
    <form id="ff" class="card p-5 space-y-3 self-start" novalidate>
      ${modeBar("fmode")}
      <button type="button" id="fchain" class="w-full text-left flex items-center gap-3 p-3 rounded-xl border border-line hover:border-primary hover:bg-mint">
        <span class="w-9 h-9 rounded-lg bg-primary text-white flex items-center justify-center shrink-0">${icon("auto_awesome")}</span>
        <span class="flex-1"><span class="block text-sm font-semibold">Full analysis from the dataset</span><span class="block text-xs text-muted">Random soil sample → crop model picks the crop → fertiliser for that crop</span></span>${icon("chevron_right", "text-muted")}
      </button>
      <div class="field"><label>What are your N, P, K numbers?</label><select name="basis"><option value="soil_test">Soil test report — available nutrients in kg/ha</option><option value="crop_profile">Same scale as Crop Recommendation</option><option value="fertiliser_dataset">Nutrient need — fertiliser dataset scale</option></select><div class="hint" id="basis-hint"></div></div>
      <div class="grid grid-cols-2 gap-3">
        <div class="field"><label>${t("Crop")}</label><select name="crop" required><option value="">Select…</option>${crops.map((c) => `<option value="${c}">${esc(title(c))}</option>`).join("")}</select></div>
        <div class="field"><label>Soil type <span class="text-muted font-normal">(optional)</span></label><select name="soil_type"><option value="">—</option>${["Alluvial", "Black", "Red", "Laterite", "Sandy", "Loamy", "Clayey"].map((s) => `<option>${s}</option>`).join("")}</select></div>
      </div>
      <div class="grid grid-cols-3 gap-3">${["N", "P", "K"].map((n) => `<div class="field"><label>${n}</label><input name="${n}" type="number" step="any" min="0" required/></div>`).join("")}</div>
      <div class="grid grid-cols-2 gap-3">
        <div class="field"><label>${t("Soil pH")} <span class="text-muted font-normal">(optional)</span></label><input name="ph" type="number" step="any"/></div>
        <div class="field"><label>Organic carbon % <span class="text-muted font-normal">(optional)</span></label><input name="organic_carbon" type="number" step="any"/></div>
      </div>
      <details class="text-sm"><summary class="cursor-pointer text-primary font-semibold py-1">Optional context</summary>
        <div class="grid grid-cols-2 gap-3 mt-2">
          <div class="field"><label>Growth stage</label><select name="growth_stage"><option value="">—</option><option>Pre-sowing</option><option>Vegetative</option><option>Flowering</option><option>Fruiting</option></select></div>
          <div class="field"><label>Irrigation</label><select name="irrigation"><option value="">—</option><option>Rainfed</option><option>Flood</option><option>Sprinkler</option><option>Drip</option></select></div>
          <div class="field col-span-2"><label>Previous crop</label><input name="previous_crop" placeholder="e.g. Chickpea"/></div>
        </div><p class="text-xs text-muted mt-1">Recorded with the result for your reference; the rules do not use them.</p></details>
      ${farmSelect()}
      <button class="btn btn-primary w-full" id="fgo">${icon("science")} ${t("Get Recommendation")}</button>
    </form>
    <div id="fres">${empty("science", "Enter your soil nutrient values to see their status.")}</div>
  </div>`;
  const f = $("#ff");
  S.cache.meta = S.cache.meta || (await api("/api/meta/options"));
  const fcrops = S.cache.meta.fertiliser_crop_types || [];
  let cropList = "";
  const setCrops = () => {  // the fertiliser dataset has its own crop types; the other bases use the 22 crops
    const list = f.basis.value === "fertiliser_dataset" ? fcrops.map((c) => [c, c]) : crops.map((c) => [c, title(c)]);
    const key = list.map((x) => x[0]).join();
    if (key === cropList) return;
    const keep = f.crop.value; cropList = key;
    f.crop.innerHTML = `<option value="">${f.basis.value === "fertiliser_dataset" ? "— (optional)" : "Select…"}</option>` + list.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("");
    f.crop.required = f.basis.value !== "fertiliser_dataset";
    if (list.some((x) => x[0] === keep)) f.crop.value = keep;
  };
  const hint = () => {
    setCrops();
    $("#basis-hint").textContent = {
      soil_test: "Each nutrient is compared with the middle of the Soil Health Card medium band; the shortfall goes to the fertiliser model.",
      crop_profile: "Each nutrient is compared with the chosen crop's typical level in the crop dataset; the shortfall goes to the fertiliser model.",
      fertiliser_dataset: "The numbers you need to supply, on the scale of the fertiliser dataset (N and P 0–42, K 0–19). They go to the model as they are.",
    }[f.basis.value];
  };
  f.basis.onchange = hint; hint();
  let sample = null;
  const fill = (inp) => { Object.entries(inp).forEach(([k, val]) => { if (f[k] && val != null) f[k].value = val; }); hint(); };
  const pick = setupMode("fmode", async () => {
    sample = await api("/api/samples/fertiliser");
    f.basis.value = "fertiliser_dataset"; hint();
    fill({ crop: sample.crop_type, N: sample.values.N, P: sample.values.P, K: sample.values.K, ph: "", organic_carbon: "" });
    if ([...f.soil_type.options].some((o) => o.value === sample.soil_type)) f.soil_type.value = sample.soil_type;
    showFieldErrors(f, {});
    f.requestSubmit();
    return { text: `Row ${sample.row} of ${fmt(sample.of, 0)} in <b>${esc(sample.source)}</b> · ${esc(sample.crop_type)}, ${esc(sample.soil_type)} soil, N ${sample.values.N}, P ${sample.values.P}, K ${sample.values.K} · the dataset records <b>${esc(sample.label)}</b>` };
  }, () => { sample = null; f.reset(); hint(); $("#fres").innerHTML = empty("science", "Enter your soil nutrient values to see their status."); });
  $("#fchain").onclick = () => runChain($("#fchain"), f.farm_id.value);
  f.onsubmit = async (e) => {
    e.preventDefault();
    try { const r = await busy($("#fgo"), () => api("/api/fertiliser", { method: "POST", body: formData(f) })); showFieldErrors(f, {}); renderFert(r, formData(f), sample && f.basis.value === "fertiliser_dataset" ? sample : null); toast("Saved to history"); }
    catch (er) { showFieldErrors(f, er); fail(er); }
  };
  const next = takeNext();
  if (next.chain) {
    const c = next.chain;
    fill(c.inp);
    renderFert(c.fert, c.inp);
    $("#fres").insertAdjacentHTML("afterbegin", chainCard(c));
    $("#chain-again").onclick = () => runChain($("#chain-again"), f.farm_id.value);
  } else if (next.auto) pick("auto");
};
function chainCard(c) {
  const s = c.sample, cr = c.crop, fe = c.fert;
  const step = (n, ic, head, body) => `<div class="chain-step"><div class="flex items-center gap-2 mb-2"><span class="chain-n">${n}</span>${icon(ic, "text-primary")}<span class="text-xs uppercase tracking-wide text-muted font-semibold">${head}</span></div>${body}</div>`;
  return `<div class="card p-5 mb-5 next-card">
    <div class="flex flex-wrap items-center justify-between gap-2 mb-4"><div><div class="font-semibold text-lg">Crop → fertiliser analysis</div><div class="text-sm text-muted">${s ? "From a random soil sample in the dataset" : "From your crop recommendation"}; both results are saved to your history.</div></div>
    <div class="flex gap-2">${s ? `<button id="chain-again" class="btn btn-ghost">${icon("shuffle")} New sample</button>` : `<span id="chain-again" class="hidden"></span>`}</div></div>
    <div class="grid md:grid-cols-3 gap-3 chain">
      ${step(1, "dataset", s ? `Soil sample · row ${s.row}` : "Your soil values", `<div class="grid grid-cols-4 gap-1 text-xs">${["N", "P", "K", "ph"].map((k) => `<div class="p-1.5 rounded-lg bg-white text-center"><div class="text-muted">${k === "ph" ? "pH" : k}</div><div class="font-semibold">${fmt(c.inp[k], 1)}</div></div>`).join("")}</div>${s ? `<div class="text-xs text-muted mt-2">${fmt(s.values.temperature, 1)} °C · ${fmt(s.values.humidity, 0)}% humidity · ${fmt(s.values.rainfall, 0)} mm. Recorded crop: <b>${esc(title(s.label))}</b></div>` : ""}`)}
      ${step(2, "psychology", "Crop model", `<div class="text-2xl font-bold text-primary-dark">${esc(title(cr.crop))}</div><div class="text-xs text-muted mt-1">${pct(cr.confidence)} probability · ${esc(cr.model)}${s ? (s.label === cr.crop ? " · matches the dataset" : ` · dataset says ${esc(title(s.label))}`) : ""}</div><a href="#/prediction/${cr.id}" class="text-xs text-primary font-semibold mt-2 inline-block">Open crop result #${cr.id} →</a>`)}
      ${step(3, "science", "Fertiliser", `${fe.fertiliser?.name ? `<div class="text-2xl font-bold text-primary-dark">${esc(fe.fertiliser.name)}</div><div class="text-xs text-muted mt-1">${esc(fe.fertiliser.grade)} · ${pct(fe.fertiliser.confidence)} model confidence</div>` : `<div class="text-base font-bold leading-snug">${esc(fe.category)}</div>`}<div class="flex flex-wrap gap-1 mt-2">${["N", "P", "K"].map((k) => statusChip(k, fe.status[k])).join("")}</div>`)}
    </div></div>`;
}
function ring(value, max, color, label, sub) {
  const r = 50, c = 2 * Math.PI * r, p = Math.max(0.04, Math.min(1, value / max));
  return `<div class="flex flex-col items-center"><div class="ring-wrap"><svg width="120" height="120"><circle cx="60" cy="60" r="${r}" fill="none" stroke="${C.line}" stroke-width="10"/><circle cx="60" cy="60" r="${r}" fill="none" stroke="${color}" stroke-width="10" stroke-linecap="round" stroke-dasharray="${c * p} ${c}"/></svg><div class="ring-label"><div class="text-xl font-bold">${fmt(value, 1)}</div><div class="text-[11px] text-muted">${esc(sub)}</div></div></div><div class="mt-2 font-semibold text-sm">${esc(label)}</div></div>`;
}
const STATUS_COL = { short: "b-red", low: "b-red", needed: "b-red", adequate: "b-green", none: "b-green", above: "b-yellow", high: "b-yellow" };
const statusChip = (k, st) => `<span class="badge ${STATUS_COL[st] || "b-grey"}">${k} ${esc(t(st || ""))}</span>`;
// The question the "Ask the assistant" button sends - carries the model's suggestion so the chat can explain it.
function fertQuestion(r, inp, lead = "") {
  const fz = r.fertiliser || {};
  const nut = ["N", "P", "K"].map((n) => `${n} ${inp[n]} (${r.status[n]})`).join(", ");
  return `${lead} My fertiliser result${r.id ? ` #${r.id}` : ""}${inp.crop ? ` for ${title(inp.crop)}` : ""}: ${nut}. `
    + (fz.name ? `The model suggests ${fz.name} (${fz.grade}, ${fz.supplies}) with ${pct(fz.confidence)} confidence. Explain why this fertiliser fits, how it is usually applied, and what I should confirm with my KVK.`
              : "No fertiliser was suggested because nothing is short. How should I maintain soil fertility?");
}
function renderFert(r, inp, sample = null) {
  const names = { N: "Nitrogen (N)", P: "Phosphorus (P)", K: "Potassium (K)" };
  const fz = r.fertiliser || {};
  const bridged = r.basis !== "fertiliser_dataset" && r.typical;
  const rows = ["N", "P", "K"].map((n) => {
    if (!bridged) return `<div><div class="flex justify-between text-sm"><span>${t(names[n])}</span><span class="font-semibold">${fmt(r.need[n], 1)}</span></div><div class="bar"><span style="width:${Math.min(100, (r.need[n] / 42) * 100)}%"></span></div></div>`;
    const sf = r.shortfall[n] || 0;
    return `<div><div class="flex justify-between items-center text-sm gap-2"><span>${t(names[n])} ${statusChip("", r.status[n])}</span><span class="text-muted">${fmt(r.values[n], 1)} / ${t("typical")} ${fmt(r.typical[n], 1)} ${esc(r.unit === "kg/ha" ? "kg/ha" : "")}</span></div>
      <div class="bar"><span style="width:${Math.max(2, sf * 100)}%;background:${sf > 0 ? C.red : C.green}"></span></div><div class="text-xs text-muted mt-0.5">${sf > 0 ? `${(sf * 100).toFixed(0)}% ${t("short")}` : t("no shortfall")}</div></div>`;
  }).join("");
  const top = (fz.top || []).map((x) => `<div><div class="flex justify-between text-sm"><span>${esc(x.name)} <span class="text-muted text-xs">${esc(x.grade || "")}</span></span><span class="font-semibold">${pct(x.probability)}</span></div><div class="bar"><span style="width:${x.probability * 100}%;background:${x.name === fz.name ? C.green : "#cfe8d7"}"></span></div></div>`).join("");
  const match = sample ? (sample.label === fz.name ? `${t("The dataset records")} <b>${esc(sample.label)}</b> — ${t("the model got it right.")}` : `${t("The dataset records")} <b>${esc(sample.label)}</b>; ${t("the model suggests")} <b>${esc(fz.name || "none")}</b>.`) : "";
  $("#fres").innerHTML = `
  <div class="card p-5 mb-5">
    <div class="flex flex-wrap gap-2 mb-2"><span class="badge b-green">${icon("model_training", "!text-sm")} ${esc(r.engine)}</span><span class="badge b-grey">#${r.id}</span></div>
    ${match ? `<div class="mb-3">${note(match)}</div>` : ""}
    <div class="text-xs uppercase tracking-wide text-muted font-semibold">${t("Suggested fertiliser")}</div>
    ${fz.name ? `<div class="flex flex-wrap items-end gap-x-4 gap-y-1 mt-1"><div class="text-4xl font-bold text-primary-dark">${esc(fz.name)}</div><div class="text-sm text-muted pb-1">${esc(fz.grade)} (N-P-K) · ${esc(t(fz.supplies))}</div></div>
      <div class="flex flex-wrap gap-2 mt-2"><span class="badge ${fz.confidence >= 0.5 ? "b-green" : "b-yellow"}">${pct(fz.confidence)} ${t("model confidence")}</span>${fz.filtered ? `<span class="badge b-grey">${t("Model's first choice")}: ${esc(fz.model_first_choice)} (${t("does not supply every short nutrient")})</span>` : ""}</div>`
      : `<div class="text-3xl font-bold text-primary-dark mt-1">${esc(t(r.category))}</div><p class="text-sm text-muted mt-1">${esc(t(r.summary))}</p>`}
    <div class="flex flex-wrap gap-2 mt-4"><button class="btn btn-primary" id="fask">${icon("smart_toy")} ${t("Ask the assistant about this")}</button><a class="btn btn-ghost" href="/api/reports/pdf?pid=${r.id}">${icon("picture_as_pdf")} ${t("Download PDF")}</a><a class="btn btn-ghost" href="#/prediction/${r.id}">${icon("visibility")} ${t("Details")}</a></div>
  </div>
  <div class="grid lg:grid-cols-2 gap-5">
    <div class="card p-5"><h3 class="font-semibold mb-3">${bridged ? t("Nutrient shortfall") : t("Nutrient need")}</h3><div class="space-y-3">${rows}</div>
      <ul class="text-sm space-y-1.5 mt-4">${r.explanation.map((x) => `<li class="flex gap-2">${icon("chevron_right", "text-primary !text-base")}<span>${esc(x)}</span></li>`).join("")}</ul>
      <p class="text-xs text-muted mt-3"><b>${t("Typical level")}:</b> ${esc(r.source)}</p></div>
    <div class="card p-5">${top ? `<h3 class="font-semibold mb-3">${t("Model's top 3")}</h3><div class="space-y-3">${top}</div>` : ""}
      <h3 class="font-semibold mt-4 mb-1">${t("How the model got its input")}</h3><p class="text-sm text-muted">${esc(r.bridge)}</p>
      ${r.notes.length ? `<h3 class="font-semibold mt-4 mb-2">${t("Notes")}</h3><ul class="text-sm space-y-1.5">${r.notes.map((x) => `<li class="p-2.5 rounded-lg bg-mint">${esc(x)}</li>`).join("")}</ul>` : ""}</div>
  </div>
  <div class="mt-5">${note("<b>Choosing a fertiliser is not the same as calculating the dose.</b> Use a soil test and your locally validated recommendation (KVK / state agriculture department) before applying any fertiliser. This tool never suggests quantities.", "warn")}</div>`;
  $("#fask").onclick = () => askAssistant(fertQuestion(r, inp));
}

// ---------------- disease ----------------
PAGES.disease = async (v) => {
  await loadFarms();
  const cls = (await api("/api/disease/classes")).classes;
  const crops = [...new Set(cls.map((c) => c[0]))];
  v.innerHTML = header(t("AI Plant Disease Detection"), "Upload a photo of a single leaf to screen for common diseases.") + `
  <div class="grid xl:grid-cols-[420px_1fr] gap-5">
    <div class="card p-5 self-start space-y-4">
      ${modeBar("dmode")}
      <label id="drop" class="drop rounded-2xl p-6 flex flex-col items-center justify-center text-center cursor-pointer min-h-[220px]">
        <input id="file" type="file" accept="image/jpeg,image/png" class="hidden"/>
        <div id="drop-inner">${icon("add_photo_alternate", "!text-5xl text-secondary")}<div class="font-semibold mt-2">Drop a leaf photo or click to upload</div><div class="text-xs text-muted mt-1">JPG, JPEG or PNG · up to 8 MB</div></div>
      </label>
      ${farmSelect()}
      <div class="flex gap-2"><button id="dgo" class="btn btn-primary flex-1" disabled>${icon("biotech")} ${t("Analyse Image")}</button><button id="dclear" class="btn btn-ghost" disabled>${icon("delete")} Remove</button></div>
      ${note("Works best with one leaf, filling the frame, on a plain background, in daylight.")}
      <details class="text-sm"><summary class="cursor-pointer text-primary font-semibold">Crops the model knows (${crops.length})</summary><p class="text-muted mt-2">${crops.map(esc).join(", ")}. A photo of any other crop cannot be diagnosed correctly.</p></details>
    </div>
    <div id="dres">${empty("coronavirus", "Upload a leaf image to see the result.")}</div>
  </div>`;
  let file = null;
  const inp = $("#file"), drop = $("#drop");
  const set = (f) => {
    if (!f) return;
    if (!/^image\/(jpeg|png)$/.test(f.type)) return toast("Please choose a JPG or PNG image", "err");
    if (f.size > 8 * 1024 * 1024) return toast("Image must be under 8 MB", "err");
    file = f; $("#drop-inner").innerHTML = `<img src="${URL.createObjectURL(f)}" class="max-h-52 rounded-xl mx-auto" alt="preview"/><div class="text-xs text-muted mt-2 truncate max-w-full">${esc(f.name)}</div>`;
    $("#dgo").disabled = false; $("#dclear").disabled = false;
  };
  inp.onchange = () => set(inp.files[0]);
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => set(e.dataTransfer.files[0]));
  $("#dclear").onclick = () => { file = null; inp.value = ""; PAGES.disease(v); };
  let sample = null;
  $("#dgo").onclick = async () => {
    const fd = new FormData(); fd.append("image", file); fd.append("farm_id", $("[name=farm_id]", v).value);
    try { const r = await busy($("#dgo"), () => api("/api/disease", { method: "POST", body: fd })); renderDisease(r, URL.createObjectURL(file), sample); toast("Saved to history"); } catch (e) { fail(e); }
  };
  const pick = setupMode("dmode", async () => {
    sample = await api("/api/samples/leaf");
    const blob = await (await fetch(sample.url, { credentials: "same-origin" })).blob();
    set(new File([blob], `dataset_${sample.class}.jpg`, { type: blob.type || "image/jpeg" }));
    $("#dgo").click();
    return { text: `Random leaf photo from the <b>${esc(sample.source)}</b> · true label hidden until the result is shown` };
  }, () => { sample = null; file = null; inp.value = ""; $("#drop-inner").innerHTML = `${icon("add_photo_alternate", "!text-5xl text-secondary")}<div class="font-semibold mt-2">Drop a leaf photo or click to upload</div><div class="text-xs text-muted mt-1">JPG, JPEG or PNG · up to 8 MB</div>`; $("#dgo").disabled = true; $("#dclear").disabled = true; $("#dres").innerHTML = empty("coronavirus", "Upload a leaf image to see the result."); });
  inp.onchange = () => { sample = null; set(inp.files[0]); };
  if (takeNext().auto) pick("auto");
};
function renderDisease(r, src, sample) {
  const b = r.best;
  const truth = sample ? (sample.class === b.class && r.verdict !== "uncertain"
    ? `Dataset label: <b>${esc(sample.crop)} — ${esc(sample.condition)}</b>. The model got it <b>right</b>.`
    : r.verdict === "uncertain" ? `Dataset label: <b>${esc(sample.crop)} — ${esc(sample.condition)}</b>. The model declined to answer (below its confidence threshold).`
    : `Dataset label: <b>${esc(sample.crop)} — ${esc(sample.condition)}</b>. The model said ${esc(b.crop)} — ${esc(b.condition)}.`) : "";
  const verdict = {
    healthy: ["b-green", "check_circle", "Healthy leaf", `${b.crop} — no disease detected`],
    diseased: ["b-red", "coronavirus", "Disease detected", `${b.crop} — ${b.condition}`],
    uncertain: ["b-yellow", "help", "Not sure", "The model is not confident enough to name a disease"],
    no_leaf: ["b-grey", "hide_image", "No leaf found", "This does not look like a leaf photo"],
  }[r.verdict];
  $("#dres").innerHTML = `${truth ? `<div class="mb-4">${note(truth, sample.class === b.class ? "info" : "warn")}</div>` : ""}<div class="card p-5"><div class="grid md:grid-cols-2 gap-5">
    <div><img src="${src}" class="w-full rounded-xl border border-line object-contain max-h-80 bg-mint" alt="uploaded leaf"/></div>
    <div>
      <span class="badge ${verdict[0]}">${icon(verdict[1], "!text-sm")} ${verdict[2]}</span>
      <div class="text-2xl font-bold mt-2">${esc(verdict[3])}</div>
      ${r.verdict === "uncertain" ? `<p class="text-sm text-muted mt-1">Top guess ${esc(b.crop)} — ${esc(b.condition)} at ${pct(b.probability)} is below the ${pct(r.threshold)} confidence the model needs to answer. Try a clearer photo of one leaf.</p>` : `<p class="text-sm text-muted mt-1">Model confidence ${pct(b.probability)} (answers only at ≥ ${pct(r.threshold)}).</p>`}
      <div class="h-44 mt-3"><canvas id="dconf"></canvas></div>
    </div></div>
    ${r.info && r.verdict === "diseased" ? `<div class="grid md:grid-cols-3 gap-3 mt-5"><div class="p-4 rounded-xl bg-mint"><div class="text-xs font-semibold text-muted uppercase mb-1">Cause</div><div class="text-sm">${esc(r.info.cause)}</div></div><div class="p-4 rounded-xl bg-mint"><div class="text-xs font-semibold text-muted uppercase mb-1">Symptoms</div><div class="text-sm">${esc(r.info.symptoms)}</div></div><div class="p-4 rounded-xl bg-mint"><div class="text-xs font-semibold text-muted uppercase mb-1">Next steps</div><div class="text-sm">${esc(r.info.management)}</div></div></div>` : ""}
    <div class="mt-5">${note("AI detection is an initial screening tool. Confirm uncertain results with an agricultural expert, especially when the image is unclear or the crop is outside the model's training classes.", "warn")}</div>
    <div class="flex gap-2 mt-4"><a class="btn btn-ghost" href="/api/reports/pdf?pid=${r.id}">${icon("picture_as_pdf")} ${t("Download PDF")}</a><button class="btn btn-ghost" id="dask">${icon("smart_toy")} Ask the assistant</button></div></div>`;
  $("#dask").onclick = () => askAssistant(r.verdict === "diseased" ? `My ${b.crop} leaf was diagnosed with ${b.condition} (${pct(b.probability)} confidence, result #${r.id}). How do I confirm it in the field and what can I do now, without chemical doses?`
    : r.verdict === "healthy" ? `My ${b.crop} leaf looks healthy according to the disease model (result #${r.id}). What should I keep monitoring this season?`
    : `The disease model could not identify my leaf photo (result #${r.id}). How should I take a better photo, and what symptoms should I describe?`);
  chart($("#dconf"), { type: "bar", data: { labels: r.top.map((x) => `${x.crop}: ${x.condition}`.slice(0, 38)), datasets: [{ data: r.top.map((x) => x.probability * 100), backgroundColor: r.top.map((_, i) => (i ? "#cfe8d7" : C.green)), borderRadius: 4 }] }, options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { max: 100, title: { display: true, text: "%" } } } } });
}

// ---------------- assistant ----------------
PAGES.assistant = async (v) => {
  const next = takeNext();
  const [listRes, predRes] = await Promise.all([api("/api/chats"), api("/api/predictions?limit=4").catch(() => ({ predictions: [] })), loadFarms()]);
  let chats = listRes.chats;
  const recent = predRes.predictions.slice(0, 3);
  const first = esc((S.user.name || "").split(" ")[0]);
  const SUGG = [
    ["psychology", "Crops", "Which crop suits my soil this season?"],
    ["science", "Fertiliser", "My nitrogen is low - which fertiliser types should I consider?"],
    ["coronavirus", "Disease", "How do I tell early blight from late blight on tomato?"],
    ["water", "Irrigation", "How often should I irrigate wheat in winter?"],
    ["landslide", "Soil", "What does a soil pH of 8 mean for my crops?"],
    ["trending_up", "Yield", "How can I raise my yield above the district average?"],
  ];
  const kindIcon = { crop: "psychology", yield: "trending_up", fertiliser: "science", disease: "coronavirus" };
  const askFor = (p) => ({ crop: `Explain my crop recommendation #${p.id} (${p.summary}). Why this crop and what should I watch out for?`,
    yield: `Explain my yield prediction #${p.id} for ${p.crop} (${p.summary}). How could I do better?`,
    fertiliser: `Explain my fertiliser result #${p.id} for ${p.crop || "my crop"} (${p.summary}). Which option suits a small farm?`,
    disease: `Explain my leaf diagnosis #${p.id} (${p.summary}). What can I do now, without chemical doses?` }[p.kind] || `Explain result #${p.id}: ${p.summary}`);

  v.innerHTML = `
  <div class="asst">
    <aside class="card asst-side">
      <button id="newchat" class="btn btn-primary w-full">${icon("add")} ${t("New conversation")}</button>
      <div class="field mt-3 mb-1"><input id="chatq" placeholder="Search conversations"/></div>
      <div id="chatlist" class="flex-1 overflow-y-auto -mx-1 px-1"></div>
      <div class="asst-ctx">${icon("info", "!text-base shrink-0")}<span>${S.user.share_farm_with_assistant ? `Answers use your ${S.farms.length} farm${S.farms.length === 1 ? "" : "s"} and recent results.` : "Farm data is not shared with the assistant."} <a href="#/settings" class="text-primary font-semibold">Change</a></span></div>
    </aside>
    <section class="card asst-main">
      <header class="asst-head">
        <div class="w-9 h-9 rounded-xl bg-primary text-white flex items-center justify-center shrink-0">${icon("eco")}</div>
        <div class="min-w-0 flex-1"><div class="font-semibold leading-tight truncate" id="chattitle">${t("AgriSense AI Assistant")}</div>
          <div class="text-xs text-muted flex items-center gap-1.5"><span class="inline-block w-2 h-2 rounded-full ${S.status?.assistant === false ? "bg-sun" : "bg-primary"}"></span>${S.status?.assistant === false ? "Not configured on this server" : "Farming questions only · answers in your language"}</div></div>
        <button type="button" id="ahist" class="asst-tool lg:hidden" title="Conversations">${icon("history")}</button>
        <label class="lang-pick hidden sm:inline-flex" title="Answer language">${icon("translate", "!text-base text-primary")}${langSelect("alang")}</label>
      </header>
      <div id="msgs" class="asst-msgs"><div class="asst-col" id="msgcol"></div></div>
      <div class="asst-compose">
        <div class="asst-col">
          <div id="attach-prev"></div>
          <form id="chatf" class="asst-box">
            <label class="asst-tool" title="Attach a leaf photo">${icon("attach_file")}<input id="cimg" type="file" accept="image/jpeg,image/png" class="hidden"/></label>
            <button type="button" id="mic" class="asst-tool" title="Speak your question">${icon("mic")}</button>
            <textarea id="cmsg" rows="1" placeholder="${t("Type your question")}…"></textarea>
            <button id="csend" class="btn btn-primary !rounded-xl !px-3" title="Send">${icon("send")}</button>
          </form>
          <div class="text-[11px] text-muted mt-1.5 px-1">Enter to send · Shift+Enter for a new line · attach a leaf photo to have it checked by the disease model. Answers can be wrong - confirm doses and sprays with your KVK.</div>
        </div>
      </div>
    </section>
  </div>`;

  let messages = [], img = null;
  const renderList = () => {
    const q = $("#chatq").value.trim().toLowerCase();
    const items = chats.filter((c) => !q || (c.title || "").toLowerCase().includes(q)).sort((a, b) => b.saved - a.saved || b.updated_at - a.updated_at);
    const row = (c) => `<div class="group asst-item ${c.id === S.chatId ? "active" : ""}"><button data-open="${c.id}" class="flex-1 min-w-0 text-left"><div class="text-sm truncate">${esc(c.title || "Conversation")}</div><div class="text-[11px] text-muted">${dateStr(c.updated_at)}</div></button><button data-save="${c.id}" data-v="${c.saved ? 0 : 1}" class="asst-mini" title="${c.saved ? "Unsave" : "Save"}">${icon(c.saved ? "bookmark_remove" : "bookmark_add", "!text-base")}</button><button data-del="${c.id}" class="asst-mini hover:!text-alert" title="Delete">${icon("delete", "!text-base")}</button></div>`;
    const saved = items.filter((c) => c.saved), rest = items.filter((c) => !c.saved);
    $("#chatlist").innerHTML = items.length
      ? (saved.length ? `<div class="asst-group">${icon("bookmark", "!text-sm")} Saved</div>${saved.map(row).join("")}` : "") + (rest.length ? `<div class="asst-group">${icon("history", "!text-sm")} Recent</div>${rest.map(row).join("")}` : "")
      : `<div class="text-xs text-muted px-2 py-6 text-center">${q ? "No conversation matches." : "No conversations yet. Ask your first question."}</div>`;
    $$("[data-open]").forEach((b) => (b.onclick = () => openChat(+b.dataset.open)));
    $$("[data-save]").forEach((b) => (b.onclick = async () => { await api(`/api/chats/${b.dataset.save}`, { method: "PATCH", body: { saved: +b.dataset.v } }); refresh(); }));
    $$("[data-del]").forEach((b) => (b.onclick = async () => { if (await confirmBox("Delete this conversation?")) { await api(`/api/chats/${b.dataset.del}`, { method: "DELETE" }); if (S.chatId === +b.dataset.del) newChat(); refresh(); } }));
  };
  const refresh = async () => { chats = (await api("/api/chats")).chats; renderList(); };
  const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/^#{1,4} (.*)$/gm, "<b>$1</b>").replace(/^\s*\d+\. (.*)$/gm, "<li>$1</li>").replace(/^\s*[-*] (.*)$/gm, "<li>$1</li>").replace(/(?<![*\w])\*([^*\n]+)\*(?![*\w])/g, "<i>$1</i>").replace(/(<li>.*<\/li>\n*)+/g, (m) => `<ul>${m.replace(/\n+/g, "")}</ul>`).replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br>");
  const welcome = () => `
    <div class="py-6 md:py-10">
      <div class="text-center">
        <div class="w-14 h-14 rounded-2xl bg-mint-2 flex items-center justify-center mx-auto mb-3">${icon("smart_toy", "!text-3xl text-primary")}</div>
        <h2 class="text-xl md:text-2xl font-semibold">${LANG === "hi" ? `नमस्ते ${first}, मैं आपकी क्या मदद करूँ?` : `Hello <span class="notranslate">${first}</span>, how can I help with your farm?`}</h2>
        <p class="text-sm text-muted mt-1">Ask about crops, soil, fertiliser, diseases, irrigation or any result in this app.</p>
      </div>
      ${recent.length ? `<div class="mt-7"><div class="asst-label">Explain one of your latest results</div><div class="grid sm:grid-cols-3 gap-2">${recent.map((p) => `<button class="asst-card" data-ask="${esc(askFor(p))}"><div class="flex items-center gap-2 text-xs text-muted">${icon(kindIcon[p.kind] || "insights", "!text-base text-primary")}${esc(title(p.kind))} · #${p.id}</div><div class="text-sm font-semibold mt-1 line-clamp-2">${esc(p.summary || "")}</div><div class="text-xs text-primary font-semibold mt-2">Explain this →</div></button>`).join("")}</div></div>` : ""}
      <div class="mt-6"><div class="asst-label">Try asking</div><div class="grid sm:grid-cols-2 gap-2">${SUGG.map(([ic, cat, q]) => `<button class="asst-card flex items-start gap-3" data-ask="${esc(q)}"><span class="w-8 h-8 rounded-lg bg-mint flex items-center justify-center shrink-0">${icon(ic, "!text-lg text-primary")}</span><span><span class="block text-[11px] uppercase tracking-wide text-muted font-semibold">${cat}</span><span class="block text-sm">${esc(q)}</span></span></button>`).join("")}</div></div>
    </div>`;
  // Answers not in the chosen language are translated (server-cached); "Show original" toggles back.
  const SCR = { hi: [0x900, 0x97f], mr: [0x900, 0x97f], mai: [0x900, 0x97f], gom: [0x900, 0x97f], bn: [0x980, 0x9ff], as: [0x980, 0x9ff],
    pa: [0xa00, 0xa7f], gu: [0xa80, 0xaff], or: [0xb00, 0xb7f], ta: [0xb80, 0xbff], te: [0xc00, 0xc7f], kn: [0xc80, 0xcff], ml: [0xd00, 0xd7f], ur: [0x600, 0x6ff] };
  const inLang = (txt, l) => { const r = SCR[l]; if (!r) return true; const L = [...txt].filter((ch) => /\p{L}/u.test(ch)); if (!L.length) return true; return L.filter((ch) => { const c = ch.codePointAt(0); return c >= r[0] && c <= r[1]; }).length / L.length >= 0.5; };
  const trMsg = {}, trBusy = new Set(), showOrig = new Set();
  const translateMsg = async (key, text) => {
    if (trBusy.has(key)) return;
    trBusy.add(key);
    try { trMsg[key] = (await api("/api/chat/translate", { method: "POST", body: { text, lang: key.split("|")[0] } })).text; }
    catch (e) { trMsg[key] = null; fail(e); }
    trBusy.delete(key);
    if (v.isConnected) draw();
  };
  S.onLang = () => { if (v.isConnected) draw(); };
  const draw = () => {
    const col = $("#msgcol");
    col.innerHTML = messages.length ? messages.map((m, i) => m.role === "user"
      ? `<div class="flex justify-end"><div class="bubble-user px-4 py-2.5 max-w-[85%] text-sm whitespace-pre-wrap">${esc(m.content.split("\n[Leaf photo")[0])}${m.content.includes("[Leaf photo") ? `<div class="text-xs opacity-80 mt-1">${icon("image", "!text-sm")} leaf photo checked by the disease model</div>` : ""}</div></div>`
      : m.role === "pending" ? `<div class="flex gap-3"><div class="asst-av">${icon("eco", "!text-base")}</div><div class="bubble-bot px-4 py-3 text-sm text-muted">${icon("progress_activity", "spin !text-base")} Thinking…</div></div>`
      : (() => {
        const key = `${LANG}|${i}`, needs = LANG !== "en" && !inLang(m.content, LANG);
        if (needs && trMsg[key] === undefined) translateMsg(key, m.content);
        const shown = needs && trMsg[key] && !showOrig.has(key) ? trMsg[key] : m.content;
        const trBtn = !needs ? "" : trMsg[key] ? `<button class="asst-mini !opacity-100 text-[11px] font-semibold text-primary" data-orig="${key}">${icon("translate", "!text-sm")} ${showOrig.has(key) ? "Show translation" : "Show original"}</button>`
          : `<span class="text-[11px] self-center">${icon("progress_activity", "spin !text-sm")} Translating…</span>`;
        return `<div class="flex gap-3"><div class="asst-av">${icon("eco", "!text-base")}</div><div class="min-w-0 flex-1"><div class="bubble-bot px-4 py-3 text-sm prose-chat"><p>${md(shown)}</p></div><div class="flex gap-1 mt-1 text-muted items-center"><button class="asst-mini" data-copy="${esc(shown)}" title="Copy">${icon("content_copy", "!text-base")}</button>${trBtn}${m.model ? `<span class="text-[11px] self-center notranslate">${esc(m.model)}</span>` : ""}</div></div></div>`;
      })()).join("") : welcome();
    $$("[data-orig]", col).forEach((b) => (b.onclick = () => { const k = b.dataset.orig; if (showOrig.has(k)) showOrig.delete(k); else showOrig.add(k); draw(); }));
    $$("[data-ask]", col).forEach((b) => (b.onclick = () => send(b.dataset.ask)));
    $$("[data-copy]", col).forEach((b) => (b.onclick = () => { navigator.clipboard?.writeText(b.dataset.copy); toast("Copied"); }));
    $("#chattitle").textContent = (S.chatId && chats.find((c) => c.id === S.chatId)?.title) || t("AgriSense AI Assistant");
    const box = $("#msgs"); box.scrollTop = messages.length ? box.scrollHeight : 0;
  };
  const openChat = async (id) => { const c = await api(`/api/chats/${id}`); S.chatId = id; messages = c.messages; draw(); renderList(); };
  const newChat = () => { S.chatId = null; messages = []; draw(); renderList(); $("#cmsg").focus(); };
  const ta = $("#cmsg");
  const send = async (text) => {
    text = (text || "").trim();
    if (!text && !img) return;
    const fd = new FormData(); fd.append("message", text); fd.append("lang", LANG); if (S.chatId) fd.append("chat_id", S.chatId); if (img) fd.append("image", img);
    messages.push({ role: "user", content: text + (img ? "\n[Leaf photo]" : "") }, { role: "pending" }); draw();
    ta.value = ""; ta.style.height = "auto"; img = null; $("#cimg").value = ""; $("#attach-prev").innerHTML = "";
    try { const r = await api("/api/chat", { method: "POST", body: fd }); S.chatId = r.chat_id; await refresh(); await openChat(r.chat_id); }
    catch (er) { messages = messages.filter((m) => m.role !== "pending"); draw(); fail(er); }
  };
  const side = $(".asst-side", v);
  $("#ahist").onclick = (e) => { e.stopPropagation(); side.classList.toggle("open"); };
  side.onclick = (e) => { if (e.target.closest("[data-open],#newchat")) side.classList.remove("open"); };
  $("#newchat").onclick = newChat;
  $("#chatq").oninput = renderList;
  $("#alang").onchange = (e) => setLang(e.target.value);
  $("#cimg").onchange = () => { img = $("#cimg").files[0] || null; $("#attach-prev").innerHTML = img ? `<div class="inline-flex items-center gap-2 text-xs bg-mint rounded-lg px-2 py-1 mb-2">${icon("image", "!text-base")}${esc(img.name)}<button type="button" id="rmimg">${icon("close", "!text-base")}</button></div>` : ""; $("#rmimg") && ($("#rmimg").onclick = () => { img = null; $("#cimg").value = ""; $("#attach-prev").innerHTML = ""; }); };
  ta.oninput = () => { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 160) + "px"; };
  ta.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(ta.value); } };
  $("#chatf").onsubmit = (e) => { e.preventDefault(); send(ta.value); };
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) $("#mic").classList.add("hidden");
  else $("#mic").onclick = () => { const r = new SR(); r.lang = SPEECH_LANG[LANG] || "en-IN"; r.onresult = (e) => { ta.value += e.results[0][0].transcript; ta.oninput(); }; r.onerror = () => toast("Voice input failed - check microphone permission", "err"); r.start(); toast("Listening…", "info"); };
  if (next.ask) { S.chatId = null; messages = []; renderList(); await send(next.ask); }
  else if (S.chatId && chats.some((c) => c.id === S.chatId)) await openChat(S.chatId);
  else { S.chatId = null; draw(); renderList(); }
};

// ---------------- weather ----------------
PAGES.weather = async (v) => {
  await loadFarms();
  const today = new Date(), iso = (d) => d.toISOString().slice(0, 10);
  const start = new Date(today); start.setFullYear(today.getFullYear() - 1);
  v.innerHTML = header(t("Weather & Climate Intelligence"), "Live forecast and historical climate for your farm.") + `
  <form id="wf" class="card p-4 mb-5 grid grid-cols-2 md:grid-cols-5 gap-3 items-end text-sm">
    <div class="field col-span-2"><label>${t("Location")}</label><select name="farm_id">${S.farms.filter((f) => f.lat != null).map((f) => `<option value="${f.id}">${esc(f.name)}</option>`).join("")}<option value="">${S.user.district ? `Registered district (${esc(S.user.district)})` : "Registered district"}</option></select></div>
    <div class="field"><label>${t("Start date")}</label><input type="date" name="start" value="${iso(start)}"/></div>
    <div class="field"><label>${t("End date")}</label><input type="date" name="end" value="${iso(new Date(today - 4 * 864e5))}"/></div>
    <button class="btn btn-primary" id="wgo">${icon("refresh")} ${t("Load")}</button>
  </form>
  <div id="wlive" class="mb-5"></div>
  <div id="whist"></div>`;
  const f = $("#wf");
  const load = async () => {
    const q = f.farm_id.value ? `farm_id=${f.farm_id.value}` : "";
    $("#wlive").innerHTML = `<div class="skeleton h-56"></div>`;
    try { $("#wlive").innerHTML = weatherCard(await api(`/api/weather?${q}`)); }
    catch (e) { $("#wlive").innerHTML = `<div class="card p-5">${empty("location_off", esc(e.error), `<a class="btn btn-ghost" href="#/farms">${icon("add")} ${t("Add farm")}</a>`)}</div>`; $("#whist").innerHTML = ""; return; }
    $("#whist").innerHTML = `<div class="skeleton h-80"></div>`;
    try {
      const h = await api(`/api/weather/history?${q}&start=${f.start.value}&end=${f.end.value}`);
      renderWeatherHistory(h);
    } catch (e) { $("#whist").innerHTML = errorState(e.error); }
  };
  f.onsubmit = (e) => { e.preventDefault(); load(); };
  await load();
};
function renderWeatherHistory(h) {
  const r = h.rows.filter((x) => x.temp_mean != null);
  const avg = (k) => r.reduce((a, x) => a + (x[k] ?? 0), 0) / (r.length || 1);
  const sum = (k) => r.reduce((a, x) => a + (x[k] ?? 0), 0);
  const months = {};
  r.forEach((x) => { const m = x.date.slice(0, 7); months[m] = (months[m] || 0) + (x.rain_mm || 0); });
  const stat = (l, v, u) => `<div class="card p-4"><div class="text-xs text-muted uppercase font-semibold">${l}</div><div class="text-2xl font-bold mt-1">${v}<span class="text-sm text-muted font-medium"> ${u}</span></div></div>`;
  $("#whist").innerHTML = `
  <div class="flex items-center gap-2 mb-3"><span class="badge b-blue">${icon("history", "!text-sm")} Historical</span><span class="text-sm text-muted">${esc(h.source)} · ${r.length} days · ${esc(h.location.label)}</span></div>
  <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-5">${stat("Total rainfall", fmt(sum("rain_mm"), 0), "mm")}${stat("Avg temperature", fmt(avg("temp_mean")), "°C")}${stat("Avg max", fmt(avg("temp_max")), "°C")}${stat("Avg min", fmt(avg("temp_min")), "°C")}${stat("Avg humidity", fmt(avg("humidity"), 0), "%")}${stat("Avg solar radiation", fmt(avg("radiation_mj")), "MJ/m²/day")}</div>
  <div class="grid lg:grid-cols-2 gap-5">
    <div class="card p-5"><h3 class="font-semibold mb-3">Daily rainfall</h3><div class="h-60"><canvas id="c-rain"></canvas></div></div>
    <div class="card p-5"><h3 class="font-semibold mb-3">Temperature</h3><div class="h-60"><canvas id="c-temp"></canvas></div></div>
    <div class="card p-5"><h3 class="font-semibold mb-3">Relative humidity</h3><div class="h-60"><canvas id="c-hum"></canvas></div></div>
    <div class="card p-5"><h3 class="font-semibold mb-3">Solar radiation</h3><div class="h-60"><canvas id="c-sun"></canvas></div></div>
    <div class="card p-5 lg:col-span-2"><h3 class="font-semibold mb-3">Monthly rainfall</h3><div class="h-60"><canvas id="c-month"></canvas></div></div>
  </div>
  <div class="card p-5 mt-5"><h3 class="font-semibold mb-1">How weather relates to crops</h3><p class="text-sm text-muted">Monthly rainfall above shows when the monsoon arrived and how much fell — the main driver of kharif yields. Days above 35 °C during flowering reduce grain set in rice and wheat (${r.filter((x) => (x.temp_max ?? 0) > 35).length} such days in this period). The yield model on this site does <b>not</b> use these weather values, because its training data has none.</p></div>
  <p class="text-xs text-muted mt-3">${esc(h.attribution)}</p>`;
  const L = r.map((x) => x.date), base = { pointRadius: 0, borderWidth: 1.5, tension: .25 };
  const xs = { x: { ticks: { maxTicksLimit: 8 } } };
  chart($("#c-rain"), { type: "bar", data: { labels: L, datasets: [{ label: "Rain (mm)", data: r.map((x) => x.rain_mm), backgroundColor: C.blue }] }, options: { scales: xs, plugins: { legend: { display: false } } } });
  chart($("#c-temp"), { type: "line", data: { labels: L, datasets: [{ label: "Max", data: r.map((x) => x.temp_max), borderColor: C.red, ...base }, { label: "Mean", data: r.map((x) => x.temp_mean), borderColor: C.green, ...base }, { label: "Min", data: r.map((x) => x.temp_min), borderColor: C.blue, ...base }] }, options: { scales: xs } });
  chart($("#c-hum"), { type: "line", data: { labels: L, datasets: [{ label: "RH %", data: r.map((x) => x.humidity), borderColor: C.green2, backgroundColor: "rgba(98,168,124,.12)", fill: true, ...base }] }, options: { scales: xs, plugins: { legend: { display: false } } } });
  chart($("#c-sun"), { type: "line", data: { labels: L, datasets: [{ label: "MJ/m²/day", data: r.map((x) => x.radiation_mj), borderColor: C.yellow, backgroundColor: "rgba(232,185,79,.15)", fill: true, ...base }] }, options: { scales: xs, plugins: { legend: { display: false } } } });
  chart($("#c-month"), { type: "bar", data: { labels: Object.keys(months), datasets: [{ label: "Rain (mm)", data: Object.values(months), backgroundColor: C.green2, borderRadius: 4 }] }, options: { plugins: { legend: { display: false } } } });
}

// ---------------- soil ----------------
PAGES.soil = async (v) => {
  await loadFarms();
  const located = S.farms.filter((f) => f.lat != null);
  v.innerHTML = header(t("Soil Health & Nutrient Analysis"), "Modelled soil properties at your farm, by depth.") + `
  <form id="sf" class="card p-4 mb-5 flex flex-wrap items-end gap-3 text-sm">
    <div class="field min-w-[220px]"><label>${t("Farm")}</label><select name="farm_id">${located.map((f) => `<option value="${f.id}">${esc(f.name)}</option>`).join("")}</select></div>
    <button class="btn btn-primary" id="sgo">${icon("refresh")} ${t("Load")}</button>
  </form>
  <div id="sres"></div>`;
  if (!located.length) { $("#sres").innerHTML = `<div class="card p-5">${empty("location_off", "Soil data needs a farm with map coordinates.", `<a class="btn btn-primary" href="#/farms">${icon("add")} ${t("Add farm")}</a>`)}</div>`; $("#sf").remove(); return; }
  const f = $("#sf");
  const load = async () => {
    $("#sres").innerHTML = `<div class="card p-6 text-sm text-muted flex items-center gap-2">${icon("progress_activity", "spin")} Fetching SoilGrids estimates (this service can take up to a minute)…</div>`;
    try { renderSoil(await busy($("#sgo"), () => api(`/api/soil?farm_id=${f.farm_id.value}`))); } catch (e) { $("#sres").innerHTML = errorState(e.error); }
  };
  f.onsubmit = (e) => { e.preventDefault(); load(); };
  await load();
};
function renderSoil(s) {
  if (!s.has_data) { $("#sres").innerHTML = `<div class="card p-5">${empty("water", "SoilGrids has no estimate for this point (water body, urban area or rock).")}</div>`; return; }
  const P = s.properties, get = (k, d = 0) => P[k]?.depths[d]?.mean;
  const depths = P.phh2o.depths.map((d) => d.depth);
  $("#sres").innerHTML = `
  <div class="mb-4">${note(`<b>${esc(s.warning)}</b> ${esc(s.source)} at ${s.lat.toFixed(4)}, ${s.lon.toFixed(4)} (${esc(s.location.label)}). Use a lab soil test for fertiliser decisions.`, "warn")}</div>
  <div class="flex items-center gap-2 mb-4 text-sm"><span class="font-semibold">${t("Depth")}:</span><div id="dsel" class="inline-flex flex-wrap gap-1">${depths.map((d, i) => `<button data-d="${i}" class="px-2.5 py-1 rounded-full border border-line ${i ? "bg-white" : "bg-primary text-white"}">${d}</button>`).join("")}</div></div>
  <div id="scards" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5"></div>
  <div class="grid lg:grid-cols-3 gap-5 mb-5">
    <div class="card p-5"><h3 class="font-semibold mb-2">pH gauge</h3><div id="phg"></div></div>
    <div class="card p-5"><h3 class="font-semibold mb-2">Soil texture</h3><div class="h-56"><canvas id="tex"></canvas></div><div id="texcls" class="text-sm text-center mt-2"></div></div>
    <div class="card p-5"><h3 class="font-semibold mb-2">Profile by depth</h3><div class="h-56"><canvas id="prof"></canvas></div></div>
  </div>
  <div class="card p-5"><h3 class="font-semibold mb-3">All properties and uncertainty</h3><div class="overflow-x-auto"><table class="tbl"><thead><tr><th>Property</th><th>Unit</th>${depths.map((d) => `<th>${d}</th>`).join("")}</tr></thead><tbody>
  ${Object.values(P).map((p) => `<tr><td class="font-medium">${esc(p.label)}</td><td class="text-muted">${esc(p.unit)}</td>${p.depths.map((d) => `<td>${fmt(d.mean, 2)}<div class="text-[11px] text-muted">${d.q05 != null ? `90%: ${fmt(d.q05, 2)}–${fmt(d.q95, 2)}` : ""}</div></td>`).join("")}</tr>`).join("")}</tbody></table></div></div>`;
  let tex, prof;
  const draw = (di) => {
    $$("#dsel button").forEach((b) => { b.className = `px-2.5 py-1 rounded-full border border-line ${+b.dataset.d === di ? "bg-primary text-white" : "bg-white"}`; });
    const card = (l, k, u) => `<div class="card p-4"><div class="text-xs text-muted uppercase font-semibold">${l}</div><div class="text-2xl font-bold mt-1">${fmt(get(k, di), 2)}<span class="text-sm text-muted font-medium"> ${u}</span></div><div class="text-[11px] text-muted mt-1">90% range ${fmt(P[k].depths[di].q05, 2)}–${fmt(P[k].depths[di].q95, 2)}</div></div>`;
    $("#scards").innerHTML = card("Soil pH", "phh2o", "") + card("Total nitrogen", "nitrogen", "g/kg") + card("Organic carbon", "soc", "g/kg") + card("Bulk density", "bdod", "g/cm³") + card("Clay", "clay", "%") + card("Sand", "sand", "%") + card("Silt", "silt", "%") + card("Water at field capacity", "wv0033", "vol %");
    const ph = get("phh2o", di) ?? 7, pos = Math.max(0, Math.min(100, ((ph - 4) / 5) * 100));
    const phText = ph < 5.5 ? "Strongly acidic" : ph < 6.5 ? "Slightly acidic" : ph <= 7.5 ? "Neutral" : ph <= 8.5 ? "Moderately alkaline" : "Strongly alkaline";
    $("#phg").innerHTML = `<div class="text-4xl font-bold text-center my-3">${fmt(ph, 1)}</div><div class="relative h-3 rounded-full" style="background:linear-gradient(90deg,#E57373,#E8B94F,#62A87C,#5B9BD5,#7b6fd0)"><div class="absolute -top-1.5 w-1.5 h-6 bg-ink rounded" style="left:calc(${pos}% - 3px)"></div></div><div class="flex justify-between text-[11px] text-muted mt-1"><span>4</span><span>5.5</span><span>7</span><span>8.5</span><span>9</span></div><div class="text-center text-sm font-semibold mt-3">${phText}</div>`;
    const cl = get("clay", di), sa = get("sand", di), si = get("silt", di);
    tex?.destroy();
    tex = chart($("#tex"), { type: "doughnut", data: { labels: ["Sand", "Silt", "Clay"], datasets: [{ data: [sa, si, cl], backgroundColor: [C.yellow, C.green2, "#a77b5a"] }] }, options: { cutout: "60%", plugins: { legend: { position: "bottom" } } } });
    $("#texcls").innerHTML = `USDA texture class: <b>${textureClass(sa, si, cl)}</b>`;
  };
  $$("#dsel button").forEach((b) => (b.onclick = () => draw(+b.dataset.d)));
  draw(0);
  prof = chart($("#prof"), { type: "line", data: { labels: depths, datasets: [{ label: "Organic carbon (g/kg)", data: P.soc.depths.map((d) => d.mean), borderColor: C.green, tension: .3 }, { label: "Clay (%)", data: P.clay.depths.map((d) => d.mean), borderColor: "#a77b5a", tension: .3 }, { label: "Nitrogen (g/kg)", data: P.nitrogen.depths.map((d) => d.mean), borderColor: C.blue, tension: .3 }] }, options: { plugins: { legend: { position: "bottom" } } } });
}
function textureClass(sand, silt, clay) {
  if (sand == null) return "—";
  if (clay >= 40) return silt >= 40 ? "Silty clay" : sand > 45 ? "Sandy clay" : "Clay";
  if (clay >= 27) return sand > 45 ? "Sandy clay loam" : silt >= 40 ? "Silty clay loam" : "Clay loam";
  if (clay >= 20 && sand > 45) return "Sandy clay loam";
  if (silt >= 80 && clay < 12) return "Silt";
  if (silt >= 50) return "Silt loam";
  if (sand >= 85) return "Sand";
  if (sand >= 70) return "Loamy sand";
  if (sand > 52 || (clay < 7 && silt < 50)) return "Sandy loam";
  return "Loam";
}

// ---------------- farms ----------------
PAGES.farms = async (v) => {
  await loadFarms();
  v.innerHTML = header(t("My Farms"), "Your fields, their location and what is growing.", `<button id="addfarm" class="btn btn-primary">${icon("add")} ${t("Add farm")}</button>`) + `
  ${S.farms.some((f) => f.lat != null) ? `<div class="card p-3 mb-5"><div id="fmap" class="h-72"></div></div>` : ""}
  <div class="grid md:grid-cols-2 xl:grid-cols-3 gap-4">${S.farms.length ? S.farms.map((f) => `
    <div class="card p-5 flex flex-col">
      <div class="flex items-start justify-between gap-2"><div><div class="text-lg font-semibold">${esc(f.name)}</div><div class="text-sm text-muted flex items-center gap-1">${icon("location_on", "!text-base")}${esc([f.village, f.district, f.state].filter(Boolean).join(", ") || "No location")}</div></div>${f.current_crop ? `<span class="badge b-green">${icon("grass", "!text-sm")}${esc(f.current_crop)}</span>` : ""}</div>
      <div class="grid grid-cols-3 gap-2 mt-4 text-sm"><div class="p-2 rounded-lg bg-mint"><div class="text-[11px] text-muted">Area</div><div class="font-semibold">${f.area_ha != null ? `${fmt(f.area_ha, 2)} ha` : "—"}</div></div><div class="p-2 rounded-lg bg-mint"><div class="text-[11px] text-muted">Soil</div><div class="font-semibold truncate">${esc(f.soil_type || "—")}</div></div><div class="p-2 rounded-lg bg-mint"><div class="text-[11px] text-muted">Irrigation</div><div class="font-semibold truncate">${esc(f.irrigation || "—")}</div></div></div>
      <div class="text-xs text-muted mt-3">Updated ${dateStr(f.updated_at)}</div>
      <div class="flex gap-2 mt-4"><a href="#/farm/${f.id}" class="btn btn-ghost flex-1">${icon("visibility")} ${t("View")}</a><button data-edit="${f.id}" class="btn btn-ghost">${icon("edit")}</button><button data-del="${f.id}" class="btn btn-danger">${icon("delete")}</button></div>
    </div>`).join("") : `<div class="card p-5 md:col-span-2 xl:col-span-3">${empty("agriculture", "No farms yet. Add one with its location to unlock weather, soil data and farm-linked predictions.")}</div>`}</div>`;
  $("#addfarm").onclick = () => farmForm();
  $$("[data-edit]").forEach((b) => (b.onclick = () => farmForm(S.farms.find((f) => f.id === +b.dataset.edit))));
  $$("[data-del]").forEach((b) => (b.onclick = async () => {
    const f = S.farms.find((x) => x.id === +b.dataset.del);
    if (await confirmBox(`Delete "${f.name}"? Its predictions stay in your history but are unlinked from the farm.`)) { try { await api(`/api/farms/${f.id}`, { method: "DELETE" }); toast("Farm deleted"); route(); } catch (e) { fail(e); } }
  }));
  const pts = S.farms.filter((f) => f.lat != null);
  if (pts.length) {
    S.map = L.map("fmap", { scrollWheelZoom: false });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap contributors", maxZoom: 18 }).addTo(S.map);
    const g = L.featureGroup(pts.map((f) => L.circleMarker([f.lat, f.lon], { radius: 9, color: C.green, fillColor: C.green2, fillOpacity: .8 }).bindPopup(`<b>${esc(f.name)}</b><br>${esc(f.current_crop || "")}`))).addTo(S.map);
    S.map.fitBounds(g.getBounds().pad(0.5), { maxZoom: 11 });
  }
};
function farmForm(f = {}) {
  const yo = S.cache.yopt?.State || [];
  modal(`<h3 class="text-lg font-semibold mb-4">${f.id ? t("Edit") : t("Add farm")}</h3>
  <form id="farmf" class="space-y-3" novalidate>
    <div class="field"><label>Farm name</label><input name="name" value="${esc(f.name || "")}" required/></div>
    <div class="field"><label>Find location</label><div class="flex gap-2"><input id="geoq" placeholder="Village, town or district"/><button type="button" id="geob" class="btn btn-ghost">${icon("search")}</button></div><div id="geores" class="mt-1"></div><div class="hint">Or use <button type="button" id="gps" class="text-primary font-semibold">my current location</button>.</div></div>
    <div class="grid grid-cols-2 gap-3"><div class="field"><label>Latitude</label><input name="lat" type="number" step="any" value="${f.lat ?? ""}"/></div><div class="field"><label>Longitude</label><input name="lon" type="number" step="any" value="${f.lon ?? ""}"/></div></div>
    <div class="grid grid-cols-2 gap-3"><div class="field"><label>${t("State")}</label><input name="state" list="statelist" value="${esc(f.state || "")}"/><datalist id="statelist">${yo.map((s) => `<option>${esc(s)}</option>`).join("")}</datalist></div><div class="field"><label>${t("District")}</label><input name="district" value="${esc(f.district || "")}"/></div></div>
    <div class="grid grid-cols-2 gap-3"><div class="field"><label>Village</label><input name="village" value="${esc(f.village || "")}"/></div><div class="field"><label>Area (ha)</label><input name="area_ha" type="number" step="any" value="${f.area_ha ?? ""}"/></div></div>
    <div class="grid grid-cols-3 gap-3"><div class="field"><label>Soil type</label><select name="soil_type"><option value="">—</option>${["Alluvial", "Black", "Red", "Laterite", "Sandy", "Loamy", "Clayey"].map((s) => `<option ${f.soil_type === s ? "selected" : ""}>${s}</option>`).join("")}</select></div><div class="field"><label>Current crop</label><input name="current_crop" value="${esc(f.current_crop || "")}"/></div><div class="field"><label>Irrigation</label><select name="irrigation"><option value="">—</option>${["Rainfed", "Canal", "Tubewell", "Drip", "Sprinkler"].map((s) => `<option ${f.irrigation === s ? "selected" : ""}>${s}</option>`).join("")}</select></div></div>
    <div class="field"><label>Notes</label><textarea name="notes" rows="2">${esc(f.notes || "")}</textarea></div>
    <div class="flex justify-end gap-2 pt-2"><button type="button" class="btn btn-ghost" id="fcancel">${t("Cancel")}</button><button class="btn btn-primary" id="fsave">${icon("save")} ${t("Save")}</button></div>
  </form>`, (m) => {
    const form = $("#farmf", m);
    $("#fcancel", m).onclick = closeModal;
    $("#geob", m).onclick = async () => {
      try {
        const r = (await api(`/api/geocode?q=${encodeURIComponent($("#geoq", m).value)}`)).results;
        $("#geores", m).innerHTML = r.length ? r.map((x, i) => `<button type="button" data-i="${i}" class="block w-full text-left text-sm px-2 py-1.5 rounded hover:bg-mint">${esc([x.name, x.admin2, x.admin1].filter(Boolean).join(", "))}</button>`).join("") : `<div class="text-sm text-muted">No places found</div>`;
        $$("[data-i]", m).forEach((b) => (b.onclick = () => { const x = r[+b.dataset.i]; form.lat.value = x.lat.toFixed(5); form.lon.value = x.lon.toFixed(5); if (!form.state.value) form.state.value = x.admin1 || ""; if (!form.district.value) form.district.value = x.admin2 || x.name; $("#geores", m).innerHTML = ""; }));
      } catch (e) { fail(e); }
    };
    $("#gps", m).onclick = () => navigator.geolocation?.getCurrentPosition((p) => { form.lat.value = p.coords.latitude.toFixed(5); form.lon.value = p.coords.longitude.toFixed(5); }, () => toast("Location permission denied", "err"));
    form.onsubmit = async (e) => {
      e.preventDefault();
      try { await api(f.id ? `/api/farms/${f.id}` : "/api/farms", { method: f.id ? "PUT" : "POST", body: { ...formData(form), crop_history: f.crop_history || [] } }); closeModal(); toast(f.id ? "Farm updated" : "Farm added"); route(); }
      catch (er) { showFieldErrors(form, er); fail(er); }
    };
  });
}
PAGES.farm = async (v, id) => {
  const [{ farm: f, predictions: preds }] = await Promise.all([api(`/api/farms/${id}`), loadFarms()]);
  v.innerHTML = header(f.name, [f.village, f.district, f.state].filter(Boolean).join(", ") || "No location set", `<a href="#/farms" class="btn btn-ghost">${icon("arrow_back")} ${t("My Farms")}</a><button id="fe" class="btn btn-ghost">${icon("edit")} ${t("Edit")}</button>`) + `
  <div class="grid lg:grid-cols-3 gap-5 mb-5">
    <div class="card p-5"><h3 class="font-semibold mb-3">Farm information</h3><dl class="text-sm grid grid-cols-2 gap-y-2">${[["Area", f.area_ha != null ? `${fmt(f.area_ha, 2)} ha` : "—"], ["Soil type", f.soil_type], ["Current crop", f.current_crop], ["Irrigation", f.irrigation], ["Coordinates", f.lat != null ? `${f.lat.toFixed(4)}, ${f.lon.toFixed(4)}` : "—"]].map(([k, x]) => `<dt class="text-muted">${k}</dt><dd class="font-medium">${esc(x || "—")}</dd>`).join("")}</dl>${f.notes ? `<p class="text-sm mt-3 p-3 rounded-lg bg-mint">${esc(f.notes)}</p>` : ""}</div>
    <div class="card p-3 lg:col-span-2">${f.lat != null ? `<div id="fmap" class="h-64"></div>` : empty("location_off", "Add coordinates to see this farm on the map and get weather and soil data.")}</div>
  </div>
  <div class="grid lg:grid-cols-2 gap-5 mb-5">
    <div class="card p-5"><div class="flex items-center justify-between mb-3"><h3 class="font-semibold">Crop history</h3><button id="addch" class="btn btn-ghost !py-1 !min-h-0 text-xs">${icon("add", "!text-base")} Add season</button></div>
      ${f.crop_history.length ? `<table class="tbl"><thead><tr><th>Season</th><th>Crop</th><th>Yield (t/ha)</th><th></th></tr></thead><tbody>${f.crop_history.map((c, i) => `<tr><td>${esc(c.season)}</td><td>${esc(c.crop)}</td><td>${c.yield ? fmt(c.yield, 2) : "—"}</td><td><button data-rmch="${i}" class="text-muted hover:text-alert">${icon("close", "!text-base")}</button></td></tr>`).join("")}</tbody></table>` : `<p class="text-sm text-muted">Record past seasons here to keep a crop rotation log.</p>`}</div>
    <div class="card p-5"><h3 class="font-semibold mb-3">Soil profile (SoilGrids, 0–5 cm)</h3><div id="fsoil" class="text-sm text-muted">${f.lat != null ? "Loading…" : "Needs coordinates."}</div></div>
  </div>
  <div id="fweather" class="mb-5"></div>
  <div class="card p-5"><h3 class="font-semibold mb-3">Predictions for this farm</h3>${preds.length ? `<div class="overflow-x-auto"><table class="tbl"><thead><tr><th>#</th><th>${t("Date")}</th><th>${t("Type")}</th><th>${t("Result")}</th><th></th></tr></thead><tbody>${preds.map((p) => `<tr><td>${p.id}</td><td>${dateStr(p.created_at)}</td><td>${kindBadge(p.kind)}</td><td>${esc(p.summary)}</td><td><a class="text-primary" href="#/prediction/${p.id}">${icon("visibility")}</a></td></tr>`).join("")}</tbody></table></div>` : `<p class="text-sm text-muted">Pick this farm in any prediction form to link results here.</p>`}</div>`;
  $("#fe").onclick = () => farmForm(f);
  const saveHistory = async (h) => { await api(`/api/farms/${f.id}`, { method: "PUT", body: { ...f, crop_history: h } }); route(); };
  $("#addch").onclick = () => modal(`<h3 class="text-lg font-semibold mb-3">Add a season</h3><form id="chf" class="space-y-3"><div class="field"><label>Season</label><input name="season" placeholder="e.g. Kharif 2025" required/></div><div class="field"><label>Crop</label><input name="crop" required/></div><div class="field"><label>Yield (t/ha, optional)</label><input name="yield" type="number" step="any"/></div><div class="flex justify-end gap-2"><button type="button" class="btn btn-ghost" onclick="closeModal()">${t("Cancel")}</button><button class="btn btn-primary">${t("Save")}</button></div></form>`, (m) => {
    $("#chf", m).onsubmit = (e) => { e.preventDefault(); const d = formData(e.target); if (!d.season || !d.crop) return toast("Season and crop are required", "err"); closeModal(); saveHistory([...f.crop_history, { season: d.season, crop: d.crop, yield: d.yield ? +d.yield : null }]).catch(fail); };
  });
  $$("[data-rmch]").forEach((b) => (b.onclick = () => saveHistory(f.crop_history.filter((_, i) => i !== +b.dataset.rmch)).catch(fail)));
  if (f.lat != null) {
    S.map = L.map("fmap").setView([f.lat, f.lon], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap contributors", maxZoom: 18 }).addTo(S.map);
    L.marker([f.lat, f.lon]).addTo(S.map).bindPopup(esc(f.name));
    api(`/api/weather?farm_id=${f.id}`).then((w) => ($("#fweather").innerHTML = weatherCard(w))).catch(() => {});
    api(`/api/soil?farm_id=${f.id}`).then((s) => {
      if (!s.has_data) { $("#fsoil").textContent = "No SoilGrids estimate at this point."; return; }
      const P = s.properties, g = (k) => P[k].depths[0].mean;
      $("#fsoil").innerHTML = `<div class="grid grid-cols-3 gap-2 text-ink">${[["pH", g("phh2o"), ""], ["Org. carbon", g("soc"), "g/kg"], ["Nitrogen", g("nitrogen"), "g/kg"], ["Clay", g("clay"), "%"], ["Sand", g("sand"), "%"], ["Texture", null, textureClass(g("sand"), g("silt"), g("clay"))]].map(([k, x, u]) => `<div class="p-2 rounded-lg bg-mint"><div class="text-[11px] text-muted">${k}</div><div class="font-semibold">${x != null ? fmt(x, 2) : ""} ${esc(u)}</div></div>`).join("")}</div><a href="#/soil" class="text-primary text-sm font-semibold mt-3 inline-block">Full soil profile →</a>`;
    }).catch((e) => ($("#fsoil").textContent = e.error || "SoilGrids unavailable"));
  }
};

// ---------------- history ----------------
PAGES.history = async (v) => {
  await loadFarms();
  v.innerHTML = header(t("Prediction History"), "Every prediction you have run, with its inputs and model version.", `<button id="cmp" class="btn btn-ghost" disabled>${icon("compare_arrows")} Compare</button>`) + `
  <form id="hf" class="card p-4 mb-5 grid grid-cols-2 md:grid-cols-3 xl:grid-cols-7 gap-3 items-end text-sm">
    <div class="field xl:col-span-2"><label>${t("Search")}</label><input name="q" placeholder="ID, crop or result"/></div>
    <div class="field"><label>${t("Type")}</label><select name="kind"><option value="">${t("All")}</option><option value="crop">Crop</option><option value="yield">Yield</option><option value="fertiliser">Fertiliser</option><option value="disease">Disease</option></select></div>
    <div class="field"><label>${t("Farm")}</label><select name="farm_id"><option value="">${t("All")}</option>${S.farms.map((f) => `<option value="${f.id}">${esc(f.name)}</option>`).join("")}</select></div>
    <div class="field"><label>${t("Status")}</label><select name="status"><option value="">${t("All")}</option><option value="completed">Completed</option><option value="needs review">Needs review</option></select></div>
    <div class="field"><label>From</label><input type="date" name="start"/></div>
    <div class="field"><label>To</label><input type="date" name="end"/></div>
  </form>
  <div class="card p-2"><div id="htable" class="overflow-x-auto"></div></div>`;
  const f = $("#hf"), picked = new Set();
  const load = async () => {
    const q = new URLSearchParams(Object.fromEntries(Object.entries(formData(f)).filter(([, x]) => x)));
    const rs = (await api(`/api/predictions?${q}`)).predictions;
    const inputSummary = (p) => Object.entries(p.inputs).filter(([k]) => !["filename"].includes(k)).slice(0, 4).map(([k, x]) => `${k}: ${x}`).join(", ") || p.inputs.filename || "";
    $("#htable").innerHTML = rs.length ? `<table class="tbl"><thead><tr><th></th><th>ID</th><th>${t("Date")}</th><th>${t("Farm")}</th><th>${t("Type")}</th><th>Inputs</th><th>${t("Result")}</th><th>${t("Model")}</th><th>${t("Status")}</th><th>${t("Action")}</th></tr></thead><tbody>
      ${rs.map((p) => `<tr><td><input type="checkbox" data-pick="${p.id}" data-kind="${p.kind}" ${picked.has(p.id) ? "checked" : ""}/></td><td class="text-muted">#${p.id}</td><td class="whitespace-nowrap">${dateStr(p.created_at)}</td><td>${esc(p.farm || "—")}</td><td>${kindBadge(p.kind)}</td><td class="text-xs text-muted max-w-[220px] truncate" title="${esc(inputSummary(p))}">${esc(inputSummary(p))}</td><td class="font-medium">${esc(p.summary)}</td><td class="text-xs text-muted">${esc(p.model_version)}</td><td>${statusBadge(p.status)}</td>
      <td class="whitespace-nowrap"><a class="text-primary p-1" href="#/prediction/${p.id}" title="View">${icon("visibility")}</a><a class="text-primary p-1" href="/api/reports/pdf?pid=${p.id}" title="Download">${icon("download")}</a><button class="text-muted hover:text-alert p-1" data-hdel="${p.id}" title="Delete">${icon("delete")}</button></td></tr>`).join("")}</tbody></table>`
      : empty("history", "No predictions match these filters.");
    $$("[data-pick]").forEach((c) => (c.onchange = () => { c.checked ? picked.add(+c.dataset.pick) : picked.delete(+c.dataset.pick); $("#cmp").disabled = picked.size < 2; }));
    $$("[data-hdel]").forEach((b) => (b.onclick = async () => { if (await confirmBox(`Delete prediction #${b.dataset.hdel}? This cannot be undone.`)) { await api(`/api/predictions/${b.dataset.hdel}`, { method: "DELETE" }); picked.delete(+b.dataset.hdel); load(); } }));
  };
  $("#cmp").onclick = async () => {
    const ps = await Promise.all([...picked].slice(0, 4).map((id) => api(`/api/predictions/${id}`)));
    const keys = [...new Set(ps.flatMap((p) => Object.keys(p.inputs)))];
    modal(`<h3 class="text-lg font-semibold mb-3">Compare predictions</h3><div class="overflow-x-auto"><table class="tbl"><thead><tr><th></th>${ps.map((p) => `<th>#${p.id}</th>`).join("")}</tr></thead><tbody>
      <tr><td class="text-muted">Type</td>${ps.map((p) => `<td>${kindBadge(p.kind)}</td>`).join("")}</tr><tr><td class="text-muted">Date</td>${ps.map((p) => `<td>${dateStr(p.created_at)}</td>`).join("")}</tr>
      <tr><td class="text-muted">Result</td>${ps.map((p) => `<td class="font-semibold">${esc(p.summary)}</td>`).join("")}</tr>
      ${keys.map((k) => `<tr><td class="text-muted">${esc(k)}</td>${ps.map((p) => `<td>${esc(p.inputs[k] ?? "—")}</td>`).join("")}</tr>`).join("")}</tbody></table></div><div class="flex justify-end mt-4"><button class="btn btn-ghost" onclick="closeModal()">Close</button></div>`);
  };
  let tmr; f.oninput = () => { clearTimeout(tmr); tmr = setTimeout(() => load().catch(fail), 250); };
  await load();
};
PAGES.prediction = async (v, id) => {
  const p = await api(`/api/predictions/${id}`);
  const r = p.result;
  let body = "";
  if (p.kind === "crop") body = `<div class="text-3xl font-bold text-primary-dark">${esc(title(r.crop))}</div><p class="text-sm text-muted mt-1">${pct(r.confidence)} probability · ${esc(r.model)}</p><div class="mt-3 text-sm">Alternatives: ${r.top.slice(1).map((a) => `${esc(title(a.crop))} (${pct(a.probability)})`).join(", ")}</div>`;
  if (p.kind === "yield") body = `<div class="text-3xl font-bold text-primary-dark">${fmt(r.yield_t_ha, 2)} t/ha</div><p class="text-sm text-muted mt-1">80% interval ${fmt(r.interval_80[0], 2)}–${fmt(r.interval_80[1], 2)} · district average ${fmt(r.district_mean_t_ha, 2)} t/ha · ${r.production_t != null ? `production ${fmt(r.production_t, 1)} t` : ""}</p>`;
  if (p.kind === "fertiliser") body = `<div class="text-2xl font-bold text-primary-dark">${esc(r.fertiliser?.name || r.category)}</div>${r.fertiliser?.name ? `<p class="text-sm text-muted mt-1">${esc(r.fertiliser.grade)} · ${esc(r.fertiliser.supplies)} · ${pct(r.fertiliser.confidence)} model confidence</p>` : ""}<ul class="text-sm mt-2 space-y-1">${r.explanation.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>${r.options?.length ? `<div class="mt-2 text-sm"><b>Options:</b> ${r.options.map(esc).join("; ")}</div>` : ""}`;
  if (p.kind === "disease") body = `<div class="text-2xl font-bold">${esc(p.summary)}</div><p class="text-sm text-muted mt-1">Verdict: ${esc(r.verdict)} · threshold ${pct(r.threshold)}</p><div class="text-sm mt-2">${r.top.map((x) => `${esc(x.crop)} — ${esc(x.condition)}: ${pct(x.probability)}`).join("<br>")}</div>${r.info ? `<p class="text-sm mt-3"><b>Next steps:</b> ${esc(r.info.management)}</p>` : ""}`;
  v.innerHTML = header(`Prediction #${p.id}`, `${title(p.kind)} · ${dateStr(p.created_at)}${p.farm ? ` · ${p.farm}` : ""}`, `<a href="#/history" class="btn btn-ghost">${icon("arrow_back")} ${t("Prediction History")}</a><a href="/api/reports/pdf?pid=${p.id}" class="btn btn-primary">${icon("picture_as_pdf")} ${t("Download PDF")}</a>`) + `
  <div class="grid lg:grid-cols-2 gap-5"><div class="card p-5"><div class="flex gap-2 mb-3">${kindBadge(p.kind)}${statusBadge(p.status)}<span class="badge b-grey">${esc(p.model_version)}</span></div>${body}</div>
  <div class="card p-5"><h3 class="font-semibold mb-3">Inputs</h3><table class="tbl"><tbody>${Object.entries(p.inputs).map(([k, x]) => `<tr><td class="text-muted">${esc(k)}</td><td class="font-medium">${esc(x)}</td></tr>`).join("")}</tbody></table></div></div>`;
};

// ---------------- reports ----------------
PAGES.reports = async (v) => {
  await loadFarms();
  const all = (await api("/api/predictions?limit=1000")).predictions;
  const kinds = [["crop", "Crop recommendation reports", "psychology"], ["yield", "Crop yield reports", "trending_up"], ["fertiliser", "Fertiliser recommendation reports", "science"], ["disease", "Plant disease reports", "coronavirus"]];
  v.innerHTML = header(t("Reports & Analytics"), "Summaries of your own predictions, ready to download.") + `
  <form id="rf" class="card p-4 mb-5 grid grid-cols-2 md:grid-cols-4 gap-3 items-end text-sm">
    <div class="field"><label>${t("Farm")}</label><select name="farm_id"><option value="">${t("All")}</option>${S.farms.map((f) => `<option value="${f.id}">${esc(f.name)}</option>`).join("")}</select></div>
    <div class="field"><label>From</label><input type="date" name="start"/></div><div class="field"><label>To</label><input type="date" name="end"/></div>
    <div class="flex gap-2"><a id="allcsv" class="btn btn-ghost flex-1">${icon("table")} CSV</a><a id="allpdf" class="btn btn-primary flex-1">${icon("picture_as_pdf")} PDF</a></div>
  </form>
  <div class="grid lg:grid-cols-3 gap-5 mb-5">
    <div class="card p-5"><h3 class="font-semibold mb-3">Predictions by type</h3><div class="h-56"><canvas id="r-kind"></canvas></div></div>
    <div class="card p-5"><h3 class="font-semibold mb-3">Activity over time</h3><div class="h-56"><canvas id="r-time"></canvas></div></div>
    <div class="card p-5"><h3 class="font-semibold mb-3">Recommended crops</h3><div class="h-56"><canvas id="r-crops"></canvas></div></div>
  </div>
  <div class="grid md:grid-cols-2 gap-4">${kinds.map(([k, l, ic]) => { const n = all.filter((p) => p.kind === k); return `<div class="card p-5"><div class="flex items-center gap-2">${icon(ic, "text-primary")}<h3 class="font-semibold">${l}</h3><span class="badge b-grey ml-auto">${n.length}</span></div><div class="text-sm text-muted mt-2 min-h-[40px]">${n.length ? n.slice(0, 3).map((p) => `${dateStr(p.created_at)} — ${esc(p.summary)}`).join("<br>") : "No predictions of this type yet."}</div><div class="flex gap-2 mt-3"><a data-rk="${k}" data-fmt="csv" class="btn btn-ghost flex-1">${icon("table")} ${t("Download CSV")}</a><a data-rk="${k}" data-fmt="pdf" class="btn btn-ghost flex-1">${icon("picture_as_pdf")} ${t("Download PDF")}</a></div></div>`; }).join("")}
    <div class="card p-5"><div class="flex items-center gap-2">${icon("partly_cloudy_day", "text-primary")}<h3 class="font-semibold">Weather reports</h3></div><p class="text-sm text-muted mt-2">Historical NASA POWER charts for any period are on the Weather page.</p><a href="#/weather" class="btn btn-ghost mt-3">${icon("open_in_new")} ${t("Weather Insights")}</a></div>
    <div class="card p-5"><div class="flex items-center gap-2">${icon("landslide", "text-primary")}<h3 class="font-semibold">Soil health reports</h3></div><p class="text-sm text-muted mt-2">SoilGrids profiles by depth for each farm are on the Soil Health page.</p><a href="#/soil" class="btn btn-ghost mt-3">${icon("open_in_new")} ${t("Soil Health")}</a></div>
  </div>`;
  const f = $("#rf");
  const qs = (k) => new URLSearchParams(Object.fromEntries(Object.entries({ ...formData(f), kind: k }).filter(([, x]) => x))).toString();
  const upd = () => { $("#allcsv").href = `/api/reports/csv?${qs("")}`; $("#allpdf").href = `/api/reports/pdf?${qs("")}`; $$("[data-rk]").forEach((a) => (a.href = `/api/reports/${a.dataset.fmt}?${qs(a.dataset.rk)}`)); };
  f.oninput = upd; upd();
  if (!all.length) return;
  chart($("#r-kind"), { type: "doughnut", data: { labels: kinds.map((k) => title(k[0])), datasets: [{ data: kinds.map(([k]) => all.filter((p) => p.kind === k).length), backgroundColor: [C.green, C.blue, C.yellow, C.red] }] }, options: { cutout: "60%", plugins: { legend: { position: "bottom" } } } });
  const byDay = {}; all.forEach((p) => { const d = new Date(p.created_at * 1000).toISOString().slice(0, 10); byDay[d] = (byDay[d] || 0) + 1; });
  const days = Object.keys(byDay).sort();
  chart($("#r-time"), { type: "bar", data: { labels: days, datasets: [{ label: "Predictions", data: days.map((d) => byDay[d]), backgroundColor: C.green2, borderRadius: 4 }] }, options: { plugins: { legend: { display: false } }, scales: { y: { ticks: { precision: 0 } } } } });
  const cc = {}; all.filter((p) => p.kind === "crop").forEach((p) => (cc[p.crop] = (cc[p.crop] || 0) + 1));
  const ck = Object.keys(cc).sort((a, b) => cc[b] - cc[a]).slice(0, 8);
  chart($("#r-crops"), { type: "bar", data: { labels: ck.map(title), datasets: [{ data: ck.map((k) => cc[k]), backgroundColor: C.green, borderRadius: 4 }] }, options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { ticks: { precision: 0 } } } } });
};

// ---------------- settings ----------------
PAGES.settings = async (v) => {
  const u = (await api("/api/me")).user; S.user = u;
  v.innerHTML = header(t("Settings"), "Your profile, preferences and account.") + `
  <div class="grid lg:grid-cols-2 gap-5">
    <form id="pf" class="card p-5 space-y-3"><h3 class="font-semibold">${t("Profile")}</h3>
      <div class="field"><label>${t("Full name")}</label><input name="name" value="${esc(u.name)}"/></div>
      <div class="grid grid-cols-2 gap-3"><div class="field"><label>${t("Email")}</label><input value="${esc(u.email || "—")}" disabled/></div><div class="field"><label>${t("Phone")}</label><input value="${esc(u.phone || "—")}" disabled/></div></div>
      <div class="grid grid-cols-2 gap-3"><div class="field"><label>${t("State")}</label><input name="state" value="${esc(u.state || "")}"/></div><div class="field"><label>${t("District")}</label><input name="district" value="${esc(u.district || "")}"/><div class="hint">Used for weather when no farm has coordinates.</div></div></div>
      <button class="btn btn-primary">${icon("save")} ${t("Save")}</button></form>
    <form id="prf" class="card p-5 space-y-3"><h3 class="font-semibold">Preferences</h3>
      <div class="field"><label>${t("Language")}</label><select name="language" data-nt>${LANGS.map(([c, n]) => `<option value="${c}" ${u.language === c ? "selected" : ""}>${n}</option>`).join("")}</select><div class="hint">Interface and assistant answers. Non-English text is translated by Azure AI Translator.</div></div>
      <div class="field"><label>Theme</label><select id="theme-pick"><option value="system" ${themePref() === "system" ? "selected" : ""}>Follow my device</option><option value="light" ${themePref() === "light" ? "selected" : ""}>Light</option><option value="dark" ${themePref() === "dark" ? "selected" : ""}>Dark</option></select></div>
      <div class="field"><label>Units</label><select name="units"><option value="metric">Metric (ha, t/ha, °C, mm)</option></select><div class="hint">All models were trained in metric units, so other units are not offered.</div></div>
      <label class="flex items-center gap-2 text-sm"><input type="checkbox" name="notify_weather" ${u.notify_weather ? "checked" : ""} class="accent-primary w-4 h-4"/> Weather alerts in the notification bell</label>
      <label class="flex items-center gap-2 text-sm"><input type="checkbox" name="share_farm_with_assistant" ${u.share_farm_with_assistant ? "checked" : ""} class="accent-primary w-4 h-4"/> Let the AI assistant read my farms and recent predictions (privacy)</label>
      <button class="btn btn-primary">${icon("save")} ${t("Save")}</button></form>
    <form id="pwf" class="card p-5 space-y-3" novalidate><h3 class="font-semibold">Change password</h3>
      <div class="field"><label>Current password</label><input type="password" name="current" autocomplete="current-password"/></div>
      <div class="field"><label>New password</label><input type="password" name="new" autocomplete="new-password"/><div class="hint">At least 8 characters with letters and numbers. You will be signed out everywhere.</div></div>
      <button class="btn btn-primary">${icon("lock_reset")} Update password</button></form>
    <div class="card p-5 space-y-3"><h3 class="font-semibold">Account</h3><p class="text-sm text-muted">Download everything you have created, or delete your account and all its data.</p>
      <div class="flex flex-wrap gap-2"><a href="/api/reports/csv" class="btn btn-ghost">${icon("download")} Export my predictions</a><button id="delacc" class="btn btn-danger">${icon("delete_forever")} Delete account</button></div></div>
  </div>`;
  $("#pf").onsubmit = async (e) => { e.preventDefault(); try { S.user = (await api("/api/me", { method: "PUT", body: formData(e.target) })).user; toast("Profile saved"); shell(); route(); } catch (er) { fail(er); } };
  $("#theme-pick") && ($("#theme-pick").onchange = (e) => setTheme(e.target.value));
  $("#prf").onsubmit = async (e) => { e.preventDefault(); const d = formData(e.target); d.notify_weather = d.notify_weather ? 1 : 0; d.share_farm_with_assistant = d.share_farm_with_assistant ? 1 : 0; try { S.user = (await api("/api/me", { method: "PUT", body: d })).user; LANG = S.user.language; localStorage.setItem("lang", LANG); toast("Preferences saved"); shell(); route(); } catch (er) { fail(er); } };
  $("#pwf").onsubmit = async (e) => { e.preventDefault(); try { await api("/api/me/password", { method: "PUT", body: formData(e.target) }); toast("Password changed. Please sign in again."); S.user = null; renderAuth("login"); } catch (er) { showFieldErrors(e.target, er); fail(er); } };
  $("#delacc").onclick = () => modal(`<h3 class="text-lg font-semibold mb-2">Delete your account?</h3><p class="text-sm text-muted mb-3">This permanently removes your profile, farms, predictions and conversations. It cannot be undone.</p><form id="dlf" class="space-y-3"><div class="field"><label>Enter your password to confirm</label><input type="password" name="password"/></div><div class="flex justify-end gap-2"><button type="button" class="btn btn-ghost" onclick="closeModal()">${t("Cancel")}</button><button class="btn btn-danger">Delete permanently</button></div></form>`, (m) => {
    $("#dlf", m).onsubmit = async (e) => { e.preventDefault(); try { await api("/api/me/delete", { method: "POST", body: formData(e.target) }); closeModal(); S.user = null; toast("Account deleted"); renderAuth("register"); } catch (er) { fail(er); } };
  });
};
PAGES.help = async (v) => {
  const s = await api("/api/status");
  const m = s.models;
  v.innerHTML = header(t("Help & Support"), "How each tool works, and what it can and cannot tell you.") + `
  <div class="grid lg:grid-cols-2 gap-5">${[
    ["psychology", "Crop recommendation", `${m.crop.name} trained on 2,200 samples of 22 crops. Test accuracy ${pct(m.crop.test_accuracy)}. It only knows those 22 crops.`],
    ["trending_up", "Yield prediction", `LightGBM trained on Indian district crop statistics 1997–2020, tested on later years (MAE ${m.yield.test_mae} t/ha, R² ${m.yield.test_r2}). It does not use weather or soil.`],
    ["science", "Fertiliser", `${m.fertiliser.name || "Fertiliser model"} trained on Fertilizer Prediction.csv (99 rows, 7 fertilisers), cross-validated accuracy ${pct(m.fertiliser.cv_accuracy)}. Your soil values are turned into a nutrient shortfall first; it names a fertiliser, never a dose.`],
    ["coronavirus", "Disease detection", m.disease.ready ? `${m.disease.name}, test accuracy ${pct(m.disease.test_accuracy)} on lab-style leaf photos. It refuses to answer below its confidence threshold.` : "Model not loaded."],
    ["partly_cloudy_day", "Weather", "Live forecast from Open-Meteo; history from NASA POWER gridded estimates (not station readings)."],
    ["landslide", "Soil", "ISRIC SoilGrids 250 m modelled estimates with 90% ranges. Not a substitute for a lab soil test."],
  ].map(([ic, h, txt]) => `<div class="card p-5 flex gap-3">${icon(ic, "text-primary !text-3xl")}<div><h3 class="font-semibold">${h}</h3><p class="text-sm text-muted mt-1">${esc(txt)}</p></div></div>`).join("")}</div>
  <div class="card p-5 mt-5"><h3 class="font-semibold mb-1">Need agronomic help?</h3><p class="text-sm text-muted">Contact your district Krishi Vigyan Kendra, or call the Kisan Call Centre on <b>1800-180-1551</b> (toll-free).</p></div>`;
};

// ---------------- auth ----------------
function renderAuth(mode) {
  const reg = mode === "register";
  $("#root").innerHTML = `
  <div class="min-h-screen grid lg:grid-cols-2">
    <div class="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-[#e2f2e8] via-mint to-cream relative overflow-hidden">
      <div class="flex items-center gap-2.5"><img src="/favicon.svg" class="w-9 h-9" alt=""/><div class="font-semibold text-lg">AgriSense AI</div></div>
      <div><h1 class="text-4xl font-bold tracking-tight max-w-md">Smarter farming decisions, from soil to harvest.</h1><p class="text-muted mt-3 max-w-md">Crop and fertiliser recommendations, yield estimates, leaf disease screening, live weather and soil data — in one place.</p></div>
      <svg viewBox="0 0 400 180" class="w-full max-w-lg" aria-hidden="true"><path d="M0 150 Q100 110 200 140 T400 125 V180 H0Z" fill="#cfe8d7"/><path d="M0 165 Q120 140 240 160 T400 150 V180 H0Z" fill="#b5dbc2"/>${Array.from({ length: 12 }, (_, i) => 20 + i * 32).map((x) => `<g transform="translate(${x} 145)"><path d="M0 0 V-34" stroke="#2E8B57" stroke-width="3"/><path d="M0 -14 Q-12 -22 -15 -34 Q-3 -27 0 -14Z M0 -22 Q12 -30 15 -42 Q3 -35 0 -22Z" fill="#62A87C"/></g>`).join("")}<circle cx="340" cy="40" r="22" fill="#E8B94F" opacity=".85"/></svg>
    </div>
    <div class="flex items-center justify-center p-6 bg-white">
      <form id="af" class="w-full max-w-md space-y-4" novalidate>
        <div class="lg:hidden flex items-center gap-2 mb-2"><img src="/favicon.svg" class="w-8 h-8" alt=""/><span class="font-semibold">AgriSense AI</span></div>
        <div><h2 class="text-2xl font-semibold">${reg ? t("Create account") : t("Sign in")}</h2><p class="text-sm text-muted mt-1">${reg ? "Already registered?" : "New to AgriSense AI?"} <a href="#" id="swap" class="text-primary font-semibold">${reg ? t("Sign in") : t("Create account")}</a></p></div>
        ${reg ? `
          <div class="field"><label>${t("Full name")}</label><input name="name" autocomplete="name"/></div>
          <div class="grid grid-cols-2 gap-3"><div class="field"><label>${t("Email")}</label><input name="email" type="email" autocomplete="email"/></div><div class="field"><label>${t("Phone")}</label><input name="phone" inputmode="tel" autocomplete="tel"/></div></div>
          <div class="field"><label>${t("Password")}</label><input name="password" type="password" autocomplete="new-password"/><div class="hint">At least 8 characters with letters and numbers.</div></div>
          <div class="grid grid-cols-2 gap-3"><div class="field"><label>${t("State")}</label><select name="state"><option value="">Select…</option></select></div><div class="field"><label>${t("District")}</label><input name="district" list="distlist"/><datalist id="distlist"></datalist></div></div>
          <div class="field"><label>${t("Role")}</label><select name="role"><option value="farmer">Farmer</option><option value="agri_officer">Agricultural officer</option><option value="researcher">Researcher</option></select></div>`
        : `
          <div class="field"><label>${t("Email or phone")}</label><input name="identifier" autocomplete="username"/></div>
          <div class="field"><label>${t("Password")}</label><input name="password" type="password" autocomplete="current-password"/></div>
          <div class="flex items-center justify-between text-sm"><label class="flex items-center gap-2"><input type="checkbox" name="remember" class="accent-primary w-4 h-4" checked/> ${t("Remember me")}</label><a href="#" id="forgot" class="text-primary font-semibold">${t("Forgot password?")}</a></div>`}
        <button class="btn btn-primary w-full !py-3" id="ago">${reg ? t("Create account") : t("Sign in")}</button>
        <div class="flex justify-center items-center gap-2 text-xs pt-2"><label class="lang-pick" title="Language">${icon("translate", "!text-base text-primary")}${langSelect("auth-lang")}</label><button type="button" id="auth-theme" class="p-1.5 rounded-full hover:bg-mint text-muted" title="${isDark() ? "Light mode" : "Dark mode"}">${icon(isDark() ? "light_mode" : "dark_mode")}</button></div>
      </form>
    </div>
  </div>`;
  $("#swap").onclick = (e) => { e.preventDefault(); renderAuth(reg ? "login" : "register"); };
  $("#auth-lang").onchange = (e) => setLang(e.target.value);   // in place: what was typed stays
  $("#auth-theme").onclick = () => setTheme(isDark() ? "light" : "dark");
  if (!reg) $("#forgot").onclick = (e) => { e.preventDefault(); renderForgot(); };
  if (reg) fetch("/api/public/states").then((r) => r.json()).then((d) => { d.states.forEach((s) => $("[name=state]").insertAdjacentHTML("beforeend", `<option>${esc(s)}</option>`)); }).catch(() => {});
  if (reg) $("[name=state]").onchange = (e) => fetch(`/api/public/districts?state=${encodeURIComponent(e.target.value)}`).then((r) => r.json()).then((d) => ($("#distlist").innerHTML = d.districts.map((x) => `<option>${esc(title(x.toLowerCase()))}</option>`).join(""))).catch(() => {});
  $("#af").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await busy($("#ago"), () => api(reg ? "/api/auth/register" : "/api/auth/login", { method: "POST", body: formData(e.target) }));
      if (r.otp_required) return renderOtp(r, mode);
      signedIn(r);
    } catch (er) { showFieldErrors(e.target, er); fail(er); }
  };
}

function signedIn(r) {
  S.user = r.user; LANG = S.user.language || LANG; localStorage.setItem("lang", LANG);
  shell();
  // Setting the hash fires hashchange -> route(); calling route() as well ran two renders at once.
  if (!location.hash || location.hash === "#") location.hash = "#/overview";
  else route();
}

// Same two-column frame as the sign-in page, with any form on the right.
function authFrame(inner) {
  renderAuth("login");
  $("#af").outerHTML = inner;
}

function renderForgot() {
  authFrame(`<form id="ff2" class="w-full max-w-md space-y-4" novalidate>
    <div><h2 class="text-2xl font-semibold">Reset your password</h2><p class="text-sm text-muted mt-1">Enter your account e-mail and a new password. We will e-mail you a 6-digit code to confirm it is you.</p></div>
    <div class="field"><label>${t("Email")}</label><input name="email" type="email" autocomplete="email"/></div>
    <div class="field"><label>New password</label><input name="new_password" type="password" autocomplete="new-password"/><div class="hint">At least 8 characters with letters and numbers.</div></div>
    <button class="btn btn-primary w-full !py-3" id="fgo">Send code</button>
    <a href="#" id="back" class="block text-center text-sm text-primary font-semibold">Back to sign in</a>
  </form>`);
  $("#back").onclick = (e) => { e.preventDefault(); renderAuth("login"); };
  $("#ff2").onsubmit = async (e) => {
    e.preventDefault();
    try { renderOtp(await busy($("#fgo"), () => api("/api/auth/forgot", { method: "POST", body: formData(e.target) })), "login"); }
    catch (er) { showFieldErrors(e.target, er); fail(er); }
  };
}

function renderOtp(ch, backTo) {
  const what = { signup: "finish creating your account", login: "finish signing in", reset: "set your new password" }[ch.purpose] || "continue";
  authFrame(`<form id="of" class="w-full max-w-md space-y-4" novalidate>
    <div class="w-12 h-12 rounded-2xl bg-mint-2 text-primary flex items-center justify-center">${icon("mark_email_read", "!text-3xl")}</div>
    <div><h2 class="text-2xl font-semibold">Check your e-mail</h2><p class="text-sm text-muted mt-1">We sent a 6-digit code to <b>${esc(ch.email)}</b>. Enter it to ${what}. It expires in ${Math.round(ch.expires_in / 60)} minutes.</p></div>
    <div class="field"><label>Verification code</label><input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" class="!text-2xl !tracking-[0.5em] text-center font-semibold" placeholder="••••••"/></div>
    <button class="btn btn-primary w-full !py-3" id="ogo">Verify</button>
    <div class="flex items-center justify-between text-sm"><a href="#" id="oback" class="text-muted">← Start again</a><button type="button" id="oresend" class="text-primary font-semibold disabled:text-muted" disabled>Resend code</button></div>
    <p class="text-xs text-muted">Did not get it? Check the spam folder. The e-mail comes from support@visioncoders.online.</p>
  </form>`);
  const code = $("[name=code]"); code.focus();
  code.oninput = () => { code.value = code.value.replace(/\D/g, "").slice(0, 6); if (code.value.length === 6) $("#of").requestSubmit(); };
  let wait = ch.resend_in || 60, timer;
  const tick = () => { const b = $("#oresend"); if (!b) return clearInterval(timer); b.disabled = wait > 0; b.textContent = wait > 0 ? `Resend in ${wait}s` : "Resend code"; wait--; };
  tick(); timer = setInterval(tick, 1000);
  $("#oresend").onclick = async () => {
    try { const r = await api("/api/auth/otp/resend", { method: "POST", body: { challenge_id: ch.challenge_id } }); toast(`New code sent to ${r.email}`); wait = r.resend_in || 60; tick(); }
    catch (er) { fail(er); }
  };
  $("#oback").onclick = (e) => { e.preventDefault(); clearInterval(timer); renderAuth(backTo === "register" ? "register" : "login"); };
  $("#of").onsubmit = async (e) => {
    e.preventDefault();
    if (code.value.length !== 6) return fail({ error: "Enter the 6-digit code" });
    try { const r = await busy($("#ogo"), () => api("/api/auth/otp/verify", { method: "POST", body: { challenge_id: ch.challenge_id, code: code.value } })); clearInterval(timer); if (ch.purpose === "reset") toast("Password changed"); signedIn(r); }
    catch (er) { code.value = ""; code.focus(); fail(er); }
  };
}

// ---------------- boot ----------------
(async () => {
  try { LANG = localStorage.getItem("lang") || "en"; } catch {}
  TR.start();
  try { S.user = (await api("/api/me")).user; LANG = S.user.language || LANG; shell(); route(); }
  catch { renderAuth("login"); }
})();
