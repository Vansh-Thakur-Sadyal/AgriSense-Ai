package com.example.agrisense.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.filled.Login
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material.icons.filled.LockReset
import androidx.compose.material.icons.filled.MarkEmailRead
import androidx.compose.material.icons.filled.PersonAdd
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.agrisense.data.Api
import com.example.agrisense.data.ApiException
import com.example.agrisense.data.Session
import com.example.agrisense.data.arr
import com.example.agrisense.data.int
import com.example.agrisense.data.jsonOf
import com.example.agrisense.data.obj
import com.example.agrisense.data.s
import com.example.agrisense.data.str
import com.example.agrisense.i18n.tr
import com.example.agrisense.ui.AppState
import com.example.agrisense.ui.components.ErrorState
import com.example.agrisense.ui.components.Field
import com.example.agrisense.ui.components.Loading
import com.example.agrisense.ui.components.Note
import com.example.agrisense.ui.components.PrimaryButton
import com.example.agrisense.ui.components.Select
import com.example.agrisense.ui.theme.agri
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject

/** First launch: pick one of the languages the dashboard offers (/api/i18n/languages). */
@Composable
fun LanguageScreen(onDone: () -> Unit) {
    val a = agri
    var reload by remember { mutableIntStateOf(0) }
    val langs by produceState<Result<List<JsonObject>>?>(null, reload) {
        value = runCatching { AppState.languages().map { it.obj() } }
    }
    var picked by remember { mutableStateOf(Session.language) }
    Column(Modifier.fillMaxSize().background(a.background).statusBarsPadding().padding(20.dp)) {
        Box(Modifier.size(56.dp).clip(RoundedCornerShape(16.dp)).background(a.primaryStrong), contentAlignment = Alignment.Center) {
            Icon(Icons.Filled.Eco, null, tint = Color.White, modifier = Modifier.size(30.dp))
        }
        Spacer(Modifier.height(16.dp))
        Text(tr("Choose your language"), style = MaterialTheme.typography.headlineMedium)
        Text(tr("You can change it later in Settings."), color = a.muted, style = MaterialTheme.typography.bodyMedium)
        Spacer(Modifier.height(16.dp))
        when (val r = langs) {
            null -> Loading()
            else -> r.fold(onSuccess = { list ->
                LazyVerticalGrid(GridCells.Fixed(3), Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(10.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(list) { l ->
                        val code = l.s("code"); val sel = code == picked
                        Column(
                            Modifier.heightIn(min = 72.dp).clip(RoundedCornerShape(16.dp)).background(if (sel) a.mint2 else a.surface)
                                .border(if (sel) 2.dp else 1.dp, if (sel) a.primary else a.line, RoundedCornerShape(16.dp))
                                .clickable { picked = code; AppState.setLanguage(code) }.padding(8.dp),
                            horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
                        ) {
                            Text(l.s("native"), style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
                            if (sel) Icon(Icons.Filled.CheckCircle, null, tint = a.primary, modifier = Modifier.size(18.dp))
                            else Text(l.s("name"), style = MaterialTheme.typography.labelSmall, color = a.muted)
                        }
                    }
                }
            }, onFailure = { ErrorState(it.message ?: "Could not load languages") { reload++ } })
        }
        Spacer(Modifier.height(12.dp))
        PrimaryButton("Continue", icon = Icons.AutoMirrored.Filled.ArrowForward, enabled = langs?.isSuccess == true) { onDone() }
    }
}

/** Sign in / sign up / forgot password, each followed by the e-mail code step (same API as the website). */
@Composable
fun AuthFlow() {
    var screen by rememberSaveable { mutableStateOf("signin") }
    val challenge = AppState.otp
    when {
        challenge != null -> OtpScreen(challenge, onBack = { AppState.otp = null })
        screen == "signup" -> SignUpScreen(onSignIn = { screen = "signin" })
        screen == "forgot" -> ForgotScreen(onBack = { screen = "signin" })
        else -> SignInScreen(onSignUp = { screen = "signup" }, onForgot = { screen = "forgot" })
    }
}

@Composable
private fun AuthFrame(title: String, sub: String, content: @Composable () -> Unit) {
    val a = agri
    Column(Modifier.fillMaxSize().background(a.background).statusBarsPadding().imePadding().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(40.dp).clip(RoundedCornerShape(12.dp)).background(a.primaryStrong), contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.Eco, null, tint = Color.White)
            }
            Spacer(Modifier.size(10.dp))
            Text("AgriSense AI", style = MaterialTheme.typography.titleLarge)
        }
        Spacer(Modifier.height(4.dp))
        Text(tr(title), style = MaterialTheme.typography.headlineMedium)
        Text(tr(sub), color = a.muted, style = MaterialTheme.typography.bodyMedium)
        content()
    }
}

