package com.example.agrisense.ui.predict

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CloudDownload
import androidx.compose.material.icons.filled.Science
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.agrisense.data.Api
import com.example.agrisense.data.ApiException
import com.example.agrisense.data.arr
import com.example.agrisense.data.bool
import com.example.agrisense.data.fmt
import com.example.agrisense.data.int
import com.example.agrisense.data.jsonOf
import com.example.agrisense.data.num
import com.example.agrisense.data.obj
import com.example.agrisense.data.pct
import com.example.agrisense.data.s
import com.example.agrisense.data.str
import com.example.agrisense.data.title
import com.example.agrisense.i18n.tr
import com.example.agrisense.ui.AppState
import com.example.agrisense.ui.components.AppBar
import com.example.agrisense.ui.components.AppCard
import com.example.agrisense.ui.components.BarRow
import com.example.agrisense.ui.components.Chip
import com.example.agrisense.ui.components.ErrorState
import com.example.agrisense.ui.components.Field
import com.example.agrisense.ui.components.Loading
import com.example.agrisense.ui.components.ModeSwitch
import com.example.agrisense.ui.components.Note
import com.example.agrisense.ui.components.PrimaryButton
import com.example.agrisense.ui.components.SecondaryButton
import com.example.agrisense.ui.components.SectionLabel
import com.example.agrisense.ui.components.Select
import com.example.agrisense.ui.theme.agri
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject

/** Farm picker filled from the user's farms in the database. */
@Composable
fun FarmPicker(value: String, onChange: (String) -> Unit) =
    Select("Farm (optional)", value, listOf("" to tr("— Not linked —")) + AppState.farms.map { it.obj().s("id") to it.obj().s("name") }, onChange)

/** Dataset sample → crop model → fertiliser for that crop; result opens on the Fertiliser screen (as on the dashboard). */
suspend fun runChain(farmId: String, open: (String) -> Unit) {
    try {
        val s = Api.get("/api/samples/crop")
        val v = s["values"].obj()
        val crop = Api.post("/api/crop/recommend", JsonObject(v + ("farm_id" to kotlinx.serialization.json.JsonPrimitive(farmId))))
        val inp = jsonOf("basis" to "crop_profile", "crop" to crop.s("crop"), "N" to v["N"], "P" to v["P"], "K" to v["K"], "ph" to v["ph"], "farm_id" to farmId)
        val fert = Api.post("/api/fertiliser", inp)
        AppState.chain = jsonOf("sample" to s, "crop" to crop, "fert" to fert, "inp" to inp)
        AppState.toast = tr("Crop and fertiliser results saved to history")
        open("fertiliser")
    } catch (e: ApiException) { AppState.toast = e.message }
}

@Composable
private fun ToolScaffold(title: String, back: () -> Unit, content: @Composable () -> Unit) {
    Scaffold(topBar = { AppBar(title, back) }, containerColor = agri.background) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) { content(); Spacer(Modifier.height(32.dp)) }
    }
}

