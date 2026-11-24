"""AI farming assistant over the Mistral chat API, grounded in the user's own farms and predictions."""
import json
import os
import re
import time

import httpx

SYSTEM = """You are AgriSense AI, an agricultural assistant for Indian farmers.
Rules:
- Answer only farming questions (crops, soil, weather, pests and diseases, fertiliser, irrigation, markets, this app). Politely decline anything else.
- Reply in {lang}. Use short paragraphs and simple words; explain technical terms.
- Use the CONTEXT below when it is relevant (the user's farms, recent model predictions and the models' measured accuracy). Never invent measurements, prices, government schemes, chemical doses or spray schedules.
- NEVER give any quantity of fertiliser, manure, pesticide or fungicide - no kg/ha, kg per acre, bags, g per plant, ml or g per litre, not even as an "example" or "typical" figure. You may name fertiliser types (e.g. urea, DAP, MOP) and their nutrient grades (e.g. 46% N), and explain timing in words (e.g. "split into two or three applications"). For any amount, say it must come from a soil test and the local Krishi Vigyan Kendra (KVK) or state agriculture department.
- When explaining a model prediction, describe what the model actually used. The yield model uses only location, crop, season, area and past yields: it has no weather or soil inputs.
- If you are unsure, say so.
- Reference scales used by this app (use exactly these words): soil pH <5.5 strongly acidic, 5.5-6.5 slightly acidic, 6.5-7.5 neutral, 7.5-8.5 moderately alkaline, >8.5 strongly alkaline. Soil Health Card available nutrients (kg/ha): N <280 low, 280-560 medium, >560 high; P <10 low, 10-25 medium, >25 high; K <110 low, 110-280 medium, >280 high. Organic carbon <0.5% low, 0.5-0.75% medium, >0.75% high.
CONTEXT:
{context}"""

# An application amount: a number followed by a mass/volume unit, a bag count or a per-area rate.
DOSE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:-|to|–)?\s*\d*\s*(?:kg|kgs|kilograms?|g|grams?|gm|ml|l|litres?|liters?|quintals?|q|tonnes?|bags?)\b"
                  r"(?:\s*(?:/|per)\s*(?:ha|hectare|acre|plant|tree|litre|liter|l|bigha))?", re.I)
REWRITE = ("Rewrite your previous answer without ANY fertiliser, manure or pesticide quantities (no kg, g, ml, litres, bags or "
           "per-hectare/acre/plant rates, not even as examples). Keep the same advice otherwise, and say the amounts must come from "
           "a soil test and the local KVK.")
DOSE_NOTE = ("\n\n*Note: amounts were removed from this answer on purpose. AgriSense AI does not give fertiliser or pesticide doses; "
             "get them from your soil test report and the local KVK.*")


def configured():
    return bool(os.environ.get("MISTRAL_API_KEY"))


def has_dose(text):
    """True when the text states an application amount (kg/ha, bags, ml per litre ...). Soil-test thresholds that the app
    itself uses (e.g. 'N <280 kg/ha low') are allowed because they describe soil, not something to apply."""
    for m in DOSE.finditer(text):
        before = text[max(0, m.start() - 40):m.start()].lower()
        if re.search(r"(<|>|below|above|under|over|less than|more than|soil|available|threshold|range)\s*$", before.strip()[-25:]):
            continue
        return True
    return False


def _call(c, key, models, msgs):
    last = None
    for attempt, model in enumerate(models * 2):
        r = c.post("https://api.mistral.ai/v1/chat/completions",
                   json={"model": model, "temperature": 0.3, "max_tokens": 900, "messages": msgs},
                   headers={"Authorization": f"Bearer {key}"})
        if r.status_code in (429, 500, 502, 503):
            last = r
            time.sleep(1.5 * (attempt + 1))
            continue
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"], j.get("model")
    last.raise_for_status()


def reply(messages, context, lang="en"):
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("The assistant is not configured (MISTRAL_API_KEY missing).")
    from .translate import LANGS, prompt_name
    language = prompt_name(lang) if lang in LANGS and lang != "en" else "the language the user writes in (English by default)"
    sys = SYSTEM.format(lang=language, context=json.dumps(context, ensure_ascii=False)[:6000])
    models = [os.environ.get("MISTRAL_MODEL", "ministral-14b-latest")] + \
        [m for m in os.environ.get("MISTRAL_FALLBACK_MODEL", "ministral-8b-latest").split(",") if m]
    msgs = [{"role": "system", "content": sys}] + [{"role": m["role"], "content": m["content"]} for m in messages[-12:]]
    if lang in LANGS and lang != "en":
        # Small models follow the language of the question; the chosen language must win, so say it last.
        msgs.append({"role": "system", "content": f"Write your whole answer in {language}, even though the question may be in "
                                                  f"English. Keep only product or chemical names in English, in brackets."})
    with httpx.Client(timeout=60) as c:
        text, model = _call(c, key, models, msgs)
        if has_dose(text):   # the model broke the no-dose rule: ask once for a rewrite, then label what is left
            text2, model2 = _call(c, key, models, msgs + [{"role": "assistant", "content": text}, {"role": "user", "content": REWRITE}])
            text, model = (text2, model2)
            if has_dose(text):
                text = DOSE.sub("[amount removed]", text) + DOSE_NOTE
    # Guarantee the language: if the model still answered mostly in another script, translate the answer.
    if lang in LANGS and lang != "en":
        from . import translate as tr
        if not tr.in_language(text, lang) and tr.configured():
            try:
                text = tr.translate_long(text, lang)
                model = f"{model} + Azure Translator"
            except tr.TranslateError:
                pass
    return text, model
