// UI strings. Hindi covers navigation, headings, buttons and form labels.
window.I18N = {
  hi: {
    "Overview": "अवलोकन", "Crop Recommendation": "फसल सुझाव", "Yield Prediction": "उपज अनुमान",
    "Fertiliser Recommendation": "उर्वरक सुझाव", "Plant Disease Detection": "पौध रोग पहचान",
    "AI Farming Assistant": "एआई कृषि सहायक", "Weather Insights": "मौसम जानकारी", "Soil Health": "मृदा स्वास्थ्य",
    "Farm Management": "खेत प्रबंधन", "Prediction History": "अनुमान इतिहास", "Reports & Analytics": "रिपोर्ट और विश्लेषण",
    "Settings": "सेटिंग्स", "Help & Support": "सहायता", "Logout": "लॉग आउट",
    "Good morning": "सुप्रभात", "Good afternoon": "नमस्कार", "Good evening": "शुभ संध्या",
    "New Prediction": "नया अनुमान", "Registered farms": "पंजीकृत खेत", "Crop recommendations": "फसल सुझाव",
    "Avg predicted yield": "औसत अनुमानित उपज", "Disease scans": "रोग जांच", "Fertiliser checks": "उर्वरक जांच",
    "Yield predictions": "उपज अनुमान", "Recent predictions": "हाल के अनुमान", "View all": "सभी देखें",
    "AI Farming Insights": "एआई कृषि सुझाव", "Ask AI Assistant": "एआई सहायक से पूछें",
    "Crop production analytics": "फसल उत्पादन विश्लेषण", "Weather": "मौसम",
    "AI Crop Recommendation": "एआई फसल सुझाव", "Predict Suitable Crop": "उपयुक्त फसल बताएं",
    "Crop Yield Prediction": "फसल उपज अनुमान", "Predict Crop Yield": "उपज अनुमान करें",
    "Smart Fertiliser Recommendation": "स्मार्ट उर्वरक सुझाव", "Get Recommendation": "सुझाव पाएं",
    "AI Plant Disease Detection": "एआई पौध रोग पहचान", "Analyse Image": "चित्र जांचें",
    "AgriSense AI Assistant": "एग्रीसेंस एआई सहायक", "Weather & Climate Intelligence": "मौसम और जलवायु",
    "Soil Health & Nutrient Analysis": "मृदा स्वास्थ्य और पोषक विश्लेषण", "My Farms": "मेरे खेत",
    "Add farm": "खेत जोड़ें", "Edit": "बदलें", "Delete": "हटाएं", "View": "देखें", "Save": "सहेजें", "Cancel": "रद्द करें",
    "Clear": "साफ़ करें", "Use farm data": "खेत का डेटा लें", "Download CSV": "CSV डाउनलोड", "Download PDF": "PDF डाउनलोड",
    "Nitrogen (N)": "नाइट्रोजन (N)", "Phosphorus (P)": "फॉस्फोरस (P)", "Potassium (K)": "पोटैशियम (K)",
    "Temperature": "तापमान", "Humidity": "आर्द्रता", "Soil pH": "मिट्टी का pH", "Rainfall": "वर्षा",
    "State": "राज्य", "District": "ज़िला", "Crop": "फसल", "Season": "मौसम", "Year": "वर्ष", "Cultivated area": "खेती का क्षेत्रफल",
    "Sign in": "साइन इन", "Create account": "खाता बनाएं", "Email or phone": "ईमेल या फ़ोन", "Password": "पासवर्ड",
    "Full name": "पूरा नाम", "Email": "ईमेल", "Phone": "फ़ोन", "Role": "भूमिका", "Remember me": "मुझे याद रखें",
    "Forgot password?": "पासवर्ड भूल गए?", "Search": "खोजें", "Notifications": "सूचनाएं",
    "New conversation": "नई बातचीत", "Saved": "सहेजे गए", "Send": "भेजें", "Type your question": "अपना सवाल लिखें",
    "Location": "स्थान", "Start date": "आरंभ तिथि", "End date": "अंतिम तिथि", "Load": "लोड करें",
    "Depth": "गहराई", "Status": "स्थिति", "Date": "तारीख", "Type": "प्रकार", "Result": "परिणाम", "Confidence": "विश्वास",
    "Farm": "खेत", "Action": "कार्य", "All": "सभी", "Model": "मॉडल", "Profile": "प्रोफ़ाइल", "Language": "भाषा",
  }
};
// Pages always render English; the DOM translator below swaps in Hindi (dictionary first) or any other language,
// and can put the English back, so switching language never has to re-render (results stay on screen).
window.t = (s) => s;

// English + 14 Indian languages. Hindi has a hand-checked dictionary above; every other string (and
// any Hindi gap) is translated by Azure AI Translator through /api/i18n/translate and cached.
window.LANGS = [
  ["en", "English"], ["hi", "हिन्दी"], ["bn", "বাংলা"], ["mr", "मराठी"], ["te", "తెలుగు"], ["ta", "தமிழ்"],
  ["gu", "ગુજરાતી"], ["ur", "اردو"], ["kn", "ಕನ್ನಡ"], ["or", "ଓଡ଼ିଆ"], ["ml", "മലയാളം"], ["pa", "ਪੰਜਾਬੀ"],
  ["as", "অসমীয়া"], ["mai", "मैथिली"], ["gom", "कोंकणी"],
];
window.SPEECH_LANG = { en: "en-IN", hi: "hi-IN", bn: "bn-IN", mr: "mr-IN", te: "te-IN", ta: "ta-IN", gu: "gu-IN", ur: "ur-IN",
  kn: "kn-IN", or: "or-IN", ml: "ml-IN", pa: "pa-IN", as: "as-IN", mai: "hi-IN", gom: "hi-IN" };

