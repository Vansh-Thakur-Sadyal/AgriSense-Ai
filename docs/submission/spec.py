"""Single source of truth for requirement IDs, shared by the SRS, the SDD and the test workbook
(traceability). Test IDs refer to tests/test_*.py docstrings (TC-001 ... TC-088)."""

PROJECT = "AgriSense AI - Smart Farming Intelligence"
AUTHOR = "Vansh Thakur"
PROGRAMME = "B.Tech CSE (Cyber Security), NIIT University"
COURSE = "AI & Software Engineering - course project"
URL = "https://ai.software.microeagle.online"
VERSION = "1.0"

# (id, area, requirement, priority, tests)
FR = [
    ("FR-01", "Accounts", "The system shall let a new user register with name, e-mail, password and optional phone, state, district and role.", "High", ["TC-001", "TC-002", "TC-059"]),
    ("FR-02", "Accounts", "The system shall verify ownership of the e-mail with a 6-digit one-time code before the account is created.", "High", ["TC-001", "TC-002", "TC-003", "TC-059", "TC-061"]),
    ("FR-03", "Accounts", "The system shall validate sign-up input (name length, e-mail format, password of 8+ characters with letters and digits) and refuse duplicate e-mails or phones.", "High", ["TC-007", "TC-008", "TC-009"]),
    ("FR-04", "Accounts", "The system shall sign a user in only after a correct password AND a correct e-mailed code.", "High", ["TC-010", "TC-011", "TC-060"]),
    ("FR-05", "Accounts", "The system shall limit codes: 10-minute expiry, single use, 5 wrong attempts, 60 s between resends, 6 codes per address per hour.", "High", ["TC-004", "TC-005", "TC-006"]),
    ("FR-06", "Accounts", "The system shall let a user reset a forgotten password with an e-mailed code, without revealing whether an address is registered.", "Medium", ["TC-012", "TC-013", "TC-067"]),
    ("FR-07", "Accounts", "The system shall let a signed-in user edit the profile (name, district, language, units, notifications), change the password and sign out.", "Medium", ["TC-016", "TC-017", "TC-019"]),
    ("FR-08", "Accounts", "The system shall let a user delete the account and all data linked to it.", "Medium", ["TC-018"]),
    ("FR-09", "Farms", "The system shall let a user add, edit, list and delete farms with name, state, district, village, map location, area, soil type, irrigation and crop history.", "High", ["TC-020", "TC-021", "TC-023", "TC-074"]),
    ("FR-10", "Farms", "The system shall reject farm coordinates outside India.", "Low", ["TC-022"]),
    ("FR-11", "Crop", "The system shall recommend the most suitable of 22 crops from N, P, K, temperature, humidity, pH and rainfall, with confidence and the top alternatives.", "High", ["TC-024", "TC-025", "TC-062"]),
    ("FR-12", "Crop", "The system shall validate the 7 crop inputs against the ranges seen in training and show field-level errors.", "High", ["TC-026"]),
    ("FR-13", "Yield", "The system shall predict yield (t/ha) and production (t) for a district, crop, season, year and cultivated area, with an 80% interval.", "High", ["TC-027", "TC-028"]),
    ("FR-14", "Yield", "The system shall explain each yield prediction with per-feature contributions (SHAP) and show the district's yield history.", "Medium", ["TC-027"]),
    ("FR-15", "Yield", "The system shall offer only the states, districts, crops and seasons present in the training data, and validate year and area.", "Medium", ["TC-029", "TC-030"]),
    ("FR-16", "Fertiliser", "The system shall find which of N, P and K are short of the typical level (crop median or Soil Health Card band) and name a fertiliser with its grade and confidence using a model trained on Fertilizer Prediction.csv; the fertiliser must supply every short nutrient; no fertiliser is named when nothing is short; never doses.", "High", ["TC-031", "TC-032", "TC-033", "TC-086", "TC-087"]),
    ("FR-17", "Disease", "The system shall identify the crop and disease (39 classes) from an uploaded JPG/PNG leaf photo up to 8 MB.", "High", ["TC-034", "TC-035", "TC-037", "TC-063"]),
    ("FR-18", "Disease", "The system shall refuse to name a disease when calibrated confidence is below the threshold, and mark the result for review.", "High", ["TC-036"]),
    ("FR-19", "Disease", "The system shall show the cause, symptoms and next steps for a detected disease.", "Medium", ["TC-034", "TC-063"]),
    ("FR-20", "Assistant", "The system shall answer farming questions in English or Hindi, grounded in the user's own farms and predictions, accept a leaf photo, and offer a one-click question from the fertiliser and leaf-disease results, where a farmer most needs follow-up advice.", "High", ["TC-056", "TC-057", "TC-058", "TC-075", "TC-082", "TC-083"]),
    ("FR-21", "Assistant", "The system shall save, rename, bookmark and delete assistant conversations per user.", "Low", ["TC-056"]),
    ("FR-22", "Weather", "The system shall show live weather, a 7-day forecast and alerts for the farm location, and daily weather history for a chosen period.", "Medium", ["TC-053", "TC-054"]),
    ("FR-23", "Soil", "The system shall show modelled soil properties (pH, organic carbon, nitrogen, clay, sand, bulk density) at 6 depths for the farm.", "Medium", ["TC-055"]),
    ("FR-24", "History", "The system shall store every prediction with inputs, result, model version and status, and let the user filter, view and delete them.", "High", ["TC-024", "TC-039", "TC-040"]),
    ("FR-25", "Reports", "The system shall show an overview dashboard (KPIs, recent predictions, insights, production analytics) and export predictions as PDF and CSV.", "Medium", ["TC-041", "TC-042", "TC-043"]),
    ("FR-26", "Data", "The system shall record every authentication event and store every uploaded leaf photo with its prediction or chat.", "Medium", ["TC-015", "TC-038", "TC-058"]),
    ("FR-28", "Automatic input", "Each prediction tool shall offer Custom input or Auto-fill from the dataset: a different random real sample on every request (crop CSV row, district production record, leaf photo, fertiliser dataset row), with the dataset's own label or recorded value shown next to the model's answer.", "High", ["TC-070", "TC-073", "TC-088"]),
    ("FR-29", "Automatic input", "The system shall run a full analysis - dataset soil sample, crop model, fertiliser model for the recommended crop - from the Overview menu, the Fertiliser page or a crop result, open the Fertiliser page with the combined result naming the suggested fertiliser, and offer a one-tap question to the assistant about it.", "High", ["TC-071", "TC-072"]),
    ("FR-30", "UI", "The interface shall be offered in English and 14 Indian languages (Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Urdu, Kannada, Odia, Malayalam, Punjabi, Assamese, Maithili, Konkani) through Azure AI Translator with a permanent cache; user and farm names are never translated; the assistant answers in the chosen language.", "High", ["TC-077", "TC-078", "TC-080", "TC-082", "TC-083"]),
    ("FR-31", "UI", "The interface shall offer a light and a dark theme (or follow the device), remembered per device.", "Medium", ["TC-079"]),
    ("FR-27", "UI", "The interface shall be available in English and Hindi and usable on phones (375 px) without sideways scrolling.", "Medium", ["TC-065", "TC-066"]),
    ("FR-32", "Mobile app", "An Android app shall offer the dashboard's features through the same API (no separate back end): bearer-token sessions from the same e-mail-code sign-in, option lists served by the API, and a 3-second branded welcome screen on every launch.", "Medium", ["TC-084", "TC-085"]),
]

