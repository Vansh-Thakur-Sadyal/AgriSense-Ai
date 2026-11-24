package com.example.agrisense.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.example.agrisense.data.Api
import com.example.agrisense.data.Session
import com.example.agrisense.data.arr
import com.example.agrisense.data.obj
import com.example.agrisense.i18n.Tr
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

/** In-memory state shared between screens. All of it comes from the API; nothing is defined here. */
object AppState {
    var user by mutableStateOf<JsonObject?>(null)
    var farms by mutableStateOf<List<JsonElement>>(emptyList())
    var status by mutableStateOf<JsonObject?>(null)
    var cropInfo by mutableStateOf<JsonObject?>(null)
    var yieldOptions by mutableStateOf<JsonObject?>(null)
    var languages by mutableStateOf<List<JsonElement>>(emptyList())
    var meta by mutableStateOf<JsonObject?>(null)

    /** One-shot hand-overs between screens (like goWith() in the web app). */
    var pendingAsk by mutableStateOf<String?>(null)
    var chain by mutableStateOf<JsonObject?>(null)          // {sample?, crop, fert, inp}
    var otp by mutableStateOf<JsonObject?>(null)            // challenge from sign-up / sign-in / reset
    var toast by mutableStateOf<String?>(null)

    suspend fun loadFarms(): List<JsonElement> { farms = Api.get("/api/farms")["farms"].arr(); return farms }
    suspend fun cropInfo(): JsonObject = cropInfo ?: Api.get("/api/crop/info").also { cropInfo = it }
    suspend fun yieldOptions(): JsonObject = yieldOptions ?: Api.get("/api/yield/options").also { yieldOptions = it }
    /** Option lists (soil types, irrigation, roles, fertiliser bases, prediction kinds) defined once on the server. */
    suspend fun meta(): JsonObject = meta ?: Api.get("/api/meta/options").also { meta = it }
    suspend fun languages(): List<JsonElement> =
        languages.ifEmpty { Api.get("/api/i18n/languages")["languages"].arr().also { languages = it } }

    fun signedIn(r: JsonObject) {
        r["token"]?.let { Session.signIn(it.toString().trim('"')) }
        user = r["user"].obj()
        val lang = user?.get("language")?.toString()?.trim('"')
        if (!lang.isNullOrBlank() && lang != Session.language) { Session.setLang(lang); Tr.use(lang) }
    }

    fun signOut() { Session.signOut(); user = null; farms = emptyList(); chain = null; pendingAsk = null }

    fun setLanguage(code: String) { Session.setLang(code); Tr.use(code) }
}
