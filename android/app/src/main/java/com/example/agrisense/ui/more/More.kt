package com.example.agrisense.ui.more

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
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
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.TableChart
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.example.agrisense.data.Api
import com.example.agrisense.data.ApiException
import com.example.agrisense.data.Session
import com.example.agrisense.data.arr
import com.example.agrisense.data.bool
import com.example.agrisense.data.dateOf
import com.example.agrisense.data.fmt
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
import com.example.agrisense.ui.components.DangerButton
import com.example.agrisense.ui.components.EmptyState
import com.example.agrisense.ui.components.ErrorState
import com.example.agrisense.ui.components.Field
import com.example.agrisense.ui.components.Loading
import com.example.agrisense.ui.components.Note
import com.example.agrisense.ui.components.PrimaryButton
import com.example.agrisense.ui.components.SecondaryButton
import com.example.agrisense.ui.components.SectionLabel
import com.example.agrisense.ui.components.Select
import com.example.agrisense.ui.home.KIND_ICON
import com.example.agrisense.ui.theme.agri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject
import java.io.File
import java.time.LocalDate

@Composable
private fun Page(title: String, back: () -> Unit, content: @Composable ColumnScope.() -> Unit) {
    Scaffold(topBar = { AppBar(title, back) }, containerColor = agri.background) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) { content(); Spacer(Modifier.height(32.dp)) }
    }
}

@Composable
private fun LocatedFarmPicker(farm: String, onChange: (String) -> Unit) {
    val located = AppState.farms.map { it.obj() }.filter { it["lat"].num() != null }
    LaunchedEffect(located.size) { if (farm.isBlank() && located.isNotEmpty()) onChange(located.first().s("id")) }
    if (located.isEmpty()) Note("Add a farm with its location (Farms tab) to see data for it.", warn = true)
    else Select("Farm", farm, located.map { it.s("id") to it.s("name") }, onChange)
}