NFR = [
    ("NFR-01", "Security", "Passwords hashed with scrypt + per-user salt; session tokens and OTP codes stored only as SHA-256 hashes.", ["TC-014"]),
    ("NFR-02", "Security", "Every data endpoint requires a session; a user can never read or change another user's farms, predictions, chats or uploads.", ["TC-044", "TC-045"]),
    ("NFR-03", "Security", "Session cookie is HttpOnly, SameSite=Lax and Secure in production; all traffic over HTTPS (Let's Encrypt).", ["TC-046"]),
    ("NFR-04", "Security", "API keys and the OTP shared secret live only in a server-side file mounted read-only; never in the browser or the repository.", []),
    ("NFR-05", "Accuracy", "Crop model test accuracy >= 97%; yield model must beat last-year and 3-year-mean baselines on unseen years; leaf model test accuracy >= 98% with calibration error < 0.02; fertiliser model cross-validated accuracy >= 95%.", ["TC-048", "TC-049", "TC-050", "TC-051", "TC-052", "TC-086"]),
    ("NFR-06", "Honesty", "Every number shown comes from a trained model, a named public data source or the user's own records; no demo or fabricated data.", ["TC-048", "TC-049", "TC-050"]),
    ("NFR-07", "Performance", "A model prediction returns in under 2 s on the server CPU; cached weather/soil look-ups in under 1 s.", ["TC-047"]),
    ("NFR-08", "Availability", "Container restarts automatically; a health check (/healthz) is polled every 30 s.", ["TC-047"]),
    ("NFR-09", "Usability", "Clear field-level validation messages; result pages explain what the model used and its limits.", ["TC-007", "TC-026", "TC-029"]),
    ("NFR-10", "Portability", "Runs anywhere Docker runs; models are served on CPU (ONNX Runtime, scikit-learn, LightGBM), no GPU needed in production.", []),
    ("NFR-11", "Maintainability", "Model cards are generated by the training scripts; 88 automated tests (API, model, live, UI) run with one command.", []),
    ("NFR-12", "Privacy", "A user can export and permanently delete all of their data.", ["TC-018", "TC-042"]),
    ("NFR-15", "Usability", "Switching theme or language never reloads the page: results, charts and typed inputs stay on screen.", ["TC-081", "TC-083"]),
    ("NFR-14", "Safety", "The assistant never states fertiliser or pesticide quantities; a server-side check asks the model to rewrite any reply containing an application amount and removes what remains.", ["TC-076"]),
    ("NFR-13", "Resilience", "Fonts, icons and front-end libraries are served by the app itself, so the interface renders correctly even when Google Fonts or public CDNs are blocked.", ["TC-068", "TC-069"]),
]
