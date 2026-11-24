package com.example.agrisense.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import android.app.Activity
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.example.agrisense.data.Session

/** Design tokens from the AgriSense mobile design system (light) and the dashboard's neutral dark theme. */
@Immutable
data class Agri(
    val primary: Color, val primaryStrong: Color, val primaryDark: Color, val ink: Color, val muted: Color,
    val background: Color, val surface: Color, val mint: Color, val mint2: Color, val line: Color,
    val sky: Color, val skyBg: Color, val warn: Color, val warnBg: Color, val danger: Color, val dangerBg: Color,
    val isDark: Boolean,
)

val LightAgri = Agri(
    primary = Color(0xFF2E8B57), primaryStrong = Color(0xFF2B8352), primaryDark = Color(0xFF236B44),
    ink = Color(0xFF24352B), muted = Color(0xFF5F6E66), background = Color(0xFFF7FAF8), surface = Color.White,
    mint = Color(0xFFF1F8F2), mint2 = Color(0xFFE2F2E8), line = Color(0xFFE5ECE6),
    sky = Color(0xFF2F6EA8), skyBg = Color(0xFFE6F0FA), warn = Color(0xFF6D5214), warnBg = Color(0xFFFBF2DC),
    danger = Color(0xFFB83C3C), dangerBg = Color(0xFFFDECEB), isDark = false,
)
val DarkAgri = Agri(
    primary = Color(0xFF3AA76B), primaryStrong = Color(0xFF2E8B57), primaryDark = Color(0xFF86D6A5),
    ink = Color(0xFFECECEE), muted = Color(0xFFA1A1AA), background = Color(0xFF0B0B0D), surface = Color(0xFF151517),
    mint = Color(0xFF1E1E21), mint2 = Color(0xFF26262B), line = Color(0xFF2E2E33),
    sky = Color(0xFF9CC8EE), skyBg = Color(0xFF1C2D3D), warn = Color(0xFFEFCF7F), warnBg = Color(0xFF3A2F12),
    danger = Color(0xFFF2A3A3), dangerBg = Color(0xFF3A1E1E), isDark = true,
)

val LocalAgri = staticCompositionLocalOf { LightAgri }
val agri: Agri @Composable get() = LocalAgri.current

private val type = Typography(
    headlineMedium = TextStyle(fontSize = 26.sp, lineHeight = 34.sp, fontWeight = FontWeight.Bold),
    headlineSmall = TextStyle(fontSize = 22.sp, lineHeight = 30.sp, fontWeight = FontWeight.Bold),
    titleLarge = TextStyle(fontSize = 20.sp, lineHeight = 28.sp, fontWeight = FontWeight.SemiBold),
    titleMedium = TextStyle(fontSize = 17.sp, lineHeight = 24.sp, fontWeight = FontWeight.SemiBold),
    titleSmall = TextStyle(fontSize = 15.sp, lineHeight = 22.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontSize = 13.sp, lineHeight = 18.sp),
    labelLarge = TextStyle(fontSize = 14.sp, lineHeight = 20.sp, fontWeight = FontWeight.SemiBold),
    labelMedium = TextStyle(fontSize = 12.sp, lineHeight = 16.sp, fontWeight = FontWeight.SemiBold),
    labelSmall = TextStyle(fontSize = 11.sp, lineHeight = 14.sp, fontWeight = FontWeight.Medium),
)

@Composable
fun AgriTheme(content: @Composable () -> Unit) {
    val dark = when (Session.theme) { "dark" -> true; "light" -> false; else -> isSystemInDarkTheme() }
    val a = if (dark) DarkAgri else LightAgri
    val scheme = if (dark) darkColorScheme(
        primary = a.primary, onPrimary = Color.White, background = a.background, onBackground = a.ink,
        surface = a.surface, onSurface = a.ink, surfaceVariant = a.mint, onSurfaceVariant = a.muted, outline = a.line,
        secondaryContainer = a.mint2, onSecondaryContainer = a.primaryDark, error = a.danger,
        // dialogs, sheets and menus use these; Material's defaults are lilac
        surfaceContainerLowest = a.surface, surfaceContainerLow = a.surface, surfaceContainer = a.surface,
        surfaceContainerHigh = a.surface, surfaceContainerHighest = a.surface, surfaceTint = Color.Transparent,
    ) else lightColorScheme(
        primary = a.primaryStrong, onPrimary = Color.White, background = a.background, onBackground = a.ink,
        surface = a.surface, onSurface = a.ink, surfaceVariant = a.mint, onSurfaceVariant = a.muted, outline = a.line,
        secondaryContainer = a.mint2, onSecondaryContainer = a.primaryDark, error = a.danger,
        // dialogs, sheets and menus use these; Material's defaults are lilac
        surfaceContainerLowest = a.surface, surfaceContainerLow = a.surface, surfaceContainer = a.surface,
        surfaceContainerHigh = a.surface, surfaceContainerHighest = a.surface, surfaceTint = Color.Transparent,
    )
    val view = LocalView.current
    if (!view.isInEditMode) SideEffect {
        // status/navigation bar icons must flip with the theme or they vanish on the dark background
        (view.context as? Activity)?.window?.let { w ->
            WindowCompat.getInsetsController(w, view).apply { isAppearanceLightStatusBars = !dark; isAppearanceLightNavigationBars = !dark }
        }
    }
    CompositionLocalProvider(LocalAgri provides a) {
        MaterialTheme(colorScheme = scheme, typography = type, content = content)
    }
}