// ============================================================ weather
@Composable
fun WeatherScreen(back: () -> Unit) {
    val a = agri
    var farm by rememberSaveable { mutableStateOf("") }
    var start by rememberSaveable { mutableStateOf(LocalDate.now().minusDays(33).toString()) }
    var end by rememberSaveable { mutableStateOf(LocalDate.now().minusDays(3).toString()) }
    var histLoad by remember { mutableIntStateOf(0) }
    val fc by produceState<Result<JsonObject>?>(null, farm) { value = if (farm.isBlank()) null else runCatching { Api.get("/api/weather?farm_id=$farm") } }
    val hist by produceState<Result<JsonObject>?>(null, farm, histLoad) {
        value = if (farm.isBlank()) null else runCatching { Api.get("/api/weather/history?farm_id=$farm&start=$start&end=$end") }
    }
    Page("Weather", back) {
        LocatedFarmPicker(farm) { farm = it }
        fc?.fold(onFailure = { ErrorState(it.message ?: "Could not load") }, onSuccess = { w ->
            val c = w["current"].obj()
            AppCard(color = a.skyBg) {
                Text("${fmt(c["temp"].num())}°C", style = MaterialTheme.typography.headlineMedium)
                Text("${tr(c.s("condition"))} · ${w["location"].obj().s("label")}", color = a.muted)
                Spacer(Modifier.height(6.dp))
                Text("${tr("Humidity")} ${fmt(c["humidity"].num(), 0)}% · ${tr("Rain now")} ${fmt(c["rain_mm"].num())} mm · ${tr("Wind")} ${fmt(c["wind_kmh"].num())} km/h · ${tr("Sunrise")} ${w.s("sunrise")} / ${w.s("sunset")}",
                    style = MaterialTheme.typography.bodySmall)
            }
            w["alerts"].arr().forEach { Note(it.obj().s("text"), warn = true) }
            SectionLabel("7-day forecast")
            w["days"].arr().forEach { d ->
                val o = d.obj()
                AppCard {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) { Text(o.s("date"), style = MaterialTheme.typography.titleSmall); Text(tr(o.s("condition")), color = a.muted, style = MaterialTheme.typography.bodySmall) }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("${fmt(o["tmax"].num(), 0)}° / ${fmt(o["tmin"].num(), 0)}°", style = MaterialTheme.typography.titleSmall)
                            Text("${fmt(o["rain_mm"].num())} mm · ${fmt(o["rain_prob"].num(), 0)}%", color = a.sky, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
            Text(tr(w.s("source")), style = MaterialTheme.typography.labelSmall, color = a.muted)
        }) ?: if (farm.isNotBlank()) Loading() else Unit
        SectionLabel("Weather history (NASA POWER)")
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Field("Start date", start, { start = it }, Modifier.weight(1f), placeholder = "YYYY-MM-DD")
            Field("End date", end, { end = it }, Modifier.weight(1f), placeholder = "YYYY-MM-DD")
        }
        SecondaryButton("Load history") { histLoad++ }
        hist?.fold(onFailure = { ErrorState(it.message ?: "Could not load") }, onSuccess = { h ->
            val rows = h["rows"].arr().map { it.obj() }
            val rain = rows.sumOf { it["rain_mm"].num() ?: 0.0 }
            AppCard {
                Text("${tr("Total rainfall")}: ${fmt(rain)} mm", style = MaterialTheme.typography.titleSmall)
                Text("${tr("Average temperature")}: ${fmt(rows.mapNotNull { it["temp_mean"].num() }.average())} °C · ${tr("Average humidity")}: ${fmt(rows.mapNotNull { it["humidity"].num() }.average(), 0)}%",
                    style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(6.dp))
                val mx = rows.maxOfOrNull { it["rain_mm"].num() ?: 0.0 }?.coerceAtLeast(1.0) ?: 1.0
                rows.takeLast(14).forEach { r -> BarRow(r.s("date"), r["rain_mm"].num() ?: 0.0, mx, "${fmt(r["rain_mm"].num())} mm · ${fmt(r["temp_mean"].num())}°", a.sky) }
            }
            Text(tr(h.s("source")), style = MaterialTheme.typography.labelSmall, color = a.muted)
        })
    }
}

// ============================================================ soil
@Composable
fun SoilScreen(back: () -> Unit) {
    val a = agri
    var farm by rememberSaveable { mutableStateOf("") }
    val soil by produceState<Result<JsonObject>?>(null, farm) { value = if (farm.isBlank()) null else runCatching { Api.get("/api/soil?farm_id=$farm") } }
    Page("Soil health", back) {
        LocatedFarmPicker(farm) { farm = it }
        when (val r = soil) {
            null -> if (farm.isNotBlank()) Loading()
            else -> r.fold(onFailure = { ErrorState(it.message ?: "Could not load") }, onSuccess = { s ->
                Note(s.s("warning"), warn = true)
                if (!s["has_data"].bool()) Note("No soil data is available for this location.")
                s["properties"].obj().values.map { it.obj() }.forEach { p ->
                    val ds = p["depths"].arr().map { it.obj() }
                    val top = ds.firstOrNull()
                    AppCard {
                        Text(tr(p.s("label")), style = MaterialTheme.typography.labelLarge, color = a.muted)
                        Text("${fmt(top?.get("mean").num(), 2)} ${p.s("unit")}", style = MaterialTheme.typography.titleLarge)
                        Text("${tr("Topsoil")} ${top?.s("depth") ?: ""} · ${tr("90% range")} ${fmt(top?.get("q05").num(), 2)}–${fmt(top?.get("q95").num(), 2)}", style = MaterialTheme.typography.bodySmall, color = a.muted)
                        Spacer(Modifier.height(4.dp))
                        val mx = ds.maxOfOrNull { it["mean"].num() ?: 0.0 }?.coerceAtLeast(0.001) ?: 1.0
                        ds.forEach { d -> BarRow(d.s("depth"), d["mean"].num() ?: 0.0, mx, fmt(d["mean"].num(), 2), a.warn) }
                    }
                }
                Text(tr(s.s("source")), style = MaterialTheme.typography.labelSmall, color = a.muted)
            })
        }
    }
}

// ============================================================ history
@Composable
fun HistoryScreen(back: () -> Unit, open: (String) -> Unit) {
    val a = agri
    var kind by rememberSaveable { mutableStateOf("") }
    val meta by produceState<JsonObject?>(null) { value = runCatching { AppState.meta() }.getOrNull() }
    val list by produceState<Result<List<JsonObject>>?>(null, kind) {
        value = runCatching { Api.get("/api/predictions?limit=200" + if (kind.isNotBlank()) "&kind=$kind" else "")["predictions"].arr().map { it.obj() } }
    }
    Page("Prediction history", back) {
        Select("Type", kind, listOf("" to "All") + meta?.get("prediction_kinds").arr().map { it.str() to title(it.str()) }, { kind = it }, translateLabels = true)
        when (val r = list) {
            null -> Loading()
            else -> r.fold(onFailure = { ErrorState(it.message ?: "Could not load") }, onSuccess = { ps ->
                if (ps.isEmpty()) EmptyState(Icons.Filled.History, "No predictions yet. Run your first one to see it here.")
                ps.forEach { p ->
                    AppCard(onClick = { open("prediction/${p.s("id")}") }) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(KIND_ICON[p.s("kind")] ?: Icons.Filled.History, null, tint = a.primary)
                            Spacer(Modifier.width(10.dp))
                            Column(Modifier.weight(1f)) {
                                Text(p.s("summary"), style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                Text("#${p.s("id")} · ${tr(title(p.s("kind")))} · ${dateOf(p["created_at"].num())}${if (p.s("farm").isNotBlank()) " · ${p.s("farm")}" else ""}",
                                    style = MaterialTheme.typography.bodySmall, color = a.muted)
                            }
                            Icon(Icons.Filled.ChevronRight, null, tint = a.muted)
                        }
                    }
                }
            })
        }
    }
}

