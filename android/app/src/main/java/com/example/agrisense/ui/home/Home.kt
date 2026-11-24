package com.example.agrisense.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.filled.ReceiptLong
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Coronavirus
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Landslide
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Science
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Thermostat
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.agrisense.data.Api
import com.example.agrisense.data.ApiException
import com.example.agrisense.data.arr
import com.example.agrisense.data.dateOf
import com.example.agrisense.data.fmt
import com.example.agrisense.data.num
import com.example.agrisense.data.obj
import com.example.agrisense.data.s
import com.example.agrisense.i18n.tr
import com.example.agrisense.ui.AppState
import com.example.agrisense.ui.components.AppCard
import com.example.agrisense.ui.components.Chip
import com.example.agrisense.ui.components.EmptyState
import com.example.agrisense.ui.components.ErrorState
import com.example.agrisense.ui.components.IconTile
import com.example.agrisense.ui.components.Loading
import com.example.agrisense.ui.components.SectionLabel
import com.example.agrisense.ui.components.SecondaryButton
import com.example.agrisense.ui.predict.runChain
import com.example.agrisense.ui.theme.agri
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject
import java.util.Calendar

val KIND_ICON = mapOf("crop" to Icons.Filled.Psychology, "yield" to Icons.Filled.TrendingUp, "fertiliser" to Icons.Filled.Science,
    "disease" to Icons.Filled.Coronavirus)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(open: (String) -> Unit) {
    val a = agri
    val scope = rememberCoroutineScope()
    var reload by remember { mutableIntStateOf(0) }
    var refreshing by remember { mutableStateOf(false) }
    val overview by produceState<Result<JsonObject>?>(null, reload) { value = runCatching { Api.get("/api/overview") }; refreshing = false }
    val weather by produceState<Result<JsonObject>?>(null, reload) { value = runCatching { Api.get("/api/weather") } }
    var chainBusy by remember { mutableStateOf(false) }

    PullToRefreshBox(isRefreshing = refreshing, onRefresh = { refreshing = true; reload++ }, modifier = Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(tr("Farm"), style = MaterialTheme.typography.labelMedium, color = a.muted)
                    Text(AppState.farms.firstOrNull()?.obj()?.s("name") ?: tr("No farm yet"), style = MaterialTheme.typography.titleMedium)
                }
                IconButton(onClick = { open("settings") }) { Icon(Icons.Filled.Settings, tr("Settings")) }
            }
            when (val r = overview) {
                null -> Loading()
                else -> r.fold(onFailure = { ErrorState((it as? ApiException)?.message ?: "This page could not load.") { reload++ } }, onSuccess = { o ->
                    val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
                    val greet = if (hour < 12) "Good morning" else if (hour < 17) "Good afternoon" else "Good evening"
                    AppCard(color = a.mint) {
                        Text("${tr(greet)}, ${o["user"].obj().s("name").substringBefore(" ")}!", style = MaterialTheme.typography.headlineSmall)
                        Spacer(Modifier.height(8.dp))
                        val w = weather?.getOrNull()
                        if (w != null) {
                            val c = w["current"].obj()
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Filled.WbSunny, null, tint = a.warn, modifier = Modifier.size(36.dp))
                                Spacer(Modifier.width(10.dp))
                                Column {
                                    Text("${fmt(c["temp"].num())}°C", style = MaterialTheme.typography.headlineSmall)
                                    Text("${tr(c.s("condition"))} · ${fmt(c["humidity"].num(), 0)}% ${tr("humidity")} · ${w["location"].obj().s("label")}",
                                        style = MaterialTheme.typography.bodySmall, color = a.muted)
                                }
                            }
                            w["alerts"].arr().firstOrNull()?.let { al ->
                                Spacer(Modifier.height(8.dp)); Chip(al.obj().s("text"), a.warn, a.warnBg, Icons.Filled.Warning)
                            }
                        } else Text(tr("Add a farm with its location to see live weather here."), style = MaterialTheme.typography.bodySmall, color = a.muted)
                    }
                    AppCard(onClick = { if (!chainBusy) { chainBusy = true; scope.launch { runChain(AppState.farms.firstOrNull()?.obj()?.s("id") ?: "", open); chainBusy = false } } },
                        color = a.mint2) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            IconTile(Icons.Filled.AutoAwesome, androidx.compose.ui.graphics.Color.White, a.primaryStrong, 44.dp)
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text(tr("Full auto analysis"), style = MaterialTheme.typography.titleSmall)
                                Text(listOf("Random soil sample from the dataset", "Crop model", "Fertiliser for that crop").joinToString(" → ") { tr(it) }, style = MaterialTheme.typography.bodySmall, color = a.muted)
                            }
                            if (chainBusy) androidx.compose.material3.CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
                            else Icon(Icons.Filled.ChevronRight, null, tint = a.primary)
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Tool("Which crop?", "Crop recommendation", Icons.Filled.Psychology, a.primaryDark, a.mint2, Modifier.weight(1f)) { open("crop") }
                        Tool("How much?", "Yield prediction", Icons.Filled.TrendingUp, a.sky, a.skyBg, Modifier.weight(1f)) { open("yield") }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Tool("Which fertiliser?", "Nutrient check", Icons.Filled.Science, a.warn, a.warnBg, Modifier.weight(1f)) { open("fertiliser") }
                        Tool("Is it sick?", "Leaf disease scan", Icons.Filled.Coronavirus, a.danger, a.dangerBg, Modifier.weight(1f)) { open("scan") }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Tool("Weather", "Forecast and history", Icons.Filled.Thermostat, a.sky, a.skyBg, Modifier.weight(1f)) { open("weather") }
                        Tool("Soil health", "Soil profile", Icons.Filled.Landslide, a.warn, a.warnBg, Modifier.weight(1f)) { open("soil") }
                    }
                    val k = o["kpis"].obj()
                    SectionLabel("Your activity")
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Kpi("Farms", fmt(k["farms"].num(), 0), Modifier.weight(1f))
                        Kpi("Predictions", fmt(k["total"].num(), 0), Modifier.weight(1f))
                        Kpi("Avg yield", k["avg_yield"].num()?.let { "${fmt(it, 2)} t/ha" } ?: "—", Modifier.weight(1f))
                    }
                    o["insights"].arr().takeIf { it.isNotEmpty() }?.let { ins ->
                        SectionLabel("AI farming insights")
                        ins.forEach { i -> AppCard { Text(tr(i.obj().s("text")), style = MaterialTheme.typography.bodyMedium) } }
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        SectionLabel("Recent results", Modifier.weight(1f))
                        androidx.compose.material3.TextButton(onClick = { open("history") }) { Text(tr("History")) }
                    }
                    val recent = o["recent"].arr()
                    if (recent.isEmpty()) EmptyState(Icons.Filled.History, "No predictions yet. Run your first one to see it here.")
                    recent.forEach { p ->
                        val po = p.obj()
                        AppCard(onClick = { open("prediction/${po.s("id")}") }) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                IconTile(KIND_ICON[po.s("kind")] ?: Icons.Filled.History, a.primaryDark, a.mint2, 36.dp)
                                Spacer(Modifier.width(10.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(po.s("summary"), style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    Text("${tr(po.s("kind").replaceFirstChar { it.uppercase() })} · ${dateOf(po["created_at"].num())}", style = MaterialTheme.typography.bodySmall, color = a.muted)
                                }
                                Icon(Icons.Filled.ChevronRight, null, tint = a.muted)
                            }
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        SecondaryButton("Reports", Modifier.weight(1f), Icons.AutoMirrored.Filled.ReceiptLong) { open("reports") }
                        SecondaryButton("History", Modifier.weight(1f), Icons.Filled.History) { open("history") }
                    }
                    Spacer(Modifier.height(40.dp))
                })
            }
        }
    }
}

