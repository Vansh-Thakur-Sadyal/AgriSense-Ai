package com.example.agrisense.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Agriculture
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.agrisense.data.Api
import com.example.agrisense.data.Session
import com.example.agrisense.i18n.tr
import com.example.agrisense.ui.assistant.AssistantScreen
import com.example.agrisense.ui.auth.AuthFlow
import com.example.agrisense.ui.auth.LanguageScreen
import com.example.agrisense.ui.farms.FarmDetailScreen
import com.example.agrisense.ui.farms.FarmFormScreen
import com.example.agrisense.ui.farms.FarmsScreen
import com.example.agrisense.ui.home.HomeScreen
import com.example.agrisense.ui.more.HistoryScreen
import com.example.agrisense.ui.more.PredictionDetailScreen
import com.example.agrisense.ui.more.ReportsScreen
import com.example.agrisense.ui.more.SettingsScreen
import com.example.agrisense.ui.more.SoilScreen
import com.example.agrisense.ui.more.WeatherScreen
import com.example.agrisense.ui.predict.CropScreen
import com.example.agrisense.ui.predict.FertiliserScreen
import com.example.agrisense.ui.home.PredictHub
import com.example.agrisense.ui.predict.YieldScreen
import com.example.agrisense.ui.scan.ScanScreen
import com.example.agrisense.ui.theme.agri

@Composable
fun AppRoot() {
    LaunchedEffect(Unit) { Api.onUnauthorized = { AppState.signOut() } }
    // 3-second welcome on every launch; saveable so turning the phone does not show it again
    var welcomed by androidx.compose.runtime.saveable.rememberSaveable { androidx.compose.runtime.mutableStateOf(false) }
    if (!welcomed) { WelcomeScreen { welcomed = true }; return }
    when {
        !Session.onboarded -> LanguageScreen(onDone = { Session.finishOnboarding() })
        Session.token == null -> AuthFlow()
        else -> MainFlow()
    }
}

private data class Tab(val route: String, val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)
private val TABS = listOf(Tab("home", "Home", Icons.Filled.Home), Tab("predict", "Predict", Icons.Filled.Insights),
    Tab("scan", "Scan", Icons.Filled.CameraAlt), Tab("assistant", "AI Assistant", Icons.Filled.SmartToy), Tab("farms", "Farms", Icons.Filled.Agriculture))

@Composable
fun MainFlow() {
    val nav = rememberNavController()
    val snack = remember { SnackbarHostState() }
    val entry by nav.currentBackStackEntryAsState()
    val route = entry?.destination?.route?.substringBefore("?") ?: "home"
    LaunchedEffect(AppState.toast) { AppState.toast?.let { snack.showSnackbar(it); AppState.toast = null } }
    LaunchedEffect(Unit) {
        runCatching { AppState.user = Api.get("/api/me")["user"] as? kotlinx.serialization.json.JsonObject }
        runCatching { AppState.status = Api.get("/api/status") }
        runCatching { AppState.loadFarms() }
    }
    Scaffold(
        snackbarHost = { SnackbarHost(snack) },
        bottomBar = { if (route in TABS.map { it.route }) BottomBar(nav, route) },
        containerColor = agri.background,
    ) { pad ->
        Box(Modifier.padding(pad)) { MainNavHost(nav) }
    }
}

@Composable
private fun BottomBar(nav: NavHostController, route: String) {
    val a = agri
    Box {
        NavigationBar(containerColor = a.surface, tonalElevation = 2.dp) {
            TABS.forEach { t ->
                if (t.route == "scan") {
                    NavigationBarItem(selected = false, onClick = { go(nav, "scan") }, icon = { Box(Modifier.size(24.dp)) },
                        label = { Text(tr(t.label)) }, enabled = true)
                } else NavigationBarItem(
                    selected = route == t.route, onClick = { go(nav, t.route) },
                    icon = { Icon(t.icon, tr(t.label)) }, label = { Text(tr(t.label), maxLines = 1) },
                    colors = NavigationBarItemDefaults.colors(indicatorColor = a.mint2, selectedIconColor = a.primaryDark, selectedTextColor = a.primaryDark),
                )
            }
        }
        FloatingActionButton(onClick = { go(nav, "scan") }, containerColor = a.primaryStrong, contentColor = androidx.compose.ui.graphics.Color.White,
            shape = RoundedCornerShape(20.dp), modifier = Modifier.align(Alignment.TopCenter).offset(y = (-22).dp).size(60.dp)) {
            Icon(Icons.Filled.CameraAlt, tr("Scan a leaf"), Modifier.size(28.dp))
        }
    }
}

/** A tab always opens on its own first screen: an earlier hop (e.g. a result's "Ask the assistant") is not restored into another tab. */
private fun go(nav: NavHostController, route: String) {
    nav.popBackStack("home", inclusive = false)
    if (route != "home") nav.navigate(route) { launchSingleTop = true }
}

@Composable
private fun MainNavHost(nav: NavHostController) {
    val back: () -> Unit = { nav.popBackStack() }
    val open: (String) -> Unit = { r -> if (TABS.any { it.route == r }) go(nav, r) else nav.navigate(r) }
    NavHost(nav, startDestination = "home") {
        composable("home") { HomeScreen(open) }
        composable("predict") { PredictHub(open) }
        composable("scan") { ScanScreen(back, open) }
        composable("assistant") { AssistantScreen() }
        composable("farms") { FarmsScreen(open) }
        composable("crop?auto={auto}", listOf(navArgument("auto") { type = NavType.BoolType; defaultValue = false })) {
            CropScreen(it.arguments?.getBoolean("auto") == true, back, open)
        }
        composable("yield?auto={auto}", listOf(navArgument("auto") { type = NavType.BoolType; defaultValue = false })) {
            YieldScreen(it.arguments?.getBoolean("auto") == true, back, open)
        }
        composable("fertiliser?auto={auto}", listOf(navArgument("auto") { type = NavType.BoolType; defaultValue = false })) {
            FertiliserScreen(it.arguments?.getBoolean("auto") == true, back, open)
        }
        composable("weather") { WeatherScreen(back) }
        composable("soil") { SoilScreen(back) }
        composable("history") { HistoryScreen(back, open) }
        composable("prediction/{id}", listOf(navArgument("id") { type = NavType.IntType })) { PredictionDetailScreen(it.arguments?.getInt("id") ?: 0, back, open) }
        composable("reports") { ReportsScreen(back) }
        composable("settings") { SettingsScreen(back) }
        composable("farm/{id}", listOf(navArgument("id") { type = NavType.IntType })) { FarmDetailScreen(it.arguments?.getInt("id") ?: 0, back, open) }
        composable("farmForm?id={id}", listOf(navArgument("id") { type = NavType.IntType; defaultValue = 0 })) { FarmFormScreen(it.arguments?.getInt("id") ?: 0, back) }
    }
}
