package com.example.agrisense.i18n

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.example.agrisense.data.Api
import com.example.agrisense.data.jsonOf
import com.example.agrisense.data.obj
import com.example.agrisense.data.str
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import java.io.File

/**
 * Interface translation, same service as the dashboard: English strings are sent to /api/i18n/translate
 * (Azure AI Translator, cached in the dashboard database) and kept in a per-language file on the phone,
 * so each phrase is fetched once. Reading [t] inside a composable recomposes it when the translation arrives.
 */
object Tr {
    private lateinit var dir: File
    var lang by mutableStateOf("en")
        private set
    private val map = mutableStateMapOf<String, String>()
    private val pending = mutableSetOf<String>()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var job: Job? = null
    private val word = Regex("[A-Za-z]{2,}")

    fun init(ctx: Context, code: String) { dir = File(ctx.filesDir, "i18n").apply { mkdirs() }; use(code) }

    fun use(code: String) {
        lang = code
        map.clear()
        if (code == "en") return
        val f = File(dir, "$code.json")
        if (f.exists()) runCatching {
            Api.json.parseToJsonElement(f.readText()).obj().forEach { (k, v) -> map[k] = v.str() }
        }
    }

    fun t(s: String): String {
        if (lang == "en" || s.isBlank() || !word.containsMatchIn(s) || s.length > 400) return s
        map[s]?.let { return it }
        synchronized(pending) { pending.add(s) }
        schedule()
        return s
    }

    private fun schedule() {
        if (job?.isActive == true) return
        job = scope.launch {
            delay(120)
            val code = lang
            val batch = synchronized(pending) { pending.take(150).also { pending.removeAll(it.toSet()) } }
            if (batch.isEmpty() || code == "en") return@launch
            try {
                val r = Api.post("/api/i18n/translate", jsonOf("lang" to code, "texts" to JsonArray(batch.map { JsonPrimitive(it) })))
                val got = r["translations"].obj()
                if (lang == code) {
                    got.forEach { (k, v) -> map[k] = v.str() }
                    batch.forEach { if (map[it] == null) map[it] = it }       // untranslatable: stop asking
                    File(dir, "$code.json").writeText(JsonObject(map.mapValues { JsonPrimitive(it.value) }).toString())
                }
            } catch (e: Exception) {
                delay(15000)                                                  // offline or busy: retry later
            }
            if (synchronized(pending) { pending.isNotEmpty() }) { job = null; schedule() }
        }
    }
}

/** Translated UI text. Not @Composable so it also works in click handlers; reads during composition are still
 *  tracked (the map is snapshot state), so screens re-render when a translation arrives. */
fun tr(s: String): String = Tr.t(s)
