package com.example.agrisense

import android.app.Application
import com.example.agrisense.data.Session
import com.example.agrisense.i18n.Tr
import org.osmdroid.config.Configuration

class AgriApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Session.init(this)
        Tr.init(this, Session.language)
        // OSM serves a "blocked" tile to placeholder ids such as com.example.*, so identify the app properly
        Configuration.getInstance().userAgentValue =
            "AgriSense-AI/${BuildConfig.VERSION_NAME} (Android; +${BuildConfig.API_BASE})"
    }
}
