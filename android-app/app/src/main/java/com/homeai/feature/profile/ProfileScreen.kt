package com.homeai.feature.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
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
import com.homeai.network.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope

@Composable
fun ProfileScreen() {
    val apiClient = remember { ApiClient() }
    var isLoading by remember { mutableStateOf(true) }
    var credits by remember { mutableIntStateOf(0) }
    var planId by remember { mutableStateOf("free") }
    var status by remember { mutableStateOf("inactive") }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        runCatching {
            coroutineScope {
                val creditsDeferred = async(Dispatchers.IO) {
                    apiClient.fetchCreditBalance("android_user_demo")
                }
                val entitlementDeferred = async(Dispatchers.IO) {
                    apiClient.fetchEntitlement("android_user_demo")
                }
                creditsDeferred.await() to entitlementDeferred.await()
            }
        }.onSuccess { (creditRes, entitlementRes) ->
            credits = creditRes.balance
            planId = entitlementRes.planId
            status = entitlementRes.status
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
        when {
            isLoading -> CircularProgressIndicator()
            errorMessage != null -> Text("Error: $errorMessage")
            else -> {
                Text("Credits: $credits")
                Text("Plan: $planId")
                Text("Status: $status")
            }
        }
    }
}
