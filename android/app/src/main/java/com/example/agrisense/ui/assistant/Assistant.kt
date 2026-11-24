package com.example.agrisense.ui.assistant

import android.app.Activity
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AddPhotoAlternate
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Translate
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import com.example.agrisense.data.Api
import com.example.agrisense.data.ApiException
import com.example.agrisense.data.Session
import com.example.agrisense.data.arr
import com.example.agrisense.data.bool
import com.example.agrisense.data.dateOf
import com.example.agrisense.data.int
import com.example.agrisense.data.jsonOf
import com.example.agrisense.data.num
import com.example.agrisense.data.obj
import com.example.agrisense.data.s
import com.example.agrisense.i18n.Tr
import com.example.agrisense.i18n.tr
import com.example.agrisense.ui.AppState
import com.example.agrisense.ui.components.IconTile
import com.example.agrisense.ui.scan.loadJpeg
import com.example.agrisense.ui.theme.agri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject

private val SPEECH = mapOf("en" to "en-IN", "hi" to "hi-IN", "bn" to "bn-IN", "mr" to "mr-IN", "te" to "te-IN", "ta" to "ta-IN", "gu" to "gu-IN",
    "ur" to "ur-IN", "kn" to "kn-IN", "or" to "or-IN", "ml" to "ml-IN", "pa" to "pa-IN", "as" to "as-IN", "mai" to "hi-IN", "gom" to "hi-IN")
private val SCRIPT = mapOf("hi" to 0x900..0x97f, "mr" to 0x900..0x97f, "mai" to 0x900..0x97f, "gom" to 0x900..0x97f, "bn" to 0x980..0x9ff,
    "as" to 0x980..0x9ff, "pa" to 0xa00..0xa7f, "gu" to 0xa80..0xaff, "or" to 0xb00..0xb7f, "ta" to 0xb80..0xbff, "te" to 0xc00..0xc7f,
    "kn" to 0xc80..0xcff, "ml" to 0xd00..0xd7f, "ur" to 0x600..0x6ff)

private fun inLang(text: String, lang: String): Boolean {
    val r = SCRIPT[lang] ?: return true
    val letters = text.filter { it.isLetter() }
    if (letters.isEmpty()) return true
    return letters.count { it.code in r } * 2 >= letters.length
}