/** Download a PDF / CSV from the API and hand it to the phone's viewer / share sheet. */
suspend fun shareReport(ctx: android.content.Context, path: String, ext: String) {
    try {
        val bytes = Api.bytes(path)
        val f = File(ctx.cacheDir, "agrisense_report.$ext")
        withContext(Dispatchers.IO) { f.writeBytes(bytes) }
        val uri = FileProvider.getUriForFile(ctx, ctx.packageName + ".files", f)
        val mime = if (ext == "pdf") "application/pdf" else "text/csv"
        ctx.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType(mime).putExtra(Intent.EXTRA_STREAM, uri)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION), com.example.agrisense.i18n.Tr.t("Open or share report")))
    } catch (e: ApiException) { AppState.toast = e.message }
}

@Composable
fun PredictionDetailScreen(id: Int, back: () -> Unit, open: (String) -> Unit) {
    val a = agri
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var ask by remember { mutableStateOf(false) }
    val data by produceState<Result<JsonObject>?>(null) { value = runCatching { Api.get("/api/predictions/$id") } }
    Page("Result #$id", back) {
        when (val r = data) {
            null -> Loading()
            else -> r.fold(onFailure = { ErrorState(it.message ?: "Could not load") }, onSuccess = { p ->
                Chip(title(p.s("kind")), a.primaryDark, a.mint2, KIND_ICON[p.s("kind")])
                Text(p.s("summary"), style = MaterialTheme.typography.headlineSmall)
                Text("${dateOf(p["created_at"].num())} · ${p.s("model_version")} · ${tr(title(p.s("status")))}", color = a.muted, style = MaterialTheme.typography.bodySmall)
                p["confidence"].num()?.let { Text("${tr("Confidence")}: ${pct(it)}", style = MaterialTheme.typography.bodyMedium) }
                SectionLabel("Inputs")
                AppCard {
                    p["inputs"].obj().forEach { (k, v) ->
                        if (v.str().isNotBlank()) Row(Modifier.padding(vertical = 2.dp)) { Text(tr(k.replace("_", " ")), color = a.muted, modifier = Modifier.width(140.dp)); Text(v.str()) }
                    }
                }
                val res = p["result"].obj()
                res["top"].arr().takeIf { it.isNotEmpty() }?.let { top ->
                    SectionLabel("Top answers")
                    AppCard { top.forEach { t -> val o = t.obj(); BarRow(listOf(o.s("crop"), o.s("condition")).filter { it.isNotBlank() }.joinToString(": "), o["probability"].num() ?: 0.0, 1.0, pct(o["probability"].num()), a.primary) } }
                }
                res["explanation"].arr().takeIf { it.isNotEmpty() }?.let { ex -> AppCard { ex.forEach { Text("• ${tr(it.str())}", style = MaterialTheme.typography.bodySmall) } } }
                SecondaryButton("Download PDF", icon = Icons.Filled.PictureAsPdf) { scope.launch { shareReport(ctx, "/api/reports/pdf?pid=$id", "pdf") } }
                DangerButton("Delete") { ask = true }
            })
        }
    }
    if (ask) AlertDialog(onDismissRequest = { ask = false }, title = { Text(tr("Delete this prediction?")) },
        confirmButton = { TextButton(onClick = { scope.launch { runCatching { Api.delete("/api/predictions/$id") }; AppState.toast = tr("Deleted"); back() }; ask = false }) { Text(tr("Delete")) } },
        dismissButton = { TextButton(onClick = { ask = false }) { Text(tr("Cancel")) } })
}

