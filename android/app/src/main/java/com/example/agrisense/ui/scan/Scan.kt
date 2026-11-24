package com.example.agrisense.ui.scan

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Biotech
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Coronavirus
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.HideImage
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.example.agrisense.data.Api
import com.example.agrisense.data.ApiException
import com.example.agrisense.data.arr
import com.example.agrisense.data.num
import com.example.agrisense.data.obj
import com.example.agrisense.data.pct
import com.example.agrisense.data.s
import com.example.agrisense.i18n.tr
import com.example.agrisense.ui.AppState
import com.example.agrisense.ui.components.AppCard
import com.example.agrisense.ui.components.BarRow
import com.example.agrisense.ui.components.Chip
import com.example.agrisense.ui.components.Note
import com.example.agrisense.ui.components.PrimaryButton
import com.example.agrisense.ui.components.SecondaryButton
import com.example.agrisense.ui.predict.FarmPicker
import com.example.agrisense.ui.theme.agri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject
import java.io.ByteArrayOutputStream
import java.io.File

/** Read a photo, fix its size (max 1024 px) and return JPEG bytes: small uploads on slow networks. */
fun loadJpeg(ctx: Context, uri: Uri): ByteArray? = runCatching {
    val bmp = ctx.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) } ?: return null
    shrink(bmp)
}.getOrNull()

fun shrink(bmp: Bitmap, max: Int = 1024): ByteArray {
    val scale = (max.toFloat() / maxOf(bmp.width, bmp.height)).coerceAtMost(1f)
    val b = if (scale < 1f) Bitmap.createScaledBitmap(bmp, (bmp.width * scale).toInt(), (bmp.height * scale).toInt(), true) else bmp
    return ByteArrayOutputStream().also { b.compress(Bitmap.CompressFormat.JPEG, 88, it) }.toByteArray()
}

@Composable
fun ScanScreen(back: () -> Unit, open: (String) -> Unit) {
    val a = agri
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var photo by remember { mutableStateOf<ByteArray?>(null) }
    var sample by remember { mutableStateOf<JsonObject?>(null) }
    var result by remember { mutableStateOf<JsonObject?>(null) }
    var busy by remember { mutableStateOf(false) }
    var farm by rememberSaveable { mutableStateOf("") }
    val camFile = remember { File(ctx.cacheDir, "leaf_capture.jpg") }
    val camUri = remember { FileProvider.getUriForFile(ctx, ctx.packageName + ".files", camFile) }

    fun analyse(bytes: ByteArray) {
        busy = true; result = null
        scope.launch {
            try { result = Api.multipart("/api/disease", mapOf("farm_id" to farm), "image", bytes); AppState.toast = tr("Saved to history") }
            catch (e: ApiException) { AppState.toast = e.message }
            busy = false
        }
    }
    val camera = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        if (ok) scope.launch { val b = withContext(Dispatchers.IO) { loadJpeg(ctx, camUri) }; if (b != null) { sample = null; photo = b; analyse(b) } }
    }
    val gallery = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) scope.launch { val b = withContext(Dispatchers.IO) { loadJpeg(ctx, uri) }; if (b != null) { sample = null; photo = b; analyse(b) } }
    }

    Column(Modifier.fillMaxSize().background(a.background).verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(tr("Scan a leaf"), style = MaterialTheme.typography.headlineMedium)
        Text(tr("One leaf, filling the frame, on a plain background, in daylight."), color = a.muted)
        Box(Modifier.fillMaxWidth().heightIn(min = 220.dp).clip(RoundedCornerShape(20.dp)).background(a.mint2), contentAlignment = Alignment.Center) {
            val bmp = remember(photo) { photo?.let { BitmapFactory.decodeByteArray(it, 0, it.size)?.asImageBitmap() } }
            if (bmp != null) Image(bmp, null, Modifier.fillMaxWidth().height(260.dp), contentScale = ContentScale.Crop)
            else Column(horizontalAlignment = Alignment.CenterHorizontally) {
                androidx.compose.material3.Icon(Icons.Filled.CameraAlt, null, tint = a.primary, modifier = Modifier.padding(8.dp))
                Text(tr("Take or choose a leaf photo"), color = a.muted)
            }
        }
        PrimaryButton("Take photo", icon = Icons.Filled.CameraAlt, loading = busy) { camera.launch(camUri) }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryButton("Gallery", Modifier.weight(1f), Icons.Filled.PhotoLibrary) {
                gallery.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            }
            SecondaryButton("Dataset sample", Modifier.weight(1f), Icons.Filled.Shuffle) {
                busy = true
                scope.launch {
                    try {
                        val s = Api.get("/api/samples/leaf")
                        val b = Api.bytes(s.s("url")); sample = s; photo = b; busy = false; analyse(b)
                    } catch (e: ApiException) { AppState.toast = e.message; busy = false }
                }
            }
        }
        FarmPicker(farm) { farm = it }
        result?.let { DiseaseResult(it, sample, open) }
        Spacer(Modifier.height(40.dp))
    }
}

