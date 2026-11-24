package com.example.agrisense.ui.farms

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Agriculture
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material.icons.filled.Save
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.example.agrisense.data.Api
import com.example.agrisense.data.ApiException
import com.example.agrisense.data.arr
import com.example.agrisense.data.dateOf
import com.example.agrisense.data.fmt
import com.example.agrisense.data.jsonOf
import com.example.agrisense.data.num
import com.example.agrisense.data.obj
import com.example.agrisense.data.s
import com.example.agrisense.data.str
import com.example.agrisense.i18n.tr
import com.example.agrisense.ui.AppState
import com.example.agrisense.ui.components.AppBar
import com.example.agrisense.ui.components.AppCard
import com.example.agrisense.ui.components.Chip
import com.example.agrisense.ui.components.DangerButton
import com.example.agrisense.ui.components.EmptyState
import com.example.agrisense.ui.components.ErrorState
import com.example.agrisense.ui.components.Field
import com.example.agrisense.ui.components.Loading
import com.example.agrisense.ui.components.PrimaryButton
import com.example.agrisense.ui.components.SecondaryButton
import com.example.agrisense.ui.components.SectionLabel
import com.example.agrisense.ui.components.Select
import com.example.agrisense.ui.home.KIND_ICON
import com.example.agrisense.ui.theme.agri
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.events.MapEventsReceiver
import org.osmdroid.views.overlay.MapEventsOverlay

/** OpenStreetMap view with the farms as pins; optional tap-to-pick. */
@Composable
fun FarmMap(farms: List<JsonObject>, modifier: Modifier, pick: ((Double, Double) -> Unit)? = null, picked: Pair<Double, Double>? = null) {
    AndroidView(
        modifier = modifier.clip(RoundedCornerShape(18.dp)),
        factory = { ctx ->
            MapView(ctx).apply {
                setTileSource(TileSourceFactory.MAPNIK); setMultiTouchControls(true); controller.setZoom(5.0)
                controller.setCenter(GeoPoint(22.5, 79.0))
                if (pick != null) overlays.add(MapEventsOverlay(object : MapEventsReceiver {
                    override fun singleTapConfirmedHelper(p: GeoPoint): Boolean { pick(p.latitude, p.longitude); return true }
                    override fun longPressHelper(p: GeoPoint) = false
                }))
            }
        },
        update = { map ->
            map.overlays.removeAll { it is Marker }
            val pts = farms.mapNotNull { f -> f["lat"].num()?.let { la -> f["lon"].num()?.let { lo -> Triple(la, lo, f.s("name")) } } } +
                listOfNotNull(picked?.let { Triple(it.first, it.second, "") })
            pts.forEach { (la, lo, name) -> map.overlays.add(Marker(map).apply { position = GeoPoint(la, lo); title = name; setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM) }) }
            pts.lastOrNull()?.let { map.controller.setZoom(if (pts.size == 1) 12.0 else 7.0); map.controller.setCenter(GeoPoint(it.first, it.second)) }
            map.invalidate()
        },
    )
}

@Composable
fun FarmsScreen(open: (String) -> Unit) {
    val a = agri
    var reload by remember { mutableIntStateOf(0) }
    val farms by produceState<Result<List<JsonObject>>?>(null, reload) { value = runCatching { AppState.loadFarms().map { it.obj() } } }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(tr("My farms"), style = MaterialTheme.typography.headlineMedium, modifier = Modifier.weight(1f))
            SecondaryButton("Add farm", icon = Icons.Filled.Add) { open("farmForm?id=0") }
        }
        when (val r = farms) {
            null -> Loading()
            else -> r.fold(onFailure = { ErrorState(it.message ?: "Could not load") { reload++ } }, onSuccess = { list ->
                if (list.any { it["lat"].num() != null }) FarmMap(list, Modifier.fillMaxWidth().height(230.dp))
                if (list.isEmpty()) EmptyState(Icons.Filled.Agriculture, "No farms yet. Add one with its location to unlock weather, soil data and farm-linked predictions.")
                list.forEach { f ->
                    AppCard(onClick = { open("farm/${f.s("id")}") }) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(f.s("name"), style = MaterialTheme.typography.titleMedium)
                                Text(listOf(f.s("village"), f.s("district"), f.s("state")).filter { it.isNotBlank() }.joinToString(", "), color = a.muted, style = MaterialTheme.typography.bodySmall)
                            }
                            if (f.s("current_crop").isNotBlank()) Chip(f.s("current_crop"), a.primaryDark, a.mint2, translate = false)
                            Icon(Icons.Filled.ChevronRight, null, tint = a.muted)
                        }
                        Spacer(Modifier.height(6.dp))
                        Text("${tr("Area")}: ${f["area_ha"].num()?.let { "${fmt(it, 2)} ha" } ?: "—"} · ${tr("Soil")}: ${tr(f.s("soil_type").ifBlank { "—" })} · ${tr("Irrigation")}: ${tr(f.s("irrigation").ifBlank { "—" })}",
                            style = MaterialTheme.typography.bodySmall, color = a.muted)
                    }
                }
                Spacer(Modifier.height(40.dp))
            })
        }
    }
}

