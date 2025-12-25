package com.agahgok.transco

import android.net.Uri
import android.os.Bundle
import android.text.Html
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class MainActivity : ComponentActivity() {

    private val client = OkHttpClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        setContent { MaterialTheme { SimpleTranscriptUI() } }
    }

    @Composable
    private fun SimpleTranscriptUI() {
        var url by remember { mutableStateOf("") }
        var transcript by remember { mutableStateOf("") }
        var loading by remember { mutableStateOf(false) }
        var error by remember { mutableStateOf<String?>(null) }
        val scope = rememberCoroutineScope()

        Column(Modifier.fillMaxSize().padding(16.dp)) {
            OutlinedTextField(
                value = url,
                onValueChange = { url = it },
                label = { Text("YouTube linki") },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(Modifier.height(12.dp))

            Button(
                onClick = {
                    error = null
                    transcript = ""
                    val videoId = getVideoId(url)
                    if (videoId == null) {
                        error = "Geçersiz URL"
                        return@Button
                    }

                    scope.launch {
                        loading = true
                        try {
                            transcript = fetchTranscript(videoId)
                        } catch (e: Exception) {
                            error = "Failed: ${e.message}"
                        } finally {
                            loading = false
                        }
                    }
                },
                enabled = !loading,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (loading) "Yükleniyor..." else "Transkript Getir")
            }

            Spacer(Modifier.height(12.dp))

            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

            Spacer(Modifier.height(8.dp))

            Surface(tonalElevation = 2.dp, modifier = Modifier.fillMaxWidth().weight(1f)) {
                Text(
                    text = transcript.ifBlank { "Burada görünecek..." },
                    modifier = Modifier.padding(12.dp).verticalScroll(rememberScrollState())
                )
            }
        }
    }

    private fun getVideoId(youtubeUrl: String): String? {
        val uri = runCatching { Uri.parse(youtubeUrl) }.getOrNull() ?: return null
        val host = (uri.host ?: "").lowercase()

        return when {
            host.contains("youtube.com") -> uri.getQueryParameter("v")
            host.contains("youtu.be") -> uri.pathSegments.firstOrNull()
            else -> null
        }
    }

    private suspend fun fetchTranscript(videoId: String): String {
        return withContext(Dispatchers.IO) {
            val py = Python.getInstance()
            val module = py.getModule("transcript_fetcher")
            // Reconstruct the URL for the python script (which expects a URL)
            val videoUrl = "https://www.youtube.com/watch?v=$videoId"
            module.callAttr("get_transcript_text", videoUrl).toString()
        }
    }


}
