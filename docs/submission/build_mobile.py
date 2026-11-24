"""Builds Project/08_Mobile_App_UI_Design.pdf - the light-theme mobile app UI design specification.

Inputs: proposed mockups (mobile_mock/*.png, rendered from mobile_mock/mock.html), the current app at
phone width (mobile/*.png, from capture_mobile.py), measured text expansion (mobile/text_expansion.json),
and the design tokens below (contrast ratios are computed, not typed)."""
import json
import sys
import time
from pathlib import Path

from PIL import Image as PI, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "docs"))
sys.path.insert(0, str(HERE))
import build_report as R  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Image, KeepTogether, PageBreak, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402
from spec import AUTHOR, COURSE, PROGRAMME, PROJECT, URL  # noqa: E402

P, h1, h2, body, small, cap, table, bullets, W = R.P, R.h1, R.h2, R.body, R.small, R.cap, R.table, R.bullets, R.W
for st in (h1, h2):
    st.keepWithNext = 1
h3 = ParagraphStyle("h3", parent=body, fontName="UI-B", fontSize=10.5, leading=14, spaceBefore=6, spaceAfter=2,
                    textColor=colors.HexColor(R.DARK), keepWithNext=1)
MOCK, CUR = HERE / "mobile_mock", HERE / "mobile"
FR = HERE / "mobile_framed"
FR.mkdir(exist_ok=True)
EXP = json.loads((CUR / "text_expansion.json").read_text(encoding="utf-8"))
LANG_NAME = {"hi": "Hindi", "bn": "Bengali", "mr": "Marathi", "te": "Telugu", "ta": "Tamil", "gu": "Gujarati", "ur": "Urdu",
             "kn": "Kannada", "or": "Odia", "ml": "Malayalam", "pa": "Punjabi", "as": "Assamese", "mai": "Maithili", "gom": "Konkani"}


# ------------------------------------------------------------------ helpers
def frame(src, name, crop_h=None):
    """Draw a simple phone bezel around a screenshot."""
    im = PI.open(src).convert("RGB")
    if crop_h and im.height > crop_h * im.width / 375:
        im = im.crop((0, 0, im.width, int(crop_h * im.width / 375)))
    s = im.width / 375
    pad, r = int(12 * s), int(44 * s)
    out = PI.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle([0, 0, out.width - 1, out.height - 1], radius=r + pad, fill=(28, 32, 30, 255))
    mask = PI.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=r, fill=255)
    out.paste(im, (pad, pad), mask)
    p = FR / f"{name}.png"
    bg = PI.new("RGB", out.size, (255, 255, 255))
    bg.paste(out, mask=out.split()[3])
    bg.save(p)
    return p


def phone(path, width_mm=62, caption=None):
    im = PI.open(path)
    w = width_mm * mm
    out = [Image(str(path), width=w, height=w * im.height / im.width)]
    if caption:
        out.append(P(caption, cap))
    return out


def side_by_side(img_flow, text_flow, img_w=0.4):
    t = Table([[img_flow, text_flow]], colWidths=[W * img_w, W * (1 - img_w)])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (1, 0), (1, 0), 12)]))
    return t


