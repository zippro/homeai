package com.homeai.feature.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.homeai.network.ExperimentAssignment
import com.homeai.network.PlanConfig
import com.homeai.ui.SessionStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun ProfileScreen() {
    val apiClient = remember { SessionStore.apiClient }
    val currentUserId = SessionStore.userId
    var isLoading by remember { mutableStateOf(true) }
    var userIdInput by remember(currentUserId) { mutableStateOf(currentUserId) }
    var credits by remember { mutableIntStateOf(0) }
    var planId by remember { mutableStateOf("free") }
    var status by remember { mutableStateOf("inactive") }
    var nextResetAt by remember { mutableStateOf<String?>(null) }
    var catalog by remember { mutableStateOf<List<PlanConfig>>(emptyList()) }
    var experiments by remember { mutableStateOf<List<ExperimentAssignment>>(emptyList()) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(currentUserId) {
        isLoading = true
        runCatching {
            withContext(Dispatchers.IO) {
                apiClient.fetchSessionBootstrap(userId = currentUserId)
            }
        }.onSuccess { bootstrap ->
            credits = bootstrap.profile.credits.balance
            planId = bootstrap.profile.effectivePlan.planId
            status = bootstrap.profile.entitlement.status
            nextResetAt = bootstrap.profile.nextCreditResetAt
            catalog = bootstrap.catalog
            experiments = bootstrap.experiments
        }.onFailure {
            errorMessage = it.message ?: "Failed to load profile"
        }
        isLoading = false
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("My Profile")
        OutlinedTextField(
            value = userIdInput,
            onValueChange = { userIdInput = it },
            label = { Text("Shared User ID") }
        )
        Button(onClick = { SessionStore.updateUserId(userIdInput) }) {
            Text("Use This User")
        }
        when {
            isLoading -> CircularProgressIndicator()
            errorMessage != null -> Text("Error: $errorMessage")
            else -> {
                Text("User: $currentUserId")
                Text("Credits: $credits")
                Text("Plan: $planId")
                Text("Status: $status")
                nextResetAt?.let { Text("Next reset: $it") }
                if (catalog.isNotEmpty()) {
                    Text("Plans")
                    catalog.forEach { plan ->
                        val price = plan.monthlyPriceUsd?.let { String.format("$%.2f", it) } ?: "-"
                        Text("• ${plan.displayName} (${plan.planId}) - $price")
                    }
                }
                if (experiments.isNotEmpty()) {
                    Text("Active Experiments")
                    experiments.forEach { assignment ->
                        Text("• ${assignment.experimentId} -> ${assignment.variantId}")
                    }
                }
            }
        }
    }
}
