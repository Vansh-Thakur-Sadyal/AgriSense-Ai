"""Hand-written text for the combined project report (kept apart from the layout code in build_combined.py)."""

TITLE = "AgriSense AI: A Smart Farming Assistant"
TEAM = [("Vansh Thakur", "BT24GCS305"), ("Sachin Sheshma", "BT24GCS022"), ("Yash Pandey", "BT24GCS046")]
SECTION = "C5"
COURSE = "SOFTWARE ENGINEERING"
COURSE_CODE = "CS 301"
LTPC = "3-0-2-4"
FACULTY = "Dr. Shreyansh Sharma"
YEAR = "2026-27"

# acceptance criterion per functional requirement (what has to be observed for the requirement to count as done)
ACCEPT = {
    "FR-01": "Account exists only after a valid code; the user lands on the Overview page signed in.",
    "FR-02": "Without the correct 6-digit code no account is created; the code arrives by e-mail.",
    "FR-03": "Each invalid field shows its own message; a repeated e-mail or phone is refused (409).",
    "FR-04": "A correct password alone does not sign in; password plus the e-mailed code does.",
    "FR-05": "Expired, reused and sixth wrong codes are refused; resend is blocked for 60 s.",
    "FR-06": "The new password works after the code; an unknown e-mail gets the same reply and no mail.",
    "FR-07": "Profile edits persist; after a password change the old one fails; sign-out ends the session.",
    "FR-08": "After deletion the account, farms, predictions, chats and photos are gone.",
    "FR-09": "A farm appears in the list and on the map; edits persist; delete removes it.",
    "FR-10": "Coordinates outside 6-38 N, 68-98 E are rejected with a field error.",
    "FR-11": "One of the 22 crops is returned with its probability and the next alternatives.",
    "FR-12": "An out-of-range value returns 422 naming the field and its allowed range.",
    "FR-13": "Yield in t/ha, production in tonnes and an 80% interval are returned.",
    "FR-14": "Per-feature contributions and the district's yield history are shown.",
    "FR-15": "Only combinations present in the data are offered; a bad year or area is refused.",
    "FR-16": "Short nutrients are identified; the named fertiliser supplies them; nothing short gives no fertiliser; no dose appears.",
    "FR-17": "Crop and disease are named for a valid photo; other file types are refused.",
    "FR-18": "Below the confidence threshold the result is marked for review and no disease is named.",
    "FR-19": "Cause, symptoms and next steps are shown for the detected disease.",
    "FR-20": "The reply uses the selected language and refers to the user's own farms and results.",
    "FR-21": "Chats can be reopened, renamed, bookmarked and deleted.",
    "FR-22": "Current weather, a 7-day forecast and daily history appear for the farm.",
    "FR-23": "Six soil properties at six depths are shown and labelled as modelled values.",
    "FR-24": "Every prediction appears in History with inputs and model version; delete removes it.",
    "FR-25": "Overview counts match the stored data; PDF and CSV files download.",
    "FR-26": "Each sign-in step and each uploaded photo is stored with the user and time.",
    "FR-27": "No sideways scrolling at 375 px; the Hindi switch translates the interface.",
    "FR-28": "Each auto-fill shows a different real record with the dataset's own label beside the answer.",
    "FR-29": "The full analysis ends on the Fertiliser page with both results saved and a fertiliser named.",
    "FR-30": "Choosing a language translates the interface; names are unchanged; the assistant replies in it.",
    "FR-31": "The dark theme applies without a reload and is remembered.",
    "FR-32": "The app signs in with the e-mail code, uses a bearer token and shows the same data as the web.",
}

# guideline 5.4: requirement -> design element -> implementation
TRACE = {
    "FR-01": ("Account service, users table", "POST /api/auth/register"),
    "FR-02": ("OTP service + n8n e-mail workflow", "otp.start(), otp.verify()"),
    "FR-03": ("Account service validation", "register() field checks"),
    "FR-04": ("Account service, sessions table", "POST /api/auth/login, /otp/verify"),
    "FR-05": ("OTP service limits", "TTL, MAX_ATTEMPTS, RESEND_GAP"),
    "FR-06": ("Account service", "POST /api/auth/forgot"),
    "FR-07": ("Account service", "PUT /api/me, /api/me/password"),
    "FR-08": ("Account service, all user tables", "DELETE /api/me"),
    "FR-09": ("Farm service, farms table", "/api/farms CRUD"),
    "FR-10": ("Farm service validation", "_farm_payload() bounds"),
    "FR-11": ("ML layer: crop model", "ml.recommend_crop()"),
    "FR-12": ("ML layer: input limits", "ml.validate()"),
    "FR-13": ("ML layer: yield model", "ml.predict_yield()"),
    "FR-14": ("ML layer: SHAP contributions", "predict_yield(pred_contrib)"),
    "FR-15": ("Yield options service", "/api/yield/options"),
    "FR-16": ("Fertiliser service + model", "fertiliser.recommend(), predict()"),
    "FR-17": ("ML layer: leaf CNN (ONNX)", "ml.diagnose()"),
    "FR-18": ("ML layer: calibration", "temperature + threshold"),
    "FR-19": ("Disease information table", "disease_info.INFO"),
    "FR-20": ("Assistant service (Mistral)", "assistant.reply()"),
    "FR-21": ("Chat repository", "/api/chats"),
    "FR-22": ("External data service", "external.weather(), history()"),
    "FR-23": ("External data service", "external.soil()"),
    "FR-24": ("Prediction repository", "save_prediction(), /api/predictions"),
    "FR-25": ("Reports service", "/api/overview, /api/reports/*"),
    "FR-26": ("Audit + upload repository", "db.log_event(), db.save_upload()"),
    "FR-27": ("Web client", "i18n.js, responsive CSS"),
    "FR-28": ("Sample service", "/api/samples/*"),
    "FR-29": ("Web + app clients", "runChain()"),
    "FR-30": ("Translation service (Azure)", "/api/i18n/translate, TR"),
    "FR-31": ("Web + app clients", "setTheme(), AgriTheme"),
    "FR-32": ("Android client + bearer sessions", "Api.kt, session_token()"),
}