private fun handle(r: JsonObject) {
    if (r["otp_required"]?.toString() == "true") AppState.otp = r else AppState.signedIn(r)
}

@Composable
private fun SignInScreen(onSignUp: () -> Unit, onForgot: () -> Unit) {
    val scope = rememberCoroutineScope()
    var id by rememberSaveable { mutableStateOf("") }
    var pw by rememberSaveable { mutableStateOf("") }
    var remember by rememberSaveable { mutableStateOf(true) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    AuthFrame("Sign in", "Welcome back. We will e-mail you a code to finish signing in.") {
        Field("Email or phone", id, { id = it }, keyboard = KeyboardType.Email)
        Field("Password", pw, { pw = it }, password = true)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(remember, { remember = it })
            Text(tr("Remember me"), Modifier.weight(1f))
            TextButton(onClick = onForgot) { Text(tr("Forgot password?")) }
        }
        error?.let { Note(it, warn = true) }
        PrimaryButton("Sign in", icon = Icons.AutoMirrored.Filled.Login, loading = busy) {
            busy = true; error = null
            scope.launch {
                try { handle(Api.post("/api/auth/login", jsonOf("identifier" to id.trim(), "password" to pw, "remember" to remember))) }
                catch (e: ApiException) { error = e.message }
                busy = false
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            Text(tr("New to AgriSense AI?"), color = agri.muted)
            TextButton(onClick = onSignUp) { Text(tr("Create account"), fontWeight = FontWeight.SemiBold) }
        }
    }
}

@Composable
private fun SignUpScreen(onSignIn: () -> Unit) {
    val scope = rememberCoroutineScope()
    val v = remember { mutableStateMapOf("name" to "", "email" to "", "phone" to "", "password" to "", "state" to "", "district" to "", "role" to "farmer") }
    var fields by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val states by produceState<List<String>>(emptyList()) { value = runCatching { Api.get("/api/public/states")["states"].arr().map { it.str() } }.getOrDefault(emptyList()) }
    val districts by produceState<List<String>>(emptyList(), v["state"]) {
        value = if (v["state"].isNullOrBlank()) emptyList()
        else runCatching { Api.get("/api/public/districts?state=${Api.q(v["state"])}")["districts"].arr().map { it.str() } }.getOrDefault(emptyList())
    }
    AuthFrame("Create account", "We will e-mail a 6-digit code to confirm your address.") {
        Field("Full name", v["name"]!!, { v["name"] = it }, error = fields["name"])
        Field("Email", v["email"]!!, { v["email"] = it }, keyboard = KeyboardType.Email, error = fields["email"])
        Field("Phone (optional)", v["phone"]!!, { v["phone"] = it }, keyboard = KeyboardType.Phone, error = fields["phone"])
        Field("Password", v["password"]!!, { v["password"] = it }, password = true, error = fields["password"],
            hint = "At least 8 characters with letters and numbers.")
        Select("State", v["state"]!!, states.map { it to it }, { v["state"] = it; v["district"] = "" })
        Select("District", v["district"]!!, districts.map { title(it.lowercase()) to title(it.lowercase()) }, { v["district"] = it })
        val roles by produceState<List<Pair<String, String>>>(emptyList()) {
            value = runCatching { AppState.meta()["roles"].arr().map { it.obj().s("value") to it.obj().s("label") } }.getOrDefault(emptyList())
        }
        Select("Role", v["role"]!!, roles, { v["role"] = it }, translateLabels = true)
        error?.let { Note(it, warn = true) }
        PrimaryButton("Create account", icon = Icons.Filled.PersonAdd, loading = busy) {
            busy = true; error = null; fields = emptyMap()
            scope.launch {
                try { handle(Api.post("/api/auth/register", jsonOf(*v.map { it.key to it.value.trim() }.toTypedArray(), "language" to Session.language))) }
                catch (e: ApiException) { error = e.message; fields = e.fields }
                busy = false
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            Text(tr("Already registered?"), color = agri.muted)
            TextButton(onClick = onSignIn) { Text(tr("Sign in"), fontWeight = FontWeight.SemiBold) }
        }
    }
}

private fun title(s: String) = s.split(" ").joinToString(" ") { w -> w.replaceFirstChar { it.uppercase() } }

@Composable
private fun ForgotScreen(onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    var email by rememberSaveable { mutableStateOf("") }
    var pw by rememberSaveable { mutableStateOf("") }
    var fields by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    AuthFrame("Reset your password", "Enter your account e-mail and a new password. We will e-mail you a code to confirm it is you.") {
        Field("Email", email, { email = it }, keyboard = KeyboardType.Email, error = fields["email"])
        Field("New password", pw, { pw = it }, password = true, error = fields["new_password"], hint = "At least 8 characters with letters and numbers.")
        error?.let { Note(it, warn = true) }
        PrimaryButton("Send code", icon = Icons.Filled.LockReset, loading = busy) {
            busy = true; error = null; fields = emptyMap()
            scope.launch {
                try { handle(Api.post("/api/auth/forgot", jsonOf("email" to email.trim(), "new_password" to pw))) }
                catch (e: ApiException) { error = e.message; fields = e.fields }
                busy = false
            }
        }
        TextButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text(tr("Back to sign in")) }
    }
}

@Composable
private fun OtpScreen(ch: JsonObject, onBack: () -> Unit) {
    val a = agri
    val scope = rememberCoroutineScope()
    var code by rememberSaveable { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var wait by remember { mutableIntStateOf(ch["resend_in"].int() ?: 60) }
    LaunchedEffect(wait) { if (wait > 0) { delay(1000); wait-- } }
    val what = when (ch.s("purpose")) { "signup" -> "finish creating your account"; "reset" -> "set your new password"; else -> "finish signing in" }
    val verify: () -> Unit = {
        busy = true; error = null
        scope.launch {
            try { val r = Api.post("/api/auth/otp/verify", jsonOf("challenge_id" to ch.s("challenge_id"), "code" to code)); AppState.otp = null; AppState.signedIn(r) }
            catch (e: ApiException) { error = e.message; code = "" }
            busy = false
        }
    }
    AuthFrame("Check your e-mail", "${tr("We sent a 6-digit code to")} ${ch.s("email")}. ${tr("Enter it to $what.")}") {
        Icon(Icons.Filled.MarkEmailRead, null, tint = a.primary, modifier = Modifier.size(40.dp))
        OutlinedTextField(
            value = code, onValueChange = { new -> code = new.filter { it.isDigit() }.take(6); if (code.length == 6 && !busy) verify() },
            modifier = Modifier.fillMaxWidth(), singleLine = true, shape = RoundedCornerShape(14.dp),
            textStyle = MaterialTheme.typography.headlineSmall.copy(letterSpacing = 8.sp, textAlign = TextAlign.Center),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword), placeholder = { Text("••••••", Modifier.fillMaxWidth(), textAlign = TextAlign.Center) },
        )
        error?.let { Note(it, warn = true) }
        PrimaryButton("Verify", loading = busy, enabled = code.length == 6) { verify() }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onBack) { Text(tr("Start again")) }
            Spacer(Modifier.weight(1f))
            TextButton(enabled = wait <= 0, onClick = {
                scope.launch {
                    try { val r = Api.post("/api/auth/otp/resend", jsonOf("challenge_id" to ch.s("challenge_id"))); wait = r["resend_in"].int() ?: 60; AppState.toast = tr("New code sent") }
                    catch (e: ApiException) { error = e.message }
                }
            }) { Text(if (wait > 0) "${tr("Resend in")} ${wait}s" else tr("Resend code")) }
        }
        Text(tr("Did not get it? Check the spam folder."), color = a.muted, style = MaterialTheme.typography.bodySmall)
    }
}