// DOM translator: finds English text in the page and swaps in the cached translation. New text from
// re-renders, toasts and dialogs is picked up by a MutationObserver. User content (chat messages,
// inputs, farm notes) and icon ligatures are never touched or sent.
window.TR = (() => {
  const SKIP = ".material-symbols-outlined, .notranslate, [data-nt], script, style, textarea, code, pre, .bubble-user, .prose-chat, .leaflet-container, input, select[data-nt]";
  const WORD = /[A-Za-z]{2,}/;
  const mem = {};               // lang -> {english: translated}
  const pending = new Set();
  let busy = false, timer = null, observer = null, failedAt = 0;
  const store = (l) => { try { localStorage.setItem("tr:" + l, JSON.stringify(mem[l])); } catch {} };
  const dict = (l) => {
    if (!mem[l]) { try { mem[l] = JSON.parse(localStorage.getItem("tr:" + l) || "{}"); } catch { mem[l] = {}; } }
    return mem[l];
  };
  const keep = new Set();         // people's and farm names: never translated
  const wanted = (s) => WORD.test(s) && s.length <= 400 && !keep.has(s);
  const lookup = (l, s) => (l === "hi" && window.I18N.hi[s]) || dict(l)[s];

  function swapText(node, l) {
    const raw = node.nodeValue, s = raw.trim();
    if (!s) return;
    if (node.__en !== undefined && (raw === node.__tr)) return;     // already translated by us
    if (!wanted(s)) return;
    const hit = lookup(l, s);
    if (hit) { if (node.__en === undefined || node.nodeValue !== node.__tr) node.__en = raw; node.__tr = raw.replace(s, hit); node.nodeValue = node.__tr; }
    else pending.add(s);
  }
  function swapAttr(el, a, l) {
    const s = (el.getAttribute(a) || "").trim();
    if (!s || !wanted(s) || el["__tr_" + a] === s) return;
    const hit = lookup(l, s);
    if (hit) { if (el["__en_" + a] === undefined) el["__en_" + a] = s; el["__tr_" + a] = hit; el.setAttribute(a, hit); } else pending.add(s);
  }
  function pass() {
    const l = window.LANG;
    if (!l || l === "en") return;
    const roots = [document.getElementById("root"), document.getElementById("modal"), document.getElementById("toasts")].filter(Boolean);
    for (const root of roots) {
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode: (n) => (n.parentElement && !n.parentElement.closest(SKIP) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT) });
      let n; while ((n = w.nextNode())) swapText(n, l);
      root.querySelectorAll("[placeholder],[title],[aria-label]").forEach((el) => {
        if (el.closest(".material-symbols-outlined, .notranslate, [data-nt]")) return;
        ["placeholder", "title", "aria-label"].forEach((a) => el.hasAttribute(a) && swapAttr(el, a, l));
      });
    }
    if (pending.size) fetchMissing(l);
  }
  async function fetchMissing(l) {
    if (busy || Date.now() - failedAt < 15000) return;
    busy = true;
    const batch = [...pending].slice(0, 150);
    batch.forEach((s) => pending.delete(s));
    try {
      const r = await fetch("/api/i18n/translate", { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lang: l, texts: batch }) });
      if (!r.ok) throw new Error(r.status);
      const j = await r.json();
      Object.assign(dict(l), j.translations || {});
      batch.forEach((s) => { if (!dict(l)[s]) dict(l)[s] = s; });   // untranslatable: stop asking
      store(l);
    } catch { failedAt = Date.now(); }
    busy = false;
    if (window.LANG === l) schedule();
  }
  function schedule() { clearTimeout(timer); timer = setTimeout(pass, 40); }
  function start() {
    if (observer) return;
    observer = new MutationObserver(schedule);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["placeholder", "title"] });
    schedule();
  }
  // Text a script needs right now (chart labels): cached translation or English, and queue the rest.
  function now(s) { const l = window.LANG; if (!l || l === "en" || !wanted(s)) return s; const h = lookup(l, s); if (!h) { pending.add(s); schedule(); } return h || s; }
  // Put the original English back on every node we translated (used when the language changes).
  function restore() {
    const roots = [document.getElementById("root"), document.getElementById("modal"), document.getElementById("toasts")].filter(Boolean);
    for (const root of roots) {
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let n; while ((n = w.nextNode())) { if (n.__en !== undefined) { if (n.nodeValue === n.__tr) n.nodeValue = n.__en; n.__en = undefined; n.__tr = undefined; } }
      root.querySelectorAll("[placeholder],[title],[aria-label]").forEach((el) => ["placeholder", "title", "aria-label"].forEach((a) => {
        if (el["__en_" + a] !== undefined) { if (el.getAttribute(a) === el["__tr_" + a]) el.setAttribute(a, el["__en_" + a]); el["__en_" + a] = undefined; el["__tr_" + a] = undefined; }
      }));
    }
  }
  function keepNames(names) { names.filter(Boolean).forEach((n) => { keep.add(String(n).trim()); }); }
  return { start, schedule, now, keepNames, restore };
})();