@Composable
fun FarmDetailScreen(id: Int, back: () -> Unit, open: (String) -> Unit) {
    val a = agri
    val scope = rememberCoroutineScope()
    var ask by remember { mutableStateOf(false) }
    val data by produceState<Result<JsonObject>?>(null) { value = runCatching { Api.get("/api/farms/$id") } }
    Scaffold(topBar = { AppBar("Farm", back) }, containerColor = a.background) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            when (val r = data) {
                null -> Loading()
                else -> r.fold(onFailure = { ErrorState(it.message ?: "Could not load") }, onSuccess = { d ->
                    val f = d["farm"].obj()
                    Text(f.s("name"), style = MaterialTheme.typography.headlineMedium)
                    Text(listOf(f.s("village"), f.s("district"), f.s("state")).filter { it.isNotBlank() }.joinToString(", "), color = a.muted)
                    if (f["lat"].num() != null) FarmMap(listOf(f), Modifier.fillMaxWidth().height(200.dp))
                    AppCard {
                        listOf("Area" to (f["area_ha"].num()?.let { "${fmt(it, 2)} ha" } ?: "—"), "Soil type" to tr(f.s("soil_type").ifBlank { "—" }),
                            "Current crop" to f.s("current_crop").ifBlank { "—" }, "Irrigation" to tr(f.s("irrigation").ifBlank { "—" }),
                            "Coordinates" to (f["lat"].num()?.let { "${fmt(it, 4)}, ${fmt(f["lon"].num(), 4)}" } ?: "—"), "Notes" to f.s("notes").ifBlank { "—" }).forEach { (k, v) ->
                            Row(Modifier.padding(vertical = 3.dp)) { Text(tr(k), color = a.muted, modifier = Modifier.width(120.dp)); Text(v) }
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        SecondaryButton("Weather", Modifier.weight(1f)) { open("weather") }
                        SecondaryButton("Soil", Modifier.weight(1f)) { open("soil") }
                    }
                    SectionLabel("Results for this farm")
                    val preds = d["predictions"].arr().map { it.obj() }
                    if (preds.isEmpty()) Text(tr("No predictions linked to this farm yet."), color = a.muted)
                    preds.forEach { p ->
                        AppCard(onClick = { open("prediction/${p.s("id")}") }) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(KIND_ICON[p.s("kind")] ?: Icons.Filled.AutoAwesome, null, tint = a.primary)
                                Spacer(Modifier.width(10.dp))
                                Column(Modifier.weight(1f)) { Text(p.s("summary")); Text(dateOf(p["created_at"].num()), style = MaterialTheme.typography.labelSmall, color = a.muted) }
                            }
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        SecondaryButton("Edit", Modifier.weight(1f), Icons.Filled.Edit) { open("farmForm?id=$id") }
                        DangerButton("Delete", Modifier.weight(1f)) { ask = true }
                    }
                    Spacer(Modifier.height(32.dp))
                })
            }
        }
    }
    if (ask) AlertDialog(onDismissRequest = { ask = false },
        title = { Text(tr("Delete this farm?")) }, text = { Text(tr("Its predictions stay in your history but are unlinked from the farm.")) },
        confirmButton = { TextButton(onClick = { scope.launch { try { Api.delete("/api/farms/$id"); AppState.loadFarms(); AppState.toast = tr("Farm deleted"); back() } catch (e: ApiException) { AppState.toast = e.message } }; ask = false }) { Text(tr("Delete")) } },
        dismissButton = { TextButton(onClick = { ask = false }) { Text(tr("Cancel")) } })
}

@SuppressLint("MissingPermission")
private fun lastLocation(ctx: Context): Pair<Double, Double>? {
    val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    return lm.getProviders(true).mapNotNull { runCatching { lm.getLastKnownLocation(it) }.getOrNull() }.maxByOrNull { it.time }?.let { it.latitude to it.longitude }
}

