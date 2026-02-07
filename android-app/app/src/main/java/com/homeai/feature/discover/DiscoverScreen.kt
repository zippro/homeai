package com.homeai.feature.discover

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.homeai.network.ApiClient
import com.homeai.network.DiscoverSection
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun DiscoverScreen() {
    val apiClient = remember { ApiClient() }
    var isLoading by remember { mutableStateOf(true) }
    var sections by remember { mutableStateOf<List<DiscoverSection>>(emptyList()) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        runCatching {
            withContext(Dispatchers.IO) {
                apiClient.fetchDiscoverFeed(tab = "Home")
            }
        }.onSuccess { feed ->
            sections = feed.sections
        }.onFailure {
            errorMessage = it.message ?: "Failed to load discover feed"
        }
        isLoading = false
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Discover")

        when {
            isLoading -> CircularProgressIndicator()
            errorMessage != null -> Text("Error: $errorMessage")
            sections.isEmpty() -> Text("No discover content.")
            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(sections) { section ->
                    DiscoverSectionCard(section = section)
                }
            }
        }
    }
}

@Composable
private fun DiscoverSectionCard(section: DiscoverSection) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(section.title)
            section.items.take(3).forEach { item ->
                Text("• ${item.title}")
            }
        }
    }
}