// ============================================================ reports
@Composable
fun ReportsScreen(back: () -> Unit) {
    val a = agri
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var kind by rememberSaveable { mutableStateOf("") }
    var busy by remember { mutableStateOf<String?>(null) }
    val meta by produceState<JsonObject?>(null) { value = runCatching { AppState.meta() }.getOrNull() }
    val preds by produceState<List<JsonObject>?>(null) { value = runCatching { Api.get("/api/predictions?limit=1000")["predictions"].arr().map { it.obj() } }.getOrDefault(emptyList()) }
    fun export(fmtName: String) {
        busy = fmtName
        scope.launch { shareReport(ctx, "/api/reports/$fmtName" + if (kind.isNotBlank()) "?kind=$kind" else "", fmtName); busy = null }
    }
    Page("Reports & analytics", back) {
        when (val ps = preds) {
            null -> Loading()
            else -> {
                AppCard {
                    Text(tr("Your predictions"), style = MaterialTheme.typography.titleSmall)
                    val counts = ps.groupingBy { it.s("kind") }.eachCount()
                    val mx = (counts.values.maxOrNull() ?: 1).toDouble()
                    meta?.get("prediction_kinds").arr().forEach { k -> BarRow(tr(title(k.str())), (counts[k.str()] ?: 0).toDouble(), mx, (counts[k.str()] ?: 0).toString(), a.primary) }
                    Text("${tr("Total")}: ${ps.size}", style = MaterialTheme.typography.labelLarge)
                }
                val crops = ps.filter { it.s("kind") == "crop" }.groupingBy { it.s("crop") }.eachCount().entries.sortedByDescending { it.value }.take(6)
                if (crops.isNotEmpty()) AppCard {
                    Text(tr("Recommended crops"), style = MaterialTheme.typography.titleSmall)
                    crops.forEach { (c, n) -> BarRow(tr(title(c)), n.toDouble(), crops.first().value.toDouble(), n.toString(), a.primaryStrong) }
                }
            }
        }
        Select("Report type", kind, listOf("" to "All") + meta?.get("prediction_kinds").arr().map { it.str() to title(it.str()) }, { kind = it }, translateLabels = true)
        PrimaryButton("Download PDF", icon = Icons.Filled.PictureAsPdf, loading = busy == "pdf") { export("pdf") }
        SecondaryButton("Download CSV", icon = Icons.Filled.TableChart, loading = busy == "csv") { export("csv") }
        Note("Reports contain only your own predictions.")
    }
}

