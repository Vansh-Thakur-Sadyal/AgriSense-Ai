package com.example.agrisense.data

import com.example.agrisense.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.longOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

/** Error from the dashboard API: message + per-field messages, exactly as the web app shows them. */
class ApiException(val code: Int, override val message: String, val fields: Map<String, String> = emptyMap()) : Exception(message)

/**
 * Thin client over the dashboard's REST API (the "master API"): same endpoints as the web app, with the
 * session sent as a bearer token. No data is defined in the app itself.
 */
object Api {
    val base: String = BuildConfig.API_BASE.trimEnd('/')
    val json = Json { ignoreUnknownKeys = true; isLenient = true }
    private val JSON_TYPE = "application/json; charset=utf-8".toMediaType()
    var onUnauthorized: () -> Unit = {}

    val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val b = chain.request().newBuilder().header("X-Client", "android")
            Session.token?.let { b.header("Authorization", "Bearer $it") }
            chain.proceed(b.build())
        }
        .build()

    fun url(path: String) = base + path
    fun q(v: Any?) = URLEncoder.encode(v?.toString() ?: "", "UTF-8")

    suspend fun get(path: String) = call(path, Request.Builder().url(url(path)).get())
    suspend fun delete(path: String) = call(path, Request.Builder().url(url(path)).delete())
    suspend fun post(path: String, body: JsonObject = JsonObject(emptyMap())) =
        call(path, Request.Builder().url(url(path)).post(body.toString().toRequestBody(JSON_TYPE)))
    suspend fun put(path: String, body: JsonObject) =
        call(path, Request.Builder().url(url(path)).put(body.toString().toRequestBody(JSON_TYPE)))
    suspend fun patch(path: String, body: JsonObject) =
        call(path, Request.Builder().url(url(path)).patch(body.toString().toRequestBody(JSON_TYPE)))

    /** multipart/form-data: text fields + optional file (leaf photo). */
    suspend fun multipart(path: String, fields: Map<String, String>, fileField: String? = null, file: ByteArray? = null,
                          fileName: String = "leaf.jpg", mime: String = "image/jpeg"): JsonObject {
        val mb = MultipartBody.Builder().setType(MultipartBody.FORM)
        fields.forEach { (k, v) -> mb.addFormDataPart(k, v) }
        if (fileField != null && file != null) mb.addFormDataPart(fileField, fileName, file.toRequestBody(mime.toMediaType()))
        return call(path, Request.Builder().url(url(path)).post(mb.build()))
    }

    /** Raw bytes (PDF / CSV reports, images). */
    suspend fun bytes(path: String): ByteArray = withContext(Dispatchers.IO) {
        client.newCall(Request.Builder().url(url(path)).get().build()).execute().use { r ->
            if (r.code == 401) { onUnauthorized(); throw ApiException(401, "Please sign in") }
            if (!r.isSuccessful) throw ApiException(r.code, "Download failed (${r.code})")
            r.body?.bytes() ?: ByteArray(0)
        }
    }

    private suspend fun call(path: String, b: Request.Builder): JsonObject = withContext(Dispatchers.IO) {
        try {
            client.newCall(b.build()).execute().use { r ->
                val text = r.body?.string().orEmpty()
                val j = try { if (text.isBlank()) JsonObject(emptyMap()) else json.parseToJsonElement(text).jsonObject } catch (e: Exception) { JsonObject(emptyMap()) }
                if (!r.isSuccessful) {
                    if (r.code == 401 && !path.startsWith("/api/auth")) onUnauthorized()
                    val fields = (j["fields"] as? JsonObject)?.mapValues { it.value.str() } ?: emptyMap()
                    throw ApiException(r.code, j["error"].str().ifBlank { "Something went wrong (${r.code})" }, fields)
                }
                j
            }
        } catch (e: IOException) {
            throw ApiException(0, "Cannot reach the server. Check your internet connection.")
        }
    }
}

// ---------------- JSON helpers (API data is read as-is, no hard-coded models) ----------------
fun JsonElement?.obj(): JsonObject = this as? JsonObject ?: JsonObject(emptyMap())
fun JsonElement?.arr(): List<JsonElement> = (this as? JsonArray)?.toList() ?: emptyList()
fun JsonElement?.str(): String = when (this) { null, JsonNull -> ""; is JsonPrimitive -> contentOrNull ?: ""; else -> toString() }
fun JsonElement?.num(): Double? = (this as? JsonPrimitive)?.let { it.doubleOrNull ?: it.contentOrNull?.toDoubleOrNull() }
fun JsonElement?.int(): Int? = (this as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
fun JsonElement?.long(): Long? = (this as? JsonPrimitive)?.let { it.longOrNull ?: it.doubleOrNull?.toLong() }
// parentheses matter: `a ?: b != 0` parses as `(a ?: b) != 0`, which made every JSON false read as true
fun JsonElement?.bool(): Boolean = (this as? JsonPrimitive)?.let { p -> p.booleanOrNull ?: ((p.intOrNull ?: 0) != 0) } ?: false
fun JsonObject.s(key: String) = this[key].str()

fun jsonOf(vararg pairs: Pair<String, Any?>): JsonObject = JsonObject(pairs.associate { (k, v) ->
    k to when (v) {
        null -> JsonNull
        is JsonElement -> v
        is Number -> JsonPrimitive(v)
        is Boolean -> JsonPrimitive(v)
        else -> JsonPrimitive(v.toString())
    }
})

fun fmt(v: Double?, digits: Int = 1): String = if (v == null || v.isNaN()) "—" else
    String.format(java.util.Locale.US, "%,.${digits}f", v).let { if (digits > 0) it.trimEnd('0').trimEnd('.') else it }
fun pct(v: Double?): String = if (v == null) "—" else String.format(java.util.Locale.US, "%.1f%%", v * 100)
fun title(s: String) = s.split(" ").joinToString(" ") { w -> w.replaceFirstChar { it.uppercase() } }
fun dateOf(ts: Double?): String = if (ts == null) "" else
    java.text.SimpleDateFormat("dd MMM yyyy", java.util.Locale.getDefault()).format(java.util.Date((ts * 1000).toLong()))
