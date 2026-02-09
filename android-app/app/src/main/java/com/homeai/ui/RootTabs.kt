package com.homeai.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.homeai.feature.create.CreateScreen
import com.homeai.feature.discover.DiscoverScreen
import com.homeai.feature.profile.ProfileScreen
import com.homeai.feature.tools.ToolsScreen
import com.homeai.network.ApiClient

object SessionStore {
    private const val defaultUserId = "homeai_demo_user"
    val apiClient: ApiClient = ApiClient()
    var userId by mutableStateOf(defaultUserId)

    fun updateUserId(raw: String) {
        val trimmed = raw.trim()
        userId = if (trimmed.isBlank()) defaultUserId else trimmed
    }
}

private val tabs = listOf("Tools", "Create", "Discover", "My Profile")

@Composable
fun RootTabs() {
    var selectedIndex by remember { mutableStateOf(0) }

    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEachIndexed { index, title ->
                    NavigationBarItem(
                        selected = selectedIndex == index,
                        onClick = { selectedIndex = index },
                        icon = { },
                        label = { Text(title) }
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding)) {
            when (selectedIndex) {
                0 -> ToolsScreen()
                1 -> CreateScreen()
                2 -> DiscoverScreen()
                else -> ProfileScreen()
            }
        }
    }
}