// ============================================================ crop
@Composable
fun CropScreen(startAuto: Boolean, back: () -> Unit, open: (String) -> Unit) {
    val a = agri
    val scope = rememberCoroutineScope()
    val info by produceState<Result<JsonObject>?>(null) { value = runCatching { AppState.cropInfo() } }
    val v = remember { mutableStateMapOf<String, String>() }
    var farm by rememberSaveable { mutableStateOf("") }
    var auto by rememberSaveable { mutableStateOf(startAuto) }
    var sample by remember { mutableStateOf<JsonObject?>(null) }
    var result by remember { mutableStateOf<JsonObject?>(null) }
    var fields by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var busy by remember { mutableStateOf(false) }
    val feats = listOf("N" to "Nitrogen (N)", "P" to "Phosphorus (P)", "K" to "Potassium (K)", "temperature" to "Temperature (°C)",
        "humidity" to "Humidity (%)", "ph" to "Soil pH", "rainfall" to "Rainfall (mm)")

    fun predict() {
        busy = true; fields = emptyMap()
        scope.launch {
            try { result = Api.post("/api/crop/recommend", jsonOf(*feats.map { it.first to v[it.first].orEmpty() }.toTypedArray(), "farm_id" to farm)); AppState.toast = tr("Recommendation saved to history") }
            catch (e: ApiException) { fields = e.fields; AppState.toast = e.message }
            busy = false
        }
    }
    fun takeSample() {
        busy = true
        scope.launch {
            try { val s = Api.get("/api/samples/crop"); sample = s; s["values"].obj().forEach { (k, x) -> v[k] = x.str() }; busy = false; predict() }
            catch (e: ApiException) { AppState.toast = e.message; busy = false }
        }
    }
    LaunchedEffect(Unit) { if (startAuto) takeSample() }

    ToolScaffold("Crop recommendation", back) {
        when (val r = info) {
            null -> Loading()
            else -> r.fold(onFailure = { ErrorState(it.message ?: "Could not load") {} }, onSuccess = { ci ->
                val ranges = ci["feature_ranges"].obj()
                ModeSwitch(auto) { auto = it; if (it) takeSample() else { sample = null; result = null; v.clear() } }
                sample?.let { Note("${tr("Dataset row")} ${it.s("row")} / ${it.s("of")} · ${tr("grown there")}: ${title(it.s("label"))}", translate = false) }
                if (auto) SecondaryButton("New sample", icon = Icons.Filled.Shuffle, loading = busy) { takeSample() }
                SectionLabel("Soil and climate")
                feats.chunked(2).forEach { row ->
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        row.forEach { (k, label) ->
                            val rg = ranges[k].obj()
                            Field(label, v[k].orEmpty(), { v[k] = it }, Modifier.weight(1f), keyboard = KeyboardType.Decimal,
                                placeholder = "${fmt(rg["min"].num(), 0)} – ${fmt(rg["max"].num(), 0)}", error = fields[k])
                        }
                        if (row.size == 1) Spacer(Modifier.weight(1f))
                    }
                }
                FarmPicker(farm) { farm = it }
                SecondaryButton("Fill temperature and humidity from forecast", icon = Icons.Filled.CloudDownload) {
                    scope.launch {
                        try {
                            val w = Api.get("/api/weather" + if (farm.isNotBlank()) "?farm_id=$farm" else "")
                            val days = w["days"].arr().map { it.obj() }
                            v["temperature"] = fmt(days.map { ((it["tmax"].num() ?: 0.0) + (it["tmin"].num() ?: 0.0)) / 2 }.average())
                            v["humidity"] = w["current"].obj().s("humidity")
                            AppState.toast = tr("Filled from the 7-day forecast. Rainfall is seasonal - enter it yourself.")
                        } catch (e: ApiException) { AppState.toast = e.message }
                    }
                }
                PrimaryButton("Find suitable crop", icon = Icons.Filled.AutoAwesome, loading = busy) { predict() }
                result?.let { CropResult(it, sample, v, farm, open) }
            })
        }
    }
}