// ============================================================ settings
@Composable
fun SettingsScreen(back: () -> Unit) {
    val a = agri
    val scope = rememberCoroutineScope()
    val u = AppState.user
    var name by rememberSaveable { mutableStateOf(u?.s("name") ?: "") }
    var district by rememberSaveable { mutableStateOf(u?.s("district") ?: "") }
    var notify by rememberSaveable { mutableStateOf(u?.get("notify_weather").bool()) }
    var share by rememberSaveable { mutableStateOf(u?.get("share_farm_with_assistant").bool()) }
    var cur by remember { mutableStateOf("") }
    var new by remember { mutableStateOf("") }
    var delPw by remember { mutableStateOf("") }
    var confirmDelete by remember { mutableStateOf(false) }
    val langs by produceState<List<JsonObject>>(emptyList()) { value = runCatching { AppState.languages().map { it.obj() } }.getOrDefault(emptyList()) }
    val activity by produceState<List<JsonObject>>(emptyList()) { value = runCatching { Api.get("/api/me/activity")["events"].arr().map { it.obj() } }.getOrDefault(emptyList()) }
    Page("Settings", back) {
        SectionLabel("Your profile")
        AppCard {
            Text(u?.s("email") ?: "", color = a.muted)
            Field("Full name", name, { name = it })
            Spacer(Modifier.height(8.dp))
            Field("District", district, { district = it })
            Row(verticalAlignment = Alignment.CenterVertically) { Text(tr("Weather alerts"), Modifier.weight(1f)); Switch(notify, { notify = it }) }
            Row(verticalAlignment = Alignment.CenterVertically) { Text(tr("Share my farm data with the assistant"), Modifier.weight(1f)); Switch(share, { share = it }) }
            PrimaryButton("Save", icon = Icons.Filled.Save) {
                scope.launch {
                    try { AppState.user = Api.put("/api/me", jsonOf("name" to name, "district" to district, "notify_weather" to if (notify) 1 else 0, "share_farm_with_assistant" to if (share) 1 else 0))["user"].obj(); AppState.toast = tr("Preferences saved") }
                    catch (e: ApiException) { AppState.toast = e.message }
                }
            }
        }
        SectionLabel("Language and display")
        AppCard {
            Select("Language", Session.language, langs.map { it.s("code") to it.s("native") }, { code ->
                AppState.setLanguage(code); scope.launch { runCatching { Api.put("/api/me", jsonOf("language" to code)) } }
            })
            Spacer(Modifier.height(8.dp))
            Select("Colour mode", Session.theme, listOf("system" to "Follow my device", "light" to "Light mode", "dark" to "Dark mode"), { Session.setThemePref(it) }, translateLabels = true)
        }
        SectionLabel("Change password")
        AppCard {
            Field("Current password", cur, { cur = it }, password = true)
            Spacer(Modifier.height(8.dp))
            Field("New password", new, { new = it }, password = true, hint = "At least 8 characters with letters and numbers.")
            Spacer(Modifier.height(8.dp))
            SecondaryButton("Change password", icon = Icons.Filled.Key) {
                scope.launch {
                    try { Api.put("/api/me/password", jsonOf("current" to cur, "new" to new)); AppState.toast = tr("Password changed. Please sign in again."); AppState.signOut() }
                    catch (e: ApiException) { AppState.toast = e.message }
                }
            }
        }
        SectionLabel("Recent sign-in activity")
        AppCard {
            if (activity.isEmpty()) Text(tr("No activity yet."), color = a.muted)
            activity.take(8).forEach { e -> Text("${dateOf(e["created_at"].num())} · ${tr(e.s("event").replace("_", " "))}${if (e.s("detail").isNotBlank()) " · ${e.s("detail")}" else ""}", style = MaterialTheme.typography.bodySmall) }
        }
        SecondaryButton("Sign out", icon = Icons.AutoMirrored.Filled.Logout) {
            scope.launch { runCatching { Api.post("/api/auth/logout") }; AppState.signOut() }
        }
        SectionLabel("Delete account")
        AppCard {
            Text(tr("Deletes your account and all of your farms, predictions, chats and photos. This cannot be undone."), style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(8.dp))
            Field("Password", delPw, { delPw = it }, password = true)
            Spacer(Modifier.height(8.dp))
            DangerButton("Delete my account") { confirmDelete = true }
        }
    }
    if (confirmDelete) AlertDialog(onDismissRequest = { confirmDelete = false }, title = { Text(tr("Delete your account permanently?")) },
        text = { Text(tr("All of your data will be removed. This cannot be undone.")) },
        confirmButton = { TextButton(onClick = {
            confirmDelete = false
            scope.launch { try { Api.post("/api/me/delete", jsonOf("password" to delPw)); AppState.signOut() } catch (e: ApiException) { AppState.toast = e.message } }
        }) { Text(tr("Delete")) } },
        dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text(tr("Cancel")) } })
}
