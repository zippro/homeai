package com.homeai.feature.create

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
import com.homeai.network.BoardProject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun CreateScreen() {
    val apiClient = remember { ApiClient() }
    var isLoading by remember { mutableStateOf(true) }
    var projects by remember { mutableStateOf<List<BoardProject>>(emptyList()) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        runCatching {
            withContext(Dispatchers.IO) {
                apiClient.fetchUserBoard("android_user_demo")
            }
        }.onSuccess { board ->
            projects = board.projects
        }.onFailure {
            errorMessage = it.message ?: "Failed to load board"
        }
        isLoading = false
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Your Board")

        when {
            isLoading -> CircularProgressIndicator()
            errorMessage != null -> Text("Error: $errorMessage")
            projects.isEmpty() -> Text("No projects yet.")
            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(projects) { project ->
                    BoardCard(project = project)
                }
            }
        }
    }
}

@Composable
private fun BoardCard(project: BoardProject) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text("Project: ${project.projectId}")
            Text("Style: ${project.lastStyleId ?: "N/A"}")
            Text("Generations: ${project.generationCount}")
            Text("Status: ${project.lastStatus ?: "unknown"}")
        }
    }
}