@Composable
private fun CropResult(r: JsonObject, sample: JsonObject?, v: Map<String, String>, farm: String, open: (String) -> Unit) {
    val a = agri
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    if (sample != null) {
        val agree = sample.s("label") == r.s("crop")
        Note(if (agree) "${tr("The dataset recorded")} ${title(sample.s("label"))}. ${tr("The model agrees.")}"
             else "${tr("The dataset recorded")} ${title(sample.s("label"))}; ${tr("the model recommends")} ${title(r.s("crop"))}.", warn = !agree, translate = false)
    }
    AppCard {
        Text(tr("Best crop for this soil"), color = a.muted, style = MaterialTheme.typography.labelLarge)
        Text(tr(title(r.s("crop"))), style = MaterialTheme.typography.headlineMedium, color = a.primaryDark)
        Spacer(Modifier.height(6.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Chip("${pct(r["confidence"].num())} ${tr("sure")}", a.primaryDark, a.mint2, Icons.Filled.Verified, translate = false)
            Chip("${r.s("model")} · ${pct(r["model_accuracy"].num())} ${tr("test accuracy")}", a.ink, a.mint, translate = false)
        }
        r["outside_training_range"].arr().takeIf { it.isNotEmpty() }?.let {
            Spacer(Modifier.height(8.dp)); Note("${it.joinToString { x -> x.str() }}: ${tr("outside the training range, treat with caution.")}", warn = true, translate = false)
        }
        SectionLabel("Top crops")
        r["top"].arr().forEach { t -> val o = t.obj(); BarRow(tr(title(o.s("crop"))), o["probability"].num() ?: 0.0, 1.0, pct(o["probability"].num()), a.primary) }
    }
    AppCard(color = a.mint) {
        Text("${tr("Next: which fertiliser does")} ${tr(title(r.s("crop")))} ${tr("need here?")}", style = MaterialTheme.typography.titleSmall)
        Spacer(Modifier.height(8.dp))
        PrimaryButton("Recommend fertiliser", icon = Icons.Filled.Science, loading = busy) {
            busy = true
            scope.launch {
                try {
                    val inp = jsonOf("basis" to "crop_profile", "crop" to r.s("crop"), "N" to v["N"], "P" to v["P"], "K" to v["K"], "ph" to v["ph"], "farm_id" to farm)
                    val fert = Api.post("/api/fertiliser", inp)
                    AppState.chain = jsonOf("sample" to sample, "crop" to r, "fert" to fert, "inp" to inp)
                    open("fertiliser")
                } catch (e: ApiException) { AppState.toast = e.message }
                busy = false
            }
        }
    }
}

// ============================================================ yield
@Composable
fun YieldScreen(startAuto: Boolean, back: () -> Unit, open: (String) -> Unit) {
    val a = agri
    val scope = rememberCoroutineScope()
    val opts by produceState<Result<JsonObject>?>(null) { value = runCatching { AppState.yieldOptions() } }
    var state by rememberSaveable { mutableStateOf(AppState.user?.s("state") ?: "") }
    var district by rememberSaveable { mutableStateOf("") }
    var crop by rememberSaveable { mutableStateOf("") }
    var season by rememberSaveable { mutableStateOf("") }
    var year by rememberSaveable { mutableStateOf(java.util.Calendar.getInstance().get(java.util.Calendar.YEAR).toString()) }
    var area by rememberSaveable { mutableStateOf("") }
    var farm by rememberSaveable { mutableStateOf("") }
    var auto by rememberSaveable { mutableStateOf(startAuto) }
    var sample by remember { mutableStateOf<JsonObject?>(null) }
    var result by remember { mutableStateOf<JsonObject?>(null) }
    var fields by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var busy by remember { mutableStateOf(false) }
    val districts by produceState<List<String>>(emptyList(), state) {
        value = if (state.isBlank()) emptyList() else runCatching { Api.get("/api/yield/districts?state=${Api.q(state)}")["districts"].arr().map { it.str() } }.getOrDefault(emptyList())
    }
    fun predict() {
        busy = true; fields = emptyMap()
        scope.launch {
            try { result = Api.post("/api/yield/predict", jsonOf("state" to state, "district" to district, "crop" to crop, "season" to season, "year" to year, "area_ha" to area, "farm_id" to farm)); AppState.toast = tr("Prediction saved to history") }
            catch (e: ApiException) { fields = e.fields; AppState.toast = e.message }
            busy = false
        }
    }
    fun takeSample() {
        busy = true
        scope.launch {
            try {
                val s = Api.get("/api/samples/yield"); sample = s
                state = s.s("state"); district = s.s("district"); crop = s.s("crop"); season = s.s("season"); year = s.s("year"); area = s.s("area_ha")
                busy = false; predict()
            } catch (e: ApiException) { AppState.toast = e.message; busy = false }
        }
    }
    LaunchedEffect(Unit) { if (startAuto) takeSample() }

    ToolScaffold("Yield prediction", back) {
        when (val r = opts) {
            null -> Loading()
            else -> r.fold(onFailure = { ErrorState(it.message ?: "Could not load") {} }, onSuccess = { o ->
                ModeSwitch(auto) { auto = it; if (it) takeSample() else { sample = null; result = null } }
                sample?.let { Note("${title(it.s("district").lowercase())}, ${it.s("state")} · ${it.s("crop")} · ${it.s("season")} ${it.s("year")}. ${tr(it.s("area_note"))}", translate = false) }
                if (auto) SecondaryButton("New sample", icon = Icons.Filled.Shuffle, loading = busy) { takeSample() }
                Select("State", state, o["State"].arr().map { it.str() to it.str() }, { state = it; district = "" }, error = fields["state"])
                Select("District", district, districts.map { it to it }, { district = it }, error = fields["district"])
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Select("Crop", crop, o["Crop"].arr().map { it.str() to it.str() }, { crop = it }, Modifier.weight(1f), error = fields["crop"])
                    Select("Season", season, o["Season"].arr().map { it.str() to it.str() }, { season = it }, Modifier.weight(1f), error = fields["season"], translateLabels = true)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Field("Year", year, { year = it }, Modifier.weight(1f), keyboard = KeyboardType.Number, error = fields["year"])
                    Field("Area (ha)", area, { area = it }, Modifier.weight(1f), keyboard = KeyboardType.Decimal, error = fields["area_ha"])
                }
                FarmPicker(farm) { id ->
                    farm = id
                    AppState.farms.map { it.obj() }.firstOrNull { it.s("id") == id }?.let { f ->
                        if (f.s("area_ha").isNotBlank()) area = f.s("area_ha")
                        if (o["State"].arr().any { it.str() == f.s("state") }) { state = f.s("state"); district = f.s("district").uppercase() }
                    }
                }
                Note("The model works at district level from past yields; it has no weather or soil inputs. Your area only scales production.")
                PrimaryButton("Predict yield", icon = Icons.Filled.TrendingUp, loading = busy) { predict() }
                result?.let { YieldResult(it, sample, crop, season, year, district, state, area, open) }
            })
        }
    }
}