BOUNDARY = {"TC-004", "TC-006", "TC-022", "TC-026", "TC-029", "TC-033", "TC-066"}
NEGATIVE = {"TC-003", "TC-005", "TC-007", "TC-008", "TC-009", "TC-011", "TC-013", "TC-021", "TC-036", "TC-037",
            "TC-044", "TC-045", "TC-060", "TC-061", "TC-068", "TC-076"}

USE_CASES = [
    ("UC-01", "Register", "Farmer", "Create an account that is tied to a real e-mail address", "Not signed in",
     "Open Create account -> enter name, e-mail, password, state, district -> system validates and e-mails a code -> enter code -> account created, Overview opens",
     "Invalid field: message under that field. Wrong code: tries left shown; five wrong codes cancel the request.",
     "Account and session exist; sign-up recorded in the audit log"),
    ("UC-02", "Sign in", "Farmer", "Open the dashboard securely", "Has an account",
     "Enter e-mail or phone and password -> system checks the password and e-mails a code -> enter code -> dashboard opens",
     "Wrong password: error and no code is sent. Code not received: resend after 60 s.",
     "Session created (1, 14 or 30 days)"),
    ("UC-03", "Full auto analysis", "Farmer", "Get a crop and a fertiliser for a soil sample", "Signed in",
     "Choose Full auto analysis -> system takes a random real soil sample -> crop model picks the crop -> shortfall against that crop's typical N, P, K -> fertiliser model names a fertiliser -> Fertiliser page shows both",
     "Nothing short: 'No fertiliser needed'. Low model confidence: the result says so and suggests the assistant.",
     "Crop and fertiliser results saved to History"),
    ("UC-04", "Detect leaf disease", "Farmer", "Find out what is wrong with a leaf", "Signed in",
     "Take or choose a photo -> upload -> system runs the CNN -> crop, disease, confidence, cause, symptoms and next steps shown",
     "Unclear photo: 'needs review', no disease named. Wrong file type: error.",
     "Result and photo stored"),
    ("UC-05", "Ask the assistant", "Farmer", "Get an explanation in own language", "Signed in",
     "Type a question (or tap the button on a fertiliser or disease result) -> system adds the user's farms and recent results -> Mistral answers -> reply shown and saved",
     "Service busy: smaller fallback model. Reply contains a dose: rewritten, then amounts removed.",
     "Conversation saved"),
    ("UC-06", "Review and export", "Farmer", "Look back at earlier results", "Has predictions",
     "Open History -> filter by type -> open a result -> download PDF, or open Reports -> download CSV",
     "No results yet: empty state with a hint.", "Files downloaded; nothing changed"),
]

LIMITATIONS = [
    "The crop dataset has 100 clean rows per crop, so the 99.6% accuracy is higher than real soil tests would give.",
    "The yield model works at district level and has no weather or soil inputs; a local drought or pest attack is invisible to it.",
    "The fertiliser model learned from 99 rows. Turning soil values into a nutrient need links two datasets with different units, so it is an approximation, shown as such on every result.",
    "Leaf photos in the training data are single leaves on plain backgrounds; field photos have not been measured.",
    "Soil values are modelled maps (SoilGrids) and weather history is a gridded estimate, not station readings.",
    "One small VPS serves the app. The load test shows the limit is about 100 people using it at the same moment (Section 6.3).",
]
ASSUMPTIONS = [
    "Users have an e-mail address they can open while signing in.",
    "N, P and K come either from a soil test report (kg/ha) or on the crop dataset's scale; the form asks which.",
    "Outside services (Open-Meteo, NASA POWER, SoilGrids, Mistral, Azure Translator) are reachable; when one is not, the page says so instead of showing numbers.",
    "Advice is for planning only. Doses must come from a soil test and the local Krishi Vigyan Kendra (KVK).",
]
FUTURE = [
    "Train the yield model with weather and soil inputs once district-level data for them is available.",
    "Collect field photos from farmers (with consent) to measure and improve the leaf model outside the lab.",
    "Replace the fertiliser bridge with a dataset that records soil tests and the fertiliser actually applied.",
    "Offline mode in the Android app for areas with weak signal, and voice input in Hindi.",
    "Move from SQLite to PostgreSQL and run more workers if usage grows past the measured capacity.",
]