def lum(hexc):
    c = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def swatch(hexc):
    t = Table([[""]], colWidths=[9 * mm], rowHeights=[5 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(hexc)),
                           ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3cd"))]))
    return t


TOKENS = [  # name, hex, role, test against
    ("primary", "#2E8B57", "Brand green: icons, active tab indicator, large text, graphics", "#FFFFFF"),
    ("primary-strong", "#2B8352", "Primary button fill and links (white 16 sp text passes AA)", "#FFFFFF"),
    ("primary-dark", "#236B44", "Text on mint, pressed state", "#F1F8F2"),
    ("ink", "#24352B", "Body text, headings", "#FFFFFF"),
    ("muted", "#5F6E66", "Secondary text, captions, inactive tabs", "#FFFFFF"),
    ("background", "#F7FAF8", "Screen background", None),
    ("surface", "#FFFFFF", "Cards, sheets, bars", None),
    ("mint", "#F1F8F2", "Soft fills, secondary buttons, input groups", None),
    ("mint-2", "#E2F2E8", "Selected item, positive chips", None),
    ("line", "#E5ECE6", "Dividers, card borders", None),
    ("sky", "#2F6EA8", "Weather / information accents (text)", "#E6F0FA"),
    ("warning", "#6D5214", "Warning text on amber fill #FBF2DC", "#FBF2DC"),
    ("danger", "#B83C3C", "Low nutrient, disease, delete (text)", "#FDECEB"),
]


def build():
    s = []
    TODAY = time.strftime("%d %B %Y")
    # ---------------- cover
    s += [Spacer(1, 22 * mm), P(PROJECT, ParagraphStyle("pp", parent=h2, fontSize=13)),
          P("Mobile App UI Design", ParagraphStyle("t", parent=h1, fontSize=30, leading=36)),
          P("Light-theme design specification for the Android-first AgriSense AI app: principles, design tokens, "
            "components, every key screen, flows, states, accessibility, localisation and developer hand-off.",
            ParagraphStyle("st", parent=body, fontSize=12, leading=16, textColor=colors.HexColor(R.MUTED))),
          Spacer(1, 6 * mm)]
    covers = [frame(MOCK / f"{n}.png", f"cover_{n}") for n in ("m_home", "m_result", "m_assistant")]
    row = [phone(c, 52)[0] for c in covers]
    t = Table([row], colWidths=[W / 3] * 3)
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    s += [t, Spacer(1, 6 * mm),
          table([["Item", "Details"], ["Prepared by", AUTHOR], ["Programme", PROGRAMME], ["Course", COURSE],
                 ["Web app (baseline)", URL], ["Theme", "Light (primary). Dark exists in the web app; not specified here."],
                 ["Date", TODAY]], [0.28, 0.72]), PageBreak()]

    # ---------------- 1 purpose
    s += [P("1. Purpose and scope", h1),
          P("AgriSense AI already runs as a responsive web app. Farmers, however, use it outdoors on low-cost Android "
            "phones, often one-handed, in bright sun and on patchy data. This document specifies a <b>native-feeling "
            "mobile app</b> (Android first, iOS later; Flutter, React Native or a Capacitor wrapper of the existing app "
            "can all implement it) that keeps the same features and back end but reorganises the interface for phones."),
          table([["In scope", "Out of scope"],
                 ["All farmer-facing screens: onboarding, sign-in with e-mail code, home, the four tools (custom and "
                  "auto input), results, leaf scan with the camera, assistant, weather, soil, farms, history, settings",
                  "Admin tools, tablet layouts, dark theme (already in the web app), new ML features"]],
                [0.5, 0.5]),
          P("Units: sizes in dp (density-independent pixels), text in sp. Mockups are drawn at 375 x 812 dp "
            "(the most common small-phone viewport) and must work from 360 dp wide upwards.", small),
          P("2. Users and context of use", h1),
          table([["Persona", "Situation", "What the design must do"],
                 ["Small farmer (primary), 25-60, basic phone skills, prefers own language", "In the field, sun, one hand, "
                  "2G/4G that drops", "Big targets, icons with words, own language from the first screen, works offline for "
                  "what it can"],
                 ["Agricultural officer / KVK staff", "Visits many farms a day", "Fast repeat tasks, farm switcher, history, "
                  "share PDF"],
                 ["Student / researcher", "Desk, good network", "See model confidence and accuracy, export data"]],
                [0.3, 0.3, 0.4]),
          P("3. Design principles", h1),
          *bullets(["<b>One screen, one job.</b> Each screen answers one farmer question (\"Which crop?\", \"How much?\", "
                    "\"Which fertiliser?\", \"Is it sick?\") with one primary button at the bottom, in thumb reach.",
                    "<b>Words + icons, never icons alone.</b> Every tab, tile and button has a label.",
                    "<b>Language first.</b> The language is chosen before sign-in; 15 languages; the assistant answers in it.",
                    "<b>Show certainty honestly.</b> Every result shows how sure the model is and its measured accuracy; "
                    "unclear leaf photos get \"not sure\" instead of a guess.",
                    "<b>Never a dose.</b> Fertiliser and disease screens name categories and next steps; quantities come from "
                    "the soil test and the KVK (enforced on the server too).",
                    "<b>Readable in sunlight.</b> Light theme, near-black text, 4.5:1 contrast minimum, 16 sp body text.",
                    "<b>Forgiving.</b> Inputs keep their values on errors, theme or language changes; destructive actions ask once.",
                    "<b>Light on data.</b> Photos are resized on the phone before upload; results and translations are cached."]),
          P("3.1 Why a light theme", h2),
          P("Most use is outdoors. A light background with dark text keeps the best legibility under glare, and most "
            "entry-level phones use LCD screens where a dark theme saves little battery. The dark theme remains an "
            "option in Settings (already shipped in the web app) but the reference design is light."),
          PageBreak()]

    # ---------------- 4 IA
    s += [P("4. Information architecture and navigation", h1),
          P("A bottom navigation bar with four destinations and a raised centre <b>Scan</b> button (the most used action "
            "in the field) replaces the web sidebar. Everything else is one level below."),
          side_by_side(phone(frame(MOCK / "m_home.png", "ia_home"), 60, "Figure 1 - Home with bottom navigation."),
                       [table([["Tab", "Contains"],
                               ["Home", "Greeting, today's weather + alerts, Full auto analysis, four tool tiles, latest result"],
                               ["Predict", "Crop, Yield, Fertiliser tools (custom or dataset sample), History, Reports"],
                               ["Scan (centre)", "Camera for leaf disease; gallery; dataset sample"],
                               ["Assistant", "Chats, voice input, ask about any result"],
                               ["Farms", "Map + list of farms, farm detail (weather, soil, results), add / edit"]],
                              [0.28, 0.72]),
                        Spacer(1, 4),
                        P("Secondary places (reached from the app bar or Home): notifications bell, farm switcher, "
                          "Settings (profile, language, theme, password, export, delete), Help.", small),
                        P("Navigation rules", h3),
                        *bullets(["Back always returns to the previous screen; tools open as full screens over the tab.",
                                  "Results open as their own screen with Close (X) at the top-left and actions at the bottom.",
                                  "The selected farm is global (app-bar switcher) and pre-fills every tool.",
                                  "Deep links: agrisense://result/{id}, agrisense://scan, agrisense://assistant?ask=..."])]),
          PageBreak()]

    # ---------------- 5 tokens
    s.append(P("5. Design tokens (light theme)", h1))
    rows = [["", "Token", "Hex", "Use", "Contrast"]]
    for name, hx, role, against in TOKENS:
        cr = f"{contrast(hx, against):.1f}:1 on {against}" + (" AA" if contrast(hx, against) >= 4.5 else " (large only)") if against else "-"
        rows.append([swatch(hx), name, hx, role, cr])
    t = table(rows, [0.08, 0.14, 0.12, 0.4, 0.26])
    s += [P("5.1 Colour", h2), t,
          P("Contrast is computed with the WCAG 2.1 formula. All text colours reach AA (4.5:1) on the surface they are "
            "used on; colour is never the only signal (chips also carry a word such as LOW / OK). The brand green "
            "#2E8B57 reaches only 4.2:1 with white text, so button fills and links use primary-strong #2B8352 "
            "(4.7:1, visually the same green); the brand green stays for icons and large text.", small)]
    s += [P("5.2 Typography", h2),
          P("Inter for Latin text; Noto Sans for every Indian script (Devanagari, Bengali, Gurmukhi, Gujarati, Odia, "
            "Tamil, Telugu, Kannada, Malayalam, Perso-Arabic for Urdu) so all 15 languages share one visual weight."),
          table([["Style", "Size / line (sp)", "Weight", "Used for"],
                 ["Display", "30 / 36", "Bold", "Result value (crop name, t/ha)"], ["Title L", "24 / 30", "Bold", "Screen greeting"],
                 ["Title", "18 / 24", "SemiBold", "App bar title, card titles"], ["Body L", "16 / 24", "Regular", "Main text, inputs"],
                 ["Body", "15 / 22", "Regular", "Chat bubbles, list rows"], ["Label", "13 / 18", "SemiBold", "Field labels, chips"],
                 ["Caption", "12 / 16", "Regular", "Hints, sources, timestamps"], ["Overline", "12 / 16, +4% tracking", "SemiBold", "Section headers (UPPERCASE in Latin only)"]],
                [0.18, 0.24, 0.16, 0.42]),
          P("5.3 Spacing, shape, elevation, motion", h2),
          table([["Token", "Value"],
                 ["Spacing scale", "4 · 8 · 12 · 16 · 20 · 24 · 32 dp (screen margin 16, card padding 16, gap between cards 12)"],
                 ["Touch target", "minimum 48 x 48 dp; primary buttons 52 dp high, full width"],
                 ["Corner radius", "cards 18 · buttons & inputs 14 · chips 999 (pill) · bottom sheet 24 (top corners)"],
                 ["Elevation", "card: 1 dp + soft 6 dp shadow at 6% · bottom sheet 8 dp · Scan button 8 dp green glow"],
                 ["Icons", "Material Symbols Outlined, 24 dp, filled when selected; 20 dp inside chips"],
                 ["Motion", "100 ms press, 200 ms screen transitions (fade + 8 dp rise), 250 ms bottom sheet; respect Reduce motion"],
                 ["Haptics", "light tick on result ready and on capture; none on scroll"]], [0.25, 0.75]),
          PageBreak()]

    # ---------------- 6 components
    s += [P("6. Components", h1),
          table([["Component", "Spec", "States"],
                 ["Primary button", "52 dp, full width, radius 14, primary-strong fill, white 16 sp bold, leading icon", "pressed (primary-dark), disabled (#9CC6AD), loading (spinner + same label)"],
                 ["Secondary button", "52 dp, mint fill, primary-dark text", "pressed mint-2"],
                 ["Bottom action bar", "white bar with top divider; 1-2 buttons; stays above keyboard", "-"],
                 ["Segmented control", "My values / Sample; 48 dp; selected segment white with shadow", "selected, focused"],
                 ["Number field", "56 dp, large 20 sp value, unit in label, range as placeholder; stepper for pH", "focused (2 dp primary ring), error (red border + message below)"],
                 ["Tool tile", "2-column grid, icon in tinted 36 dp square, question as title, tool name as caption", "pressed"],
                 ["Result header card", "label, Display value, confidence chip + model-accuracy chip", "certain / not sure"],
                 ["Status chip", "pill, 13 sp, word + colour (LOW / OK / HIGH)", "-"],
                 ["Source chip", "amber, shows dataset row / sample source", "-"],
                 ["Bottom navigation", "76 dp, 4 labelled tabs + 60 dp raised Scan button", "selected = filled icon in mint-2 pill"],
                 ["Bottom sheet", "farm detail on the map, drag handle, 24 dp top radius", "collapsed / expanded"],
                 ["Chat bubble", "user: primary fill, right; assistant: white card, left, with listen / copy / helpful", "sending, error-retry"],
                 ["Snackbar", "one line + optional action, above the bottom bar, 4 s", "info, success, error"],
                 ["Empty state", "icon in mint square, one sentence, one action", "-"],
                 ["Skeleton", "grey blocks in the shape of the content, shimmer 1.2 s", "-"]],
                [0.2, 0.5, 0.3]),
          PageBreak()]

    # ---------------- 7 screens
    s.append(P("7. Key screens", h1))
    screens = [
        ("m_language", "7.1 Onboarding - language", "First launch, after the 3-second welcome screen (green, leaf mark, progress bar), before sign-in.",
         ["15 language tiles written in their own script (3 x 5 grid, 74 dp tall).", "Selected tile: primary border, mint-2 fill, check icon.",
          "Speaker hint: tapping a tile reads the language name aloud (helps users who cannot read the script yet).",
          "Continue button fixed at the bottom; the choice is saved and can be changed in Settings."],
         "Sign-in with e-mail and password, then the 6-digit e-mail code screen (auto-submits on the 6th digit, resend after 60 s)."),
        ("m_home", "7.2 Home", "Answers \"what should I do today?\"",
         ["App bar: logo, farm switcher (name + chevron), notifications bell with dot.",
          "Greeting card: today's weather in one line and the most important alert as an amber chip.",
          "Full auto analysis banner: one tap runs sample → crop → fertiliser.",
          "Four tool tiles phrased as farmer questions; latest result row with link to History."],
         "Empty: no farm → greeting card asks to add a farm; no results → tile hint \"Run your first check\"."),
        ("m_crop_input", "7.3 Tool input - crop recommendation", "Same pattern for every tool.",
         ["Segmented control: My values / Sample (random real dataset row, new on each tap).",
          "Soil Health Card shortcut: photograph the card to fill N, P, K, pH (OCR, future).",
          "Grouped number fields with units; pH stepper with an acidic-to-alkaline scale.",
          "Climate group with \"Fill from forecast\"; primary button sticky at the bottom."],
         "Validation on submit: field turns red with the allowed range below it; values are never cleared."),
        ("m_result", "7.4 Result - crop and fertiliser", "One result screen for the whole analysis.",
         ["Header card: best crop in Display size, \"99% sure\" and model accuracy chips, alternatives.",
          "Fertiliser card: the suggested fertiliser by name with its grade and model confidence, and N / P / K tiles showing how far each is below the crop's typical level.",
          "Fixed note that doses come from the soil test and KVK.",
          "Ask about this result → Assistant with the question pre-filled. Bottom bar: Save PDF, New sample."],
         "Low confidence: header shows \"Not sure\" (amber) and suggests checking the inputs."),
        ("m_scan", "7.5 Scan a leaf (camera)", "Full-screen camera, dark chrome for the viewfinder only.",
         ["Dashed frame guide and three tips in a chip: one leaf, fills the frame, daylight.",
          "Shutter 78 dp centred; gallery and dataset-sample buttons either side; flash toggle.",
          "After capture: crop to the leaf, resize to 512 px on the phone, upload, show result screen.",
          "\"Works for 14 crops\" chip links to the list."],
         "Camera permission denied: explain why and offer Gallery instead. Unclear photo: result says \"Not sure\" with a Retake button."),
        ("m_assistant", "7.6 Assistant", "Chat that speaks the farmer's language.",
         ["App bar shows the answer language as a chip (tap to change).",
          "Large mic button (voice is the default input); photo button sends the leaf to the disease model first.",
          "Answers have Listen (text-to-speech), Copy and Helpful actions.",
          "Quick-reply chips under the last answer (send photo, nearest KVK, check weather)."],
         "Offline: message is queued with a clock icon and sent when the network returns."),
        ("m_farm", "7.7 Farms - map and detail", "Map first, details in a bottom sheet.",
         ["Search field for village / district, my-location button.",
          "Farm drawn as a boundary + pin; tap opens the bottom sheet.",
          "Sheet: name, place, area, soil, crop chip, today's weather, soil pH, last yield; Edit and Analyse.",
          "Add farm: drop a pin or use current location, then a short form."],
         "Coordinates outside India are rejected with a clear message."),
    ]
    for i, (img, title, sub, points, states) in enumerate(screens):
        fr = frame(MOCK / f"{img}.png", f"s_{img}")
        txt = [P(title, h2), P(sub, small), *bullets(points), P("<b>States:</b> " + states, body)]
        s.append(side_by_side(phone(fr, 62, f"Figure {i + 2} - {title.split(' ', 1)[1]}."), txt))
        s.append(PageBreak())

    # ---------------- 8 flows
    s += [P("8. Key user flows", h1),
          table([["Flow", "Steps", "Target"],
                 ["First use", "Language → Sign up → e-mail code → Add farm (pin or my location) → Home", "under 2 min"],
                 ["Full auto analysis", "Home → Full auto analysis → Result (crop + fertiliser) → Ask / Save PDF", "1 tap to result"],
                 ["Disease check", "Scan → capture → Result → Ask assistant (pre-filled)", "3 taps, < 10 s on 4G"],
                 ["Yield estimate", "Predict → Yield → farm pre-filled → choose crop & season → Result with range", "4 taps"],
                 ["Fertiliser from crop result", "Crop result → Recommend fertiliser → Fertiliser result", "1 tap"],
                 ["Change language", "Assistant chip or Settings → pick → screen re-labels in place, nothing is lost", "instant (cached)"]],
                [0.22, 0.58, 0.2]),
          P("9. States and feedback", h1),
          table([["State", "Design"],
                 ["Loading", "Skeleton in the shape of the result; button shows spinner and keeps its label"],
                 ["Empty", "Icon + one sentence + one action (e.g. \"Add your first farm\")"],
                 ["Error", "Snackbar with plain cause and Retry; inputs keep their values"],
                 ["Offline", "Top banner \"Offline - showing saved data\"; cached weather/soil with time stamp; queued actions marked"],
                 ["Not sure (model)", "Amber header, no disease / crop named, guidance to retake or check inputs"],
                 ["Out of range input", "Field error with the training range; result shows a caution note if allowed"],
                 ["Permission denied", "Explain the benefit, button to open settings, alternative path (gallery)"]],
                [0.25, 0.75]),
          PageBreak()]

    # ---------------- 10 a11y + l10n
    rows = [["Language", "Avg width vs English", "Worst case", "Example (longest relative)"]]
    for code, v in sorted(EXP.items(), key=lambda kv: -kv[1]["avg"]):
        rows.append([LANG_NAME.get(code, code), f"{v['avg']:.2f}x", f"{v['max']:.2f}x", f"\"{v['longest_src']}\""])
    s += [P("10. Accessibility and localisation", h1),
          *bullets(["Touch targets 48 dp minimum; primary actions at the bottom within thumb reach.",
                    "Text scales to 200% (Android font size) without clipping: cards grow, no fixed heights on text.",
                    "TalkBack / VoiceOver labels on every icon button (\"Scan a leaf\", \"Notifications, 2 new\").",
                    "Colour never the only signal; status chips carry words; charts have a text summary.",
                    "Reduce-motion setting removes transitions; haptics can be turned off.",
                    "Urdu uses right-to-left text inside the same layout; icons that imply direction are mirrored."]),
          P("10.1 Measured text expansion", h2),
          P(f"The 30 most important labels were translated by the same Azure Translator the app uses and their "
            f"rendered width measured with Nirmala UI at the same size. Labels can become several times wider than English, "
            f"so <b>no button, tab or chip may have a fixed width</b>; labels wrap to two lines before truncating, and tab "
            f"labels use the short form.", body),
          table(rows, [0.2, 0.22, 0.18, 0.4]),
          PageBreak(),
          P("11. Performance, data and offline", h1),
          table([["Topic", "Rule"],
                 ["App size", "< 15 MB install; fonts subset to the icons used; no bundled ML models (server inference)"],
                 ["Data per check", "crop / yield / fertiliser < 5 KB; leaf photo resized to 512 px JPEG (~60 KB) before upload"],
                 ["Caching", "last weather and soil per farm, last 50 results, all translations; time-stamped"],
                 ["Offline", "history, farms and cached data readable; new checks queued; assistant messages queued"],
                 ["Start-up", "cold start < 2 s on a 2 GB RAM phone; Home renders from cache first, then refreshes"],
                 ["Notifications", "weather alerts for the selected farm (heavy rain, heat) and \"result ready\"; quiet hours 21:00-06:00"]],
                [0.22, 0.78]),
          P("12. Current web app at phone width (baseline)", h1),
          P("The screens below are the existing responsive web app captured at 375 x 812 in the light theme. They work, "
            "and they define the content; the mobile design above reorganises them. Observed gaps the app fixes:"),
          table([["Observed on the web at 375 px", "Mobile design response"],
                 ["Top bar crowded: title truncated to \"Ov...\", language, theme, bell and avatar compete", "App bar holds only farm switcher and bell; language and theme move to Settings / Assistant chip"],
                 ["Navigation hidden in a drawer", "Bottom navigation with labelled tabs and a centre Scan button"],
                 ["Forms are long single columns with small hints", "Grouped fields, 56 dp inputs, sticky primary button"],
                 ["Tables (history) scroll sideways", "History as a list of cards with type chip and one-line summary"],
                 ["Disease uses a file picker", "Camera-first Scan screen with framing guide"],
                 ["Charts are small on phones", "One chart per card, full width, with a one-line text summary"]],
                [0.5, 0.5]),
          PageBreak()]
    cur = sorted(CUR.glob("*.png"))
    cells, rowsimg = [], []
    for i, pth in enumerate(cur):
        fr = frame(pth, f"cur_{pth.stem}", crop_h=812)
        cells.append(phone(fr, 40, pth.stem.split("_", 1)[1].replace("_", " ").capitalize()))
        if len(cells) == 4 or i == len(cur) - 1:
            while len(cells) < 4:
                cells.append("")
            rowsimg.append(cells)
            cells = []
    for k in range(0, len(rowsimg), 2):
        t = Table(rowsimg[k:k + 2], colWidths=[W / 4] * 4)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        s += [t, PageBreak()]

    # ---------------- 13 handoff + 14 testing
    s += [P("13. Developer hand-off", h1),
          P("Tokens are exported as JSON (excerpt) so Flutter / Compose / CSS read the same values:"),
          P('<font face="Courier" size="8">{ "color": { "primary": "#2E8B57", "primaryDark": "#236B44", "ink": "#24352B", '
            '"muted": "#5F6E66", "background": "#F7FAF8", "surface": "#FFFFFF", "mint": "#F1F8F2", "mint2": "#E2F2E8", '
            '"line": "#E5ECE6" }, "radius": { "card": 18, "control": 14, "sheet": 24 }, "space": [4, 8, 12, 16, 20, 24, 32], '
            '"type": { "display": [30, 36, 700], "title": [18, 24, 600], "body": [16, 24, 400], "caption": [12, 16, 400] } }</font>'),
          *bullets(["Icons: Material Symbols Outlined, exported as a subset font containing only used glyphs.",
                    "Screens map 1:1 to the existing REST API (/api/crop/recommend, /api/yield/predict, /api/fertiliser, "
                    "/api/disease, /api/chat, /api/samples/*, /api/i18n/translate); no new back-end work is needed for v1.",
                    "Strings are English keys; translation through /api/i18n/translate with on-device cache.",
                    "Acceptance: every screen passes the checklist below on a 360 dp phone at 100% and 200% font size, in "
                    "English, Malayalam (widest) and Urdu (RTL)."]),
          table([["Acceptance checklist", "Pass rule"],
                 ["Targets", "all interactive elements >= 48 dp"], ["Contrast", "text >= 4.5:1, large text / icons >= 3:1"],
                 ["Truncation", "no clipped label in Malayalam at 200% font"], ["State keeping", "rotate, theme or language change keeps inputs and results"],
                 ["Offline", "Home, Farms, History open without network"], ["No dose", "no quantity appears in any fertiliser or disease text"]],
                [0.3, 0.7]),
          P("14. Usability testing plan", h1),
          table([["Item", "Plan"],
                 ["Participants", "8 farmers (4 Hindi, 2 Punjabi, 2 Tamil speakers), 2 KVK staff"],
                 ["Tasks", "1) choose language and sign in, 2) run Full auto analysis, 3) scan a leaf, 4) ask the assistant "
                           "about the result in own language, 5) add a farm on the map"],
                 ["Measures", "task success, time on task, errors, SUS questionnaire (target >= 75), think-aloud notes"],
                 ["Conditions", "outdoors at midday, one hand, 3G throttling"],
                 ["Exit criteria", "all tasks >= 80% success without help; no task > 2x the target time"]],
                [0.22, 0.78])]

    def page(c, d):
        c.saveState(); c.setFont("UI", 7.5); c.setFillColor(colors.HexColor(R.MUTED))
        c.drawString(18 * mm, 10 * mm, "AgriSense AI - Mobile App UI Design (light theme)")
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")
        c.restoreState()
    out = ROOT / "Project" / "08_Mobile_App_UI_Design.pdf"
    SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                      title="AgriSense AI - Mobile App UI Design", author=AUTHOR).build(s, onFirstPage=page, onLaterPages=page)
    print("wrote", out.name, f"{out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    build()