@Composable
private fun YieldResult(r: JsonObject, sample: JsonObject?, crop: String, season: String, year: String, district: String, state: String, area: String, open: (String) -> Unit) {
    val a = agri
    val iv = r["interval_80"].arr()
    if (sample != null && sample.s("year") == year && sample.s("crop") == crop && sample.s("district") == district) {
        Note("${tr("The dataset recorded")} ${fmt(sample["recorded_yield_t_ha"].num(), 2)} t/ha ${tr("for this district, crop, season and year. The deployed model was refit on all years, so this record was part of its training data.")}", translate = false)
    }
    AppCard {
        Text(tr("Expected yield"), color = a.muted, style = MaterialTheme.typography.labelLarge)
        Text("${fmt(r["yield_t_ha"].num(), 2)} t/ha", style = MaterialTheme.typography.headlineMedium, color = a.primaryDark)
        Text("${tr("80% range")} ${fmt(iv.getOrNull(0).num(), 2)} – ${fmt(iv.getOrNull(1).num(), 2)} t/ha", color = a.muted, style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(6.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Chip("${tr("Production")}: ${fmt(r["production_t"].num(), 1)} t", a.ink, a.mint, translate = false)
            if (r.s("category").isNotBlank()) Chip(r.s("category"), a.primaryDark, a.mint2)
        }
        Spacer(Modifier.height(6.dp))
        Text("${tr("District average")}: ${fmt(r["district_mean_t_ha"].num(), 2)} t/ha · ${r.s("years_of_history")} ${tr("years of history")}", style = MaterialTheme.typography.bodySmall, color = a.muted)
    }
    if ((r["years_of_history"].int() ?: 0) < 3) Note("Only a few past years exist for this district, crop and season, so the estimate is less reliable.", warn = true)
    AppCard {
        Text(tr("District yield history"), style = MaterialTheme.typography.titleSmall)
        val hist = r["district_history"].arr().map { it.obj() }.takeLast(10)
        val mx = (hist.mapNotNull { it["yield"].num() } + listOfNotNull(r["yield_t_ha"].num())).maxOrNull() ?: 1.0
        hist.forEach { h -> BarRow(h.s("year"), h["yield"].num() ?: 0.0, mx, "${fmt(h["yield"].num(), 2)} t/ha", a.primary.copy(alpha = .55f)) }
        BarRow("${year} (${tr("prediction")})", r["yield_t_ha"].num() ?: 0.0, mx, "${fmt(r["yield_t_ha"].num(), 2)} t/ha", a.primaryStrong)
    }
    AppCard {
        Text(tr("Why this number"), style = MaterialTheme.typography.titleSmall)
        Text(tr("How much each factor pushed the estimate (green raises, red lowers)."), style = MaterialTheme.typography.bodySmall, color = a.muted)
        val cs = r["contributions"].arr().map { it.obj() }.take(6)
        val mx = cs.maxOfOrNull { kotlin.math.abs(it["contribution"].num() ?: 0.0) } ?: 1.0
        cs.forEach { c ->
            val x = c["contribution"].num() ?: 0.0
            BarRow(tr(c.s("feature").replace("_", " ")), kotlin.math.abs(x), mx, fmt(x, 3), if (x >= 0) a.primary else a.danger)
        }
    }
}

// ============================================================ fertiliser
@Composable
fun FertiliserScreen(startAuto: Boolean, back: () -> Unit, open: (String) -> Unit) {
    val a = agri
    val scope = rememberCoroutineScope()
    val info by produceState<Result<JsonObject>?>(null) { value = runCatching { AppState.cropInfo() } }
    val chain = remember { AppState.chain.also { AppState.chain = null } }
    val inpStart = chain?.get("inp").obj()
    var basis by rememberSaveable { mutableStateOf(inpStart.s("basis").ifBlank { "soil_test" }) }
    var crop by rememberSaveable { mutableStateOf(inpStart.s("crop")) }
    var n by rememberSaveable { mutableStateOf(inpStart.s("N")) }
    var p by rememberSaveable { mutableStateOf(inpStart.s("P")) }
    var k by rememberSaveable { mutableStateOf(inpStart.s("K")) }
    var ph by rememberSaveable { mutableStateOf(inpStart.s("ph")) }
    var oc by rememberSaveable { mutableStateOf("") }
    var farm by rememberSaveable { mutableStateOf(inpStart.s("farm_id")) }
    var auto by rememberSaveable { mutableStateOf(startAuto) }
    var result by remember { mutableStateOf(chain?.get("fert")?.obj()) }
    var fields by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var busy by remember { mutableStateOf(false) }
    var chainBusy by remember { mutableStateOf(false) }
    var sample by remember { mutableStateOf<JsonObject?>(null) }
    fun run() {
        busy = true; fields = emptyMap()
        scope.launch {
            try { result = Api.post("/api/fertiliser", jsonOf("basis" to basis, "crop" to crop, "N" to n, "P" to p, "K" to k, "ph" to ph, "organic_carbon" to oc, "farm_id" to farm)); AppState.toast = tr("Saved to history") }
            catch (e: ApiException) { fields = e.fields; AppState.toast = e.message }
            busy = false
        }
    }
    fun takeSample() {
        busy = true
        scope.launch {
            try {
                // a real row of the fertiliser dataset, entered on its own scale
                val s = Api.get("/api/samples/fertiliser"); val v = s["values"].obj()
                sample = s
                basis = "fertiliser_dataset"; crop = s.s("crop_type"); n = v.s("N"); p = v.s("P"); k = v.s("K"); ph = ""; oc = ""; busy = false; run()
            } catch (e: ApiException) { AppState.toast = e.message; busy = false }
        }
    }
    LaunchedEffect(Unit) { if (startAuto && chain == null) takeSample() }

    ToolScaffold("Fertiliser recommendation", back) {
        when (val r = info) {
            null -> Loading()
            else -> r.fold(onFailure = { ErrorState(it.message ?: "Could not load") {} }, onSuccess = { ci ->
                chain?.let { ChainCard(it, open) }
                ModeSwitch(auto) { auto = it; if (it) takeSample() else { result = null; sample = null } }
                AppCard(onClick = { if (!chainBusy) { chainBusy = true; scope.launch { runChain(farm, open); chainBusy = false } } }, color = a.mint2) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(listOf("Soil sample from the dataset", "Crop model", "Fertiliser").joinToString(" → ") { tr(it) }, style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                        Spacer(Modifier.width(8.dp))
                        if (chainBusy) androidx.compose.material3.CircularProgressIndicator(Modifier.padding(4.dp), strokeWidth = 2.dp)
                        else androidx.compose.material3.Icon(Icons.Filled.AutoAwesome, null, tint = a.primary)
                    }
                }
                val meta by produceState<JsonObject?>(null) { value = runCatching { AppState.meta() }.getOrNull() }
                val bases = meta?.get("fertiliser_bases").arr().map { it.obj().s("value") to it.obj().s("label") }
                Select("What are your N, P, K numbers?", basis, bases, { basis = it; sample = null }, translateLabels = true)
                Note(when (basis) {
                    "soil_test" -> "Each nutrient is compared with the middle of the Soil Health Card medium band; the shortfall goes to the fertiliser model."
                    "crop_profile" -> "Each nutrient is compared with the chosen crop's typical level in the crop dataset; the shortfall goes to the fertiliser model."
                    else -> "The numbers you need to supply, on the fertiliser dataset's scale (N and P 0-42, K 0-19). They go to the model as they are."
                })
                // the fertiliser dataset has its own crop types; the other bases use the 22 crops of the crop model
                val cropOptions = if (basis == "fertiliser_dataset") meta?.get("fertiliser_crop_types").arr().map { it.str() to it.str() }
                                  else ci["classes"].arr().map { it.str() to title(it.str()) }
                Select(if (basis == "fertiliser_dataset") "Crop (optional)" else "Crop", crop, cropOptions, { crop = it }, error = fields["crop"], translateLabels = true)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Field("N", n, { n = it }, Modifier.weight(1f), keyboard = KeyboardType.Decimal, error = fields["N"])
                    Field("P", p, { p = it }, Modifier.weight(1f), keyboard = KeyboardType.Decimal, error = fields["P"])
                    Field("K", k, { k = it }, Modifier.weight(1f), keyboard = KeyboardType.Decimal, error = fields["K"])
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Field("Soil pH (optional)", ph, { ph = it }, Modifier.weight(1f), keyboard = KeyboardType.Decimal, error = fields["ph"])
                    Field("Organic carbon % (optional)", oc, { oc = it }, Modifier.weight(1f), keyboard = KeyboardType.Decimal, error = fields["organic_carbon"])
                }
                FarmPicker(farm) { farm = it }
                PrimaryButton("Get recommendation", icon = Icons.Filled.Science, loading = busy) { run() }
                result?.let { FertResult(it, mapOf("N" to n, "P" to p, "K" to k), crop, open, sample) }
            })
        }
    }
}