@Composable
private fun DiseaseResult(r: JsonObject, sample: JsonObject?, open: (String) -> Unit) {
    val a = agri
    val b = r["best"].obj()
    val (icon, color, head, line) = when (r.s("verdict")) {
        "healthy" -> listOf(Icons.Filled.CheckCircle, a.primaryDark, "Healthy leaf", "${b.s("crop")} — ${tr("no disease detected")}")
        "diseased" -> listOf(Icons.Filled.Coronavirus, a.danger, "Disease detected", "${b.s("crop")} — ${b.s("condition")}")
        "uncertain" -> listOf(Icons.Filled.HelpOutline, a.warn, "Not sure", tr("The model is not confident enough to name a disease"))
        else -> listOf(Icons.Filled.HideImage, a.muted, "No leaf found", tr("This does not look like a leaf photo"))
    }
    if (sample != null) {
        val right = sample.s("class") == b.s("class") && r.s("verdict") != "uncertain"
        Note("${tr("Dataset label")}: ${sample.s("crop")} — ${sample.s("condition")}. " + tr(if (right) "The model got it right." else "Compare with the model's answer below."),
            warn = !right, translate = false)
    }
    AppCard {
        @Suppress("UNCHECKED_CAST")
        Chip(head as String, color as androidx.compose.ui.graphics.Color, a.mint, icon as androidx.compose.ui.graphics.vector.ImageVector)
        Spacer(Modifier.height(6.dp))
        Text(tr(line as String), style = MaterialTheme.typography.headlineSmall)
        Text("${tr("Model confidence")} ${pct(b["probability"].num())} (${tr("answers only at")} ≥ ${pct(r["threshold"].num())})", style = MaterialTheme.typography.bodySmall, color = a.muted)
        Spacer(Modifier.height(8.dp))
        r["top"].arr().forEach { t -> val o = t.obj(); BarRow("${o.s("crop")}: ${o.s("condition")}", o["probability"].num() ?: 0.0, 1.0, pct(o["probability"].num()), a.primary) }
    }
    val info = r["info"] as? JsonObject
    if (info != null && r.s("verdict") == "diseased") {
        listOf("cause" to "Cause", "symptoms" to "Symptoms", "management" to "Next steps").forEach { (k, l) ->
            AppCard(color = a.mint) { Text(tr(l).uppercase(), style = MaterialTheme.typography.labelMedium, color = a.muted); Text(tr(info.s(k))) }
        }
    }
    Note("AI detection is an initial screening tool. Confirm uncertain results with an agricultural expert.", warn = true)
    SecondaryButton("Ask the assistant", icon = Icons.Filled.SmartToy) {
        AppState.pendingAsk = when (r.s("verdict")) {
            "diseased" -> "My ${b.s("crop")} leaf was diagnosed with ${b.s("condition")} (${pct(b["probability"].num())} confidence, result #${r.s("id")}). How do I confirm it in the field and what can I do now, without chemical doses?"
            "healthy" -> "My ${b.s("crop")} leaf looks healthy according to the disease model (result #${r.s("id")}). What should I keep monitoring this season?"
            else -> "The disease model could not identify my leaf photo (result #${r.s("id")}). How should I take a better photo, and what symptoms should I describe?"
        }
        open("assistant")
    }
}