/** Minimal markdown: **bold**, bullet / numbered lines. */
private fun md(s: String): AnnotatedString = buildAnnotatedString {
    s.lines().forEachIndexed { i, raw ->
        var line = raw.replace(Regex("^#{1,4} "), "")
        line = line.replace(Regex("^\\s*[-*] "), "•  ")
        val parts = line.split("**")
        parts.forEachIndexed { k, p -> if (k % 2 == 1) withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(p) } else append(p) }
        if (i < s.lines().size - 1) append("\n")
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AssistantScreen() {
    val a = agri
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val chats = remember { mutableStateListOf<JsonObject>() }
    val messages = remember { mutableStateListOf<JsonObject>() }
    var chatId by remember { mutableStateOf<Int?>(null) }
    var text by remember { mutableStateOf("") }
    var image by remember { mutableStateOf<ByteArray?>(null) }
    var sending by remember { mutableStateOf(false) }
    var showList by remember { mutableStateOf(false) }
    val translated = remember { mutableStateMapOf<String, String>() }
    val showOriginal = remember { mutableStateMapOf<String, Boolean>() }
    val list = rememberLazyListState()

    suspend fun refresh() { runCatching { chats.clear(); chats.addAll(Api.get("/api/chats")["chats"].arr().map { it.obj() }) } }
    suspend fun openChat(id: Int) {
        runCatching { val c = Api.get("/api/chats/$id"); chatId = id; messages.clear(); messages.addAll(c["messages"].arr().map { it.obj() }) }
            .onFailure { AppState.toast = it.message }
    }
    fun send(q: String) {
        if (q.isBlank() && image == null) return
        sending = true
        val img = image
        messages.add(jsonOf("role" to "user", "content" to q + if (img != null) "\n[Leaf photo]" else ""))
        text = ""; image = null
        scope.launch {
            try {
                val fields = mutableMapOf("message" to q, "lang" to Session.language)
                chatId?.let { fields["chat_id"] = it.toString() }
                val r = Api.multipart("/api/chat", fields, if (img != null) "image" else null, img)
                chatId = r["chat_id"].int(); refresh(); chatId?.let { openChat(it) }
            } catch (e: ApiException) { messages.removeAt(messages.size - 1); text = q; AppState.toast = e.message }
            sending = false
        }
    }
    val voice = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        if (res.resultCode == Activity.RESULT_OK) res.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()?.let { text = (text + " " + it).trim() }
    }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) scope.launch { image = withContext(Dispatchers.IO) { loadJpeg(ctx, uri) } }
    }
    LaunchedEffect(Unit) {
        refresh()
        AppState.pendingAsk?.let { q -> AppState.pendingAsk = null; chatId = null; messages.clear(); send(q) }
    }
    LaunchedEffect(messages.size, sending) { if (messages.isNotEmpty()) list.animateScrollToItem(messages.size) }
    val lang = Tr.lang
    // older answers not in the chosen language are translated by the dashboard (cached), with a toggle back
    LaunchedEffect(messages.size, lang) {
        messages.forEachIndexed { i, m ->
            val key = "$lang|$i|$chatId"
            if (m.s("role") == "assistant" && lang != "en" && !inLang(m.s("content"), lang) && translated[key] == null) {
                runCatching { translated[key] = Api.post("/api/chat/translate", jsonOf("text" to m.s("content"), "lang" to lang)).s("text") }
            }
        }
    }

    Column(Modifier.fillMaxSize().background(a.background).imePadding()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            IconTile(Icons.Filled.Eco, Color.White, a.primaryStrong, 38.dp)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(chats.firstOrNull { it["id"].int() == chatId }?.s("title") ?: tr("AgriSense AI Assistant"), style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(tr("Farming questions only · answers in your language"), style = MaterialTheme.typography.labelSmall, color = a.muted)
            }
            IconButton(onClick = { chatId = null; messages.clear() }) { Icon(Icons.Filled.Add, tr("New conversation")) }
            IconButton(onClick = { showList = true }) { Icon(Icons.Filled.History, tr("Conversations")) }
        }
        LazyColumn(Modifier.weight(1f).fillMaxWidth(), state = list, contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (messages.isEmpty()) item { Welcome { send(it) } }
            itemsIndexed(messages) { i, m ->
                if (m.s("role") == "user") {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        Text(m.s("content").substringBefore("\n[Leaf photo"), color = Color.White,
                            modifier = Modifier.widthIn(max = 300.dp).clip(RoundedCornerShape(18.dp, 18.dp, 4.dp, 18.dp)).background(a.primaryStrong).padding(12.dp))
                    }
                } else {
                    val key = "$lang|$i|$chatId"
                    val tx = translated[key]
                    val shown = if (tx != null && showOriginal[key] != true) tx else m.s("content")
                    Row {
                        IconTile(Icons.Filled.Eco, Color.White, a.primary, 30.dp)
                        Spacer(Modifier.width(8.dp))
                        Column(Modifier.weight(1f)) {
                            Text(md(shown), modifier = Modifier.clip(RoundedCornerShape(18.dp, 18.dp, 18.dp, 4.dp)).background(a.surface)
                                .border(1.dp, a.line, RoundedCornerShape(18.dp, 18.dp, 18.dp, 4.dp)).padding(12.dp), style = MaterialTheme.typography.bodyMedium)
                            if (tx != null) TextButton(onClick = { showOriginal[key] = showOriginal[key] != true }) {
                                Icon(Icons.Filled.Translate, null, Modifier.size(16.dp)); Spacer(Modifier.width(4.dp))
                                Text(tr(if (showOriginal[key] == true) "Show translation" else "Show original"), style = MaterialTheme.typography.labelMedium)
                            }
                        }
                    }
                }
            }
            if (sending) item { Row(verticalAlignment = Alignment.CenterVertically) { CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp); Spacer(Modifier.width(8.dp)); Text(tr("Thinking…"), color = a.muted) } }
        }
        image?.let {
            Row(Modifier.padding(horizontal = 16.dp).clip(CircleShape).background(a.mint).padding(horizontal = 10.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.Image, null, Modifier.size(16.dp)); Spacer(Modifier.width(4.dp)); Text(tr("Leaf photo attached"), style = MaterialTheme.typography.labelMedium)
                IconButton(onClick = { image = null }) { Icon(Icons.Filled.Close, tr("Remove"), Modifier.size(16.dp)) }
            }
        }
        Row(Modifier.fillMaxWidth().background(a.surface).padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = { picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) }) { Icon(Icons.Filled.AddPhotoAlternate, tr("Attach a leaf photo"), tint = a.primary) }
            OutlinedTextField(text, { text = it }, Modifier.weight(1f), placeholder = { Text(tr("Type your question…")) }, maxLines = 4, shape = RoundedCornerShape(24.dp),
                colors = OutlinedTextFieldDefaults.colors(unfocusedBorderColor = a.line))
            if (text.isBlank() && image == null) IconButton(onClick = {
                runCatching {
                    voice.launch(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                        .putExtra(RecognizerIntent.EXTRA_LANGUAGE, SPEECH[Session.language] ?: "en-IN"))
                }.onFailure { AppState.toast = tr("Voice input is not available on this phone") }
            }) { Icon(Icons.Filled.Mic, tr("Speak"), tint = a.primary) }
            else IconButton(onClick = { send(text.trim()) }, enabled = !sending) { Icon(Icons.AutoMirrored.Filled.Send, tr("Send"), tint = a.primary) }
        }
    }

    if (showList) ModalBottomSheet(onDismissRequest = { showList = false }, containerColor = agri.surface) {
        Column(Modifier.padding(16.dp)) {
            Text(tr("Conversations"), style = MaterialTheme.typography.titleMedium)
            if (chats.isEmpty()) Text(tr("No conversations yet. Ask your first question."), color = a.muted, modifier = Modifier.padding(vertical = 16.dp))
            LazyColumn {
                items(chats.sortedWith(compareByDescending<JsonObject> { it["saved"].bool() }.thenByDescending { it["updated_at"].num() ?: 0.0 })) { c ->
                    val id = c["id"].int() ?: 0
                    Row(Modifier.fillMaxWidth().clickable { scope.launch { openChat(id) }; showList = false }.padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(c.s("title"), maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium)
                            Text(dateOf(c["updated_at"].num()), style = MaterialTheme.typography.labelSmall, color = a.muted)
                        }
                        IconButton(onClick = { scope.launch { runCatching { Api.patch("/api/chats/$id", jsonOf("saved" to if (c["saved"].bool()) 0 else 1)) }; refresh() } }) {
                            Icon(if (c["saved"].bool()) Icons.Filled.Bookmark else Icons.Filled.BookmarkBorder, tr("Save"), tint = a.primary)
                        }
                        IconButton(onClick = { scope.launch { runCatching { Api.delete("/api/chats/$id") }; if (chatId == id) { chatId = null; messages.clear() }; refresh() } }) {
                            Icon(Icons.Filled.Delete, tr("Delete"), tint = a.danger)
                        }
                    }
                }
            }
            Spacer(Modifier.size(24.dp))
        }
    }
}

@Composable
private fun Welcome(ask: (String) -> Unit) {
    val a = agri
    val sugg = listOf("Which crop suits my soil this season?", "My nitrogen is low - which fertiliser types should I consider?",
        "How do I tell early blight from late blight on tomato?", "How often should I irrigate wheat in winter?",
        "What does a soil pH of 8 mean for my crops?", "How can I raise my yield above the district average?")
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("${tr("Hello")} ${AppState.user?.s("name")?.substringBefore(" ") ?: ""}, ${tr("how can I help with your farm?")}", style = MaterialTheme.typography.titleLarge)
        Text(tr("Ask about crops, soil, fertiliser, diseases, irrigation or any result in this app."), color = a.muted)
        sugg.forEach { q ->
            Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(a.surface).border(1.dp, a.line, RoundedCornerShape(14.dp))
                .clickable { ask(tr(q)) }.padding(12.dp)) { Text(tr(q), style = MaterialTheme.typography.bodyMedium) }
        }
    }
}