@Composable
private fun ChainCard(c: JsonObject, open: (String) -> Unit) {
    val a = agri
    val s = c["sample"] as? JsonObject
    val cr = c["crop"].obj(); val fe = c["fert"].obj(); val inp = c["inp"].obj()
    AppCard(color = a.mint, border = a.primary.copy(alpha = .3f)) {
        Text("${tr("Crop")} → ${tr("Fertiliser")}", style = MaterialTheme.typography.titleMedium)
        Text(tr(if (s != null) "From a random soil sample in the dataset; both results are saved to your history." else "From your crop recommendation."),
            style = MaterialTheme.typography.bodySmall, color = a.muted)
        Spacer(Modifier.height(8.dp))
        Text("1 · ${tr(if (s != null) "Soil sample" else "Your soil values")}${if (s != null) " · ${tr("row")} ${s.s("row")}" else ""}", style = MaterialTheme.typography.labelLarge)
        Text("N ${inp.s("N")} · P ${inp.s("P")} · K ${inp.s("K")} · pH ${inp.s("ph")}" + if (s != null) " · ${tr("recorded crop")}: ${title(s.s("label"))}" else "", style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(6.dp))
        Text("2 · ${tr("Crop model")}: ${tr(title(cr.s("crop")))} (${pct(cr["confidence"].num())})", style = MaterialTheme.typography.labelLarge)
        Spacer(Modifier.height(6.dp))
        val fz = fe["fertiliser"].obj()
        Text("3 · ${tr("Fertiliser")}", style = MaterialTheme.typography.labelLarge)
        if (fz.s("name").isNotBlank()) {
            Text(fz.s("name"), style = MaterialTheme.typography.headlineSmall, color = a.primaryDark)
            Text("${fz.s("grade")} · ${pct(fz["confidence"].num())} ${tr("model confidence")}", style = MaterialTheme.typography.bodySmall, color = a.muted)
        } else Text(tr(fe.s("category")), style = MaterialTheme.typography.titleMedium, color = a.primaryDark)
        StatusChips(fe["status"].obj())
        Spacer(Modifier.height(8.dp))
        SecondaryButton("Open crop result") { open("prediction/${cr.s("id")}") }
    }
}

