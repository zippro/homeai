package com.homeai.feature.tools

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenu
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.homeai.network.ApiClient
import com.homeai.network.RenderJobCreateRequest
import com.homeai.network.RenderJobResponse
import com.homeai.network.RenderOperation
import com.homeai.network.RenderTier
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ToolsScreen() {
    val scope = rememberCoroutineScope()
    val apiClient = remember { ApiClient() }

    var imageUrl by remember { mutableStateOf("") }
    var styleId by remember { mutableStateOf("modern_minimal") }
    var selectedOperation by remember { mutableStateOf(RenderOperation.restyle) }
    var selectedTier by remember { mutableStateOf(RenderTier.preview) }
    var isLoading by remember { mutableStateOf(false) }
    var result by remember { mutableStateOf<RenderJobResponse?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Tools", style = MaterialTheme.typography.headlineMedium)

        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = imageUrl,
            onValueChange = { imageUrl = it },
            label = { Text("Image URL") }
        )

        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = styleId,
            onValueChange = { styleId = it },
            label = { Text("Style ID") }
        )

        OperationDropdown(
            selectedOperation = selectedOperation,
            onOperationSelected = { selectedOperation = it }
        )

        TierDropdown(
            selectedTier = selectedTier,
            onTierSelected = { selectedTier = it }
        )

        Button(
            onClick = {
                if (imageUrl.isBlank()) {
                    error = "Image URL is required"
                    return@Button
                }

                scope.launch {
                    isLoading = true
                    error = null
                    result = null

                    runCatching {
                        val created = withContext(Dispatchers.IO) {
                            apiClient.createRenderJob(
                                RenderJobCreateRequest(
                                    userId = "android_user_demo",
                                    projectId = "android_project",
                                    imageUrl = imageUrl,
                                    styleId = styleId,
                                    operation = selectedOperation,
                                    tier = selectedTier,
                                    targetParts = listOf("full_room")
                                )
                            )
                        }

                        var latest = created
                        if (latest.status == "queued" || latest.status == "in_progress") {
                            var terminalReached = false
                            repeat(8) {
                                if (terminalReached) {
                                    return@repeat
                                }
                                delay(1500)
                                latest = withContext(Dispatchers.IO) {
                                    apiClient.fetchRenderJob(latest.id)
                                }
                                if (latest.status == "completed" || latest.status == "failed" || latest.status == "canceled") {
                                    terminalReached = true
                                }
                            }
                        }
                        latest
                    }.onSuccess {
                        result = it
                    }.onFailure {
                        error = it.message ?: "Render request failed"
                    }

                    isLoading = false
                }
            },
            enabled = !isLoading,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (isLoading) "Generating..." else "Generate")
        }

        result?.let {
            Text("Job: ${it.id}")
            Text("Status: ${it.status}")
            Text("Provider: ${it.provider}")
            Text("Model: ${it.providerModel}")
            it.outputUrl?.let { url -> Text(url) }
            it.errorCode?.let { code -> Text("Error: $code") }
        }

        error?.let {
            Text(it, color = MaterialTheme.colorScheme.error)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun OperationDropdown(
    selectedOperation: RenderOperation,
    onOperationSelected: (RenderOperation) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded }
    ) {
        OutlinedTextField(
            modifier = Modifier
                .menuAnchor()
                .fillMaxWidth(),
            readOnly = true,
            value = selectedOperation.name,
            onValueChange = {},
            label = { Text("Operation") },
            trailingIcon = {
                ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded)
            }
        )

        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            RenderOperation.entries.forEach { operation ->
                DropdownMenuItem(
                    text = { Text(operation.name) },
                    onClick = {
                        onOperationSelected(operation)
                        expanded = false
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TierDropdown(
    selectedTier: RenderTier,
    onTierSelected: (RenderTier) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded }
    ) {
        OutlinedTextField(
            modifier = Modifier
                .menuAnchor()
                .fillMaxWidth(),
            readOnly = true,
            value = selectedTier.name,
            onValueChange = {},
            label = { Text("Tier") },
            trailingIcon = {
                ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded)
            }
        )

        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            RenderTier.entries.forEach { tier ->
                DropdownMenuItem(
                    text = { Text(tier.name) },
                    onClick = {
                        onTierSelected(tier)
                        expanded = false
                    }
                )
            }
        }
    }
}
