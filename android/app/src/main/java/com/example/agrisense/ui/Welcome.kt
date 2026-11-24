package com.example.agrisense.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import android.app.Activity
import com.example.agrisense.i18n.tr
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

const val WELCOME_MS = 3000

/** Branded welcome shown for 3 seconds every time the app is opened, before sign-in or the home screen. */
@Composable
fun WelcomeScreen(onDone: () -> Unit) {
    val logo = remember { Animatable(0.6f) }
    val fade = remember { Animatable(0f) }
    val progress = remember { Animatable(0f) }
    val view = LocalView.current
    DisposableEffect(Unit) {  // white status-bar icons on the green screen; put the theme's choice back afterwards
        val ctl = (view.context as? Activity)?.window?.let { WindowCompat.getInsetsController(it, view) }
        val before = ctl?.isAppearanceLightStatusBars to ctl?.isAppearanceLightNavigationBars
        ctl?.isAppearanceLightStatusBars = false; ctl?.isAppearanceLightNavigationBars = false
        onDispose { before.first?.let { ctl?.isAppearanceLightStatusBars = it }; before.second?.let { ctl?.isAppearanceLightNavigationBars = it } }
    }
    LaunchedEffect(Unit) {
        launch { logo.animateTo(1f, tween(700, easing = FastOutSlowInEasing)) }
        launch { fade.animateTo(1f, tween(900)) }
        launch { progress.animateTo(1f, tween(WELCOME_MS, easing = LinearEasing)) }
        delay(WELCOME_MS.toLong())
        onDone()
    }
    Box(
        Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color(0xFF2B8352), Color(0xFF1E6B42)))),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
            modifier = Modifier.padding(horizontal = 32.dp)) {
            Box(Modifier.size(104.dp).scale(logo.value).clip(RoundedCornerShape(30.dp)).background(Color.White.copy(alpha = .16f)),
                contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.Eco, null, tint = Color.White, modifier = Modifier.size(60.dp))
            }
            Spacer(Modifier.height(24.dp))
            Column(Modifier.alpha(fade.value), horizontalAlignment = Alignment.CenterHorizontally) {
                Text("AgriSense AI", color = Color.White, style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(6.dp))
                Text(tr("Smart Farming Intelligence"), color = Color.White.copy(alpha = .85f), style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(10.dp))
                Text(tr("Crop, fertiliser, yield and leaf-disease help in one place"), color = Color.White.copy(alpha = .7f),
                    style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center)
            }
        }
        Column(Modifier.align(Alignment.BottomCenter).navigationBarsPadding().padding(start = 64.dp, end = 64.dp, bottom = 48.dp),
            horizontalAlignment = Alignment.CenterHorizontally) {
            LinearProgressIndicator(progress = { progress.value }, modifier = Modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(2.dp)),
                color = Color.White, trackColor = Color.White.copy(alpha = .25f))
            Spacer(Modifier.height(10.dp))
            Text(tr("Getting things ready…"), color = Color.White.copy(alpha = .75f), style = MaterialTheme.typography.bodySmall)
        }
    }
}