/** The question the assistant button sends: carries the model's suggestion so the chat can explain it. */
private fun fertQuestion(r: JsonObject, inp: Map<String, String>, crop: String, lead: String = ""): String {
    val fz = r["fertiliser"].obj(); val st = r["status"].obj()
    val nut = listOf("N", "P", "K").joinToString(", ") { "$it ${inp[it]} (${st.s(it)})" }
    val head = "$lead My fertiliser result #${r.s("id")}${if (crop.isNotBlank()) " for ${title(crop)}" else ""}: $nut. ".trim()
    return if (fz.s("name").isNotBlank())
        "$head The model suggests ${fz.s("name")} (${fz.s("grade")}, ${fz.s("supplies")}) with ${pct(fz["confidence"].num())} confidence. " +
            "Explain why this fertiliser fits, how it is usually applied, and what I should confirm with my KVK."
    else "$head No fertiliser was suggested because nothing is short. How should I maintain soil fertility?"
}

@Composable
private fun StatusChips(st: JsonObject) {
    val a = agri
    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 6.dp)) {
        listOf("N", "P", "K").forEach { n ->
            val s = st.s(n)
            val (fg, bg) = when (s) { "short", "low", "needed" -> a.danger to a.danger.copy(alpha = .12f); "above", "high" -> a.warn to a.warnBg; else -> a.primaryDark to a.mint2 }
            Chip("$n ${tr(s)}", fg, bg, translate = false)
        }
    }
}

