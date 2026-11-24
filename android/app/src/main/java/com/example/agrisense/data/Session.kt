package com.example.agrisense.data

import android.content.Context
import android.content.SharedPreferences
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * What the app keeps on the phone: the session token (encrypted), the chosen language and theme.
 * Everything else (profile, farms, results, chats) lives in the dashboard database and is fetched.
 */
object Session {
    private lateinit var prefs: SharedPreferences

    var token by mutableStateOf<String?>(null)
        private set
    var language by mutableStateOf("en")
        private set
    var theme by mutableStateOf("system")       // system | light | dark
        private set
    var onboarded by mutableStateOf(false)
        private set

    fun init(ctx: Context) {
        prefs = try {
            val key = MasterKey.Builder(ctx).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
            EncryptedSharedPreferences.create(ctx, "agrisense_secure", key,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM)
        } catch (e: Exception) {
            ctx.getSharedPreferences("agrisense_fallback", Context.MODE_PRIVATE)
        }
        token = prefs.getString("token", null)
        language = prefs.getString("language", "en") ?: "en"
        theme = prefs.getString("theme", "system") ?: "system"
        onboarded = prefs.getBoolean("onboarded", false)
    }

    fun signIn(newToken: String) { token = newToken; prefs.edit().putString("token", newToken).apply() }
    fun signOut() { token = null; prefs.edit().remove("token").apply() }
    fun setLang(code: String) { language = code; prefs.edit().putString("language", code).apply() }
    fun setThemePref(p: String) { theme = p; prefs.edit().putString("theme", p).apply() }
    fun finishOnboarding() { onboarded = true; prefs.edit().putBoolean("onboarded", true).apply() }
}