@Composable
private fun Tool(t: String, sub: String, icon: ImageVector, fg: androidx.compose.ui.graphics.Color, bg: androidx.compose.ui.graphics.Color,
                 modifier: Modifier, onClick: () -> Unit) {
    AppCard(modifier, onClick = onClick) {
        IconTile(icon, fg, bg, 38.dp)
        Spacer(Modifier.height(8.dp))
        Text(tr(t), style = MaterialTheme.typography.titleSmall)
        Text(tr(sub), style = MaterialTheme.typography.bodySmall, color = agri.muted)
    }
}

@Composable
private fun Kpi(label: String, value: String, modifier: Modifier) {
    AppCard(modifier) {
        Text(tr(label), style = MaterialTheme.typography.labelMedium, color = agri.muted)
        Text(value, style = if (value.length > 6) MaterialTheme.typography.titleMedium else MaterialTheme.typography.titleLarge, maxLines = 1, softWrap = false)
    }
}

@Composable
fun PredictHub(open: (String) -> Unit) {
    val a = agri
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(tr("Predict"), style = MaterialTheme.typography.headlineMedium)
        Text(tr("Use your own values or a random real sample from the dataset."), color = a.muted)
        listOf(Triple("crop", "Crop recommendation", Icons.Filled.Psychology), Triple("yield", "Yield prediction", Icons.Filled.TrendingUp),
            Triple("fertiliser", "Fertiliser recommendation", Icons.Filled.Science), Triple("scan", "Plant disease detection", Icons.Filled.Coronavirus)).forEach { (r, l, ic) ->
            AppCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconTile(ic, a.primaryDark, a.mint2)
                    Spacer(Modifier.width(12.dp))
                    Text(tr(l), style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                }
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (r == "scan") SecondaryButton("Scan a leaf", Modifier.weight(1f), Icons.Filled.CameraAlt) { open(r) }
                    else {
                        SecondaryButton("My values", Modifier.weight(1f)) { open(r) }
                        SecondaryButton("Sample", Modifier.weight(1f), Icons.AutoMirrored.Filled.ArrowForward) { open("$r?auto=true") }
                    }
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryButton("History", Modifier.weight(1f), Icons.Filled.History) { open("history") }
            SecondaryButton("Reports", Modifier.weight(1f), Icons.AutoMirrored.Filled.ReceiptLong) { open("reports") }
        }
        Box(Modifier.height(40.dp))
    }
}