@Composable
private fun FertResult(r: JsonObject, inp: Map<String, String>, crop: String, open: (String) -> Unit, sample: JsonObject? = null) {
    val a = agri
    val fz = r["fertiliser"].obj()
    val name = fz.s("name")
    AppCard {
        Chip(r.s("engine"), a.primaryDark, a.mint2, translate = false)
        if (sample != null) {
            Spacer(Modifier.height(8.dp))
            Note(if (sample.s("label") == name) "${tr("The dataset records")} ${sample.s("label")} - ${tr("the model got it right.")}"
                 else "${tr("The dataset records")} ${sample.s("label")}; ${tr("the model suggests")} ${name.ifBlank { "-" }}.", translate = false)
        }
        Spacer(Modifier.height(8.dp))
        Text(tr("Suggested fertiliser"), color = a.muted, style = MaterialTheme.typography.labelLarge)
        if (name.isNotBlank()) {
            Text(name, style = MaterialTheme.typography.headlineMedium, color = a.primaryDark)
            Text("${fz.s("grade")} (N-P-K) · ${tr(fz.s("supplies"))}", style = MaterialTheme.typography.bodySmall, color = a.muted)
            Spacer(Modifier.height(6.dp))
            val conf = fz["confidence"].num() ?: 0.0
            Chip("${pct(conf)} ${tr("model confidence")}", if (conf >= 0.5) a.primaryDark else a.warn, if (conf >= 0.5) a.mint2 else a.warnBg, translate = false)
            if (fz["filtered"].bool()) Text("${tr("Model's first choice")}: ${fz.s("model_first_choice")} (${tr("does not supply every short nutrient")})",
                style = MaterialTheme.typography.bodySmall, color = a.muted, modifier = Modifier.padding(top = 4.dp))
        } else {
            Text(tr(r.s("category")), style = MaterialTheme.typography.headlineSmall, color = a.primaryDark)
            Text(tr(r.s("summary")), style = MaterialTheme.typography.bodySmall, color = a.muted)
        }
        StatusChips(r["status"].obj())
        Spacer(Modifier.height(10.dp))
        PrimaryButton("Ask the assistant about this", icon = Icons.Filled.SmartToy) {
            AppState.pendingAsk = fertQuestion(r, inp, crop); open("assistant")
        }
    }
    val bridged = r.s("basis") != "fertiliser_dataset" && r["typical"] is JsonObject
    AppCard {
        Text(tr(if (bridged) "Nutrient shortfall" else "Nutrient need"), style = MaterialTheme.typography.titleSmall)
        Spacer(Modifier.height(6.dp))
        listOf("N" to "Nitrogen (N)", "P" to "Phosphorus (P)", "K" to "Potassium (K)").forEach { (key, label) ->
            if (bridged) {
                val sf = r["shortfall"].obj()[key].num() ?: 0.0
                val v = r["values"].obj()[key].num(); val t = r["typical"].obj()[key].num()
                BarRow("${tr(label)} · ${fmt(v, 1)} / ${tr("typical")} ${fmt(t, 1)}", sf, 1.0,
                    if (sf > 0) "${(sf * 100).toInt()}% ${tr("short")}" else tr("no shortfall"), if (sf > 0) a.danger else a.primary)
            } else {
                val nd = r["need"].obj()[key].num() ?: 0.0
                BarRow(tr(label), nd, 42.0, fmt(nd, 1), a.primary)
            }
        }
        Spacer(Modifier.height(6.dp))
        r["explanation"].arr().forEach { Text("• ${tr(it.str())}", style = MaterialTheme.typography.bodySmall) }
    }
    fz["top"].arr().takeIf { it.isNotEmpty() }?.let { top ->
        AppCard {
            Text(tr("Model's top 3"), style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(6.dp))
            top.forEach { x -> val o = x.obj(); BarRow("${o.s("name")} (${o.s("grade")})", o["probability"].num() ?: 0.0, 1.0, pct(o["probability"].num()),
                if (o.s("name") == name) a.primary else a.primary.copy(alpha = .35f)) }
        }
    }
    AppCard {
        Text(tr("How the model got its input"), style = MaterialTheme.typography.titleSmall)
        Text(tr(r.s("bridge")), style = MaterialTheme.typography.bodySmall, color = a.muted)
        r["notes"].arr().forEach { Spacer(Modifier.height(4.dp)); Text("• ${tr(it.str())}", style = MaterialTheme.typography.bodySmall) }
    }
    Note("Choosing a fertiliser is not the same as calculating the dose. Use your soil test and your KVK recommendation before applying any fertiliser.", warn = true)
}