@Composable
fun FarmFormScreen(id: Int, back: () -> Unit) {
    val a = agri
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val v = remember { mutableStateMapOf<String, String>() }
    var loaded by remember { mutableStateOf(id == 0) }
    var fields by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var busy by remember { mutableStateOf(false) }
    val meta by produceState<JsonObject?>(null) { value = runCatching { AppState.meta() }.getOrNull() }
    val states by produceState<List<String>>(emptyList()) { value = runCatching { Api.get("/api/public/states")["states"].arr().map { it.str() } }.getOrDefault(emptyList()) }
    val districts by produceState<List<String>>(emptyList(), v["state"]) {
        value = if (v["state"].isNullOrBlank()) emptyList() else runCatching { Api.get("/api/public/districts?state=${Api.q(v["state"])}")["districts"].arr().map { it.str() } }.getOrDefault(emptyList())
    }
    LaunchedEffect(id) {
        if (id != 0) runCatching { Api.get("/api/farms/$id")["farm"].obj() }.onSuccess { f ->
            listOf("name", "state", "district", "village", "lat", "lon", "area_ha", "soil_type", "current_crop", "irrigation", "notes").forEach { k -> v[k] = f.s(k) }
            loaded = true
        }
    }
    val perm = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        if (ok) lastLocation(ctx)?.let { v["lat"] = fmt(it.first, 5); v["lon"] = fmt(it.second, 5) } ?: run { AppState.toast = tr("Location not available yet - tap the map instead") }
    }
    Scaffold(topBar = { AppBar(if (id == 0) "Add farm" else "Edit farm", back) }, containerColor = a.background) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (!loaded) { Loading(); return@Column }
            Field("Farm name", v["name"].orEmpty(), { v["name"] = it }, error = fields["name"])
            Select("State", v["state"].orEmpty(), states.map { it to it }, { v["state"] = it; v["district"] = "" })
            Select("District", v["district"].orEmpty(), districts.map { it to it }, { v["district"] = it })
            Field("Village", v["village"].orEmpty(), { v["village"] = it })
            SectionLabel("Location")
            FarmMap(emptyList(), Modifier.fillMaxWidth().height(220.dp), pick = { la, lo -> v["lat"] = fmt(la, 5); v["lon"] = fmt(lo, 5) },
                picked = v["lat"]?.toDoubleOrNull()?.let { la -> v["lon"]?.toDoubleOrNull()?.let { la to it } })
            Text(tr("Tap the map to drop a pin, or use your current location."), color = a.muted, style = MaterialTheme.typography.bodySmall)
            SecondaryButton("Use my location", icon = Icons.Filled.MyLocation) {
                if (ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED)
                    lastLocation(ctx)?.let { v["lat"] = fmt(it.first, 5); v["lon"] = fmt(it.second, 5) } ?: run { AppState.toast = tr("Location not available yet - tap the map instead") }
                else perm.launch(Manifest.permission.ACCESS_FINE_LOCATION)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Field("Latitude", v["lat"].orEmpty(), { v["lat"] = it }, Modifier.weight(1f), keyboard = KeyboardType.Decimal, error = fields["lat"])
                Field("Longitude", v["lon"].orEmpty(), { v["lon"] = it }, Modifier.weight(1f), keyboard = KeyboardType.Decimal, error = fields["lon"])
            }
            Field("Area (ha)", v["area_ha"].orEmpty(), { v["area_ha"] = it }, keyboard = KeyboardType.Decimal, error = fields["area_ha"])
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Select("Soil type", v["soil_type"].orEmpty(), meta?.get("soil_types").arr().map { it.str() to it.str() }, { v["soil_type"] = it }, Modifier.weight(1f), translateLabels = true)
                Select("Irrigation", v["irrigation"].orEmpty(), meta?.get("irrigation").arr().map { it.str() to it.str() }, { v["irrigation"] = it }, Modifier.weight(1f), translateLabels = true)
            }
            Field("Current crop", v["current_crop"].orEmpty(), { v["current_crop"] = it })
            Field("Notes", v["notes"].orEmpty(), { v["notes"] = it }, singleLine = false, minLines = 3)
            PrimaryButton("Save", icon = Icons.Filled.Save, loading = busy) {
                busy = true; fields = emptyMap()
                scope.launch {
                    try {
                        val body = jsonOf(*listOf("name", "state", "district", "village", "lat", "lon", "area_ha", "soil_type", "current_crop", "irrigation", "notes")
                            .map { it to (v[it] ?: "") }.toTypedArray())
                        if (id == 0) Api.post("/api/farms", body) else Api.put("/api/farms/$id", body)
                        AppState.loadFarms(); AppState.toast = tr("Farm saved"); back()
                    } catch (e: ApiException) { fields = e.fields; AppState.toast = e.message }
                    busy = false
                }
            }
            Spacer(Modifier.height(32.dp))
        }
    }
}
