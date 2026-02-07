package com.homeai.network

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URLEncoder
import java.net.URL

class ApiClient(private val baseUrl: String = "http://10.0.2.2:8000") {

    fun createRenderJob(payload: RenderJobCreateRequest): RenderJobResponse {
        val endpoint = URL("$baseUrl/v1/ai/render-jobs")
        val connection = (endpoint.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            setRequestProperty("Content-Type", "application/json")
            doOutput = true
        }

        val body = JSONObject()
            .put("user_id", payload.userId)
            .put("project_id", payload.projectId)
            .put("image_url", payload.imageUrl)
            .put("style_id", payload.styleId)
            .put("operation", payload.operation.name)
            .put("tier", payload.tier.name)
            .put("target_parts", payload.targetParts)

        connection.outputStream.use { output ->
            output.write(body.toString().toByteArray())
        }

        val responseCode = connection.responseCode
        val stream = if (responseCode in 200..299) connection.inputStream else connection.errorStream
        val raw = BufferedReader(InputStreamReader(stream)).readText()

        if (responseCode !in 200..299) {
            throw IllegalStateException("createRenderJob failed: $responseCode $raw")
        }

        return parseRenderJobResponse(raw)
    }

    fun fetchRenderJob(jobId: String): RenderJobResponse {
        val endpoint = URL("$baseUrl/v1/ai/render-jobs/$jobId")
        val connection = (endpoint.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
        }

        val responseCode = connection.responseCode
        val stream = if (responseCode in 200..299) connection.inputStream else connection.errorStream
        val raw = BufferedReader(InputStreamReader(stream)).readText()

        if (responseCode !in 200..299) {
            throw IllegalStateException("fetchRenderJob failed: $responseCode $raw")
        }

        return parseRenderJobResponse(raw)
    }

    fun fetchUserBoard(userId: String, limit: Int = 30): UserBoardResponse {
        val endpoint = URL("$baseUrl/v1/projects/board/$userId?limit=$limit")
        val raw = requestRaw("GET", endpoint)
        val json = JSONObject(raw)
        val projectsArray = json.optJSONArray("projects") ?: JSONArray()
        val projects = mutableListOf<BoardProject>()
        for (i in 0 until projectsArray.length()) {
            val item = projectsArray.getJSONObject(i)
            projects.add(
                BoardProject(
                    projectId = item.optString("project_id"),
                    coverImageUrl = item.optString("cover_image_url").ifBlank { null },
                    generationCount = item.optInt("generation_count"),
                    lastStyleId = item.optString("last_style_id").ifBlank { null },
                    lastStatus = item.optString("last_status").ifBlank { null },
                    lastOutputUrl = item.optString("last_output_url").ifBlank { null },
                    lastUpdatedAt = item.optString("last_updated_at").ifBlank { null },
                )
            )
        }
        return UserBoardResponse(
            userId = json.optString("user_id"),
            projects = projects,
        )
    }

    fun fetchDiscoverFeed(tab: String? = null): DiscoverFeedResponse {
        val encodedTab = tab?.takeIf { it.isNotBlank() }?.let { URLEncoder.encode(it, "UTF-8") }
        val suffix = if (encodedTab != null) "?tab=$encodedTab" else ""
        val endpoint = URL("$baseUrl/v1/discover/feed$suffix")
        val raw = requestRaw("GET", endpoint)
        val json = JSONObject(raw)

        val tabsArray = json.optJSONArray("tabs") ?: JSONArray()
        val tabs = mutableListOf<String>()
        for (i in 0 until tabsArray.length()) {
            tabs.add(tabsArray.optString(i))
        }

        val sectionsArray = json.optJSONArray("sections") ?: JSONArray()
        val sections = mutableListOf<DiscoverSection>()
        for (s in 0 until sectionsArray.length()) {
            val sectionJson = sectionsArray.getJSONObject(s)
            val itemsJson = sectionJson.optJSONArray("items") ?: JSONArray()
            val items = mutableListOf<DiscoverItem>()
            for (i in 0 until itemsJson.length()) {
                val itemJson = itemsJson.getJSONObject(i)
                items.add(
                    DiscoverItem(
                        id = itemJson.optString("id"),
                        title = itemJson.optString("title"),
                        subtitle = itemJson.optString("subtitle"),
                        category = itemJson.optString("category"),
                        beforeImageUrl = itemJson.optString("before_image_url"),
                        afterImageUrl = itemJson.optString("after_image_url"),
                    )
                )
            }
            sections.add(
                DiscoverSection(
                    key = sectionJson.optString("key"),
                    title = sectionJson.optString("title"),
                    items = items,
                )
            )
        }

        return DiscoverFeedResponse(tabs = tabs, sections = sections)
    }

    fun fetchCreditBalance(userId: String): CreditBalanceResponse {
        val endpoint = URL("$baseUrl/v1/credits/balance/$userId")
        val raw = requestRaw("GET", endpoint)
        val json = JSONObject(raw)
        return CreditBalanceResponse(
            userId = json.optString("user_id"),
            balance = json.optInt("balance"),
        )
    }

    fun fetchEntitlement(userId: String): SubscriptionEntitlement {
        val endpoint = URL("$baseUrl/v1/subscriptions/entitlements/$userId")
        val raw = requestRaw("GET", endpoint)
        val json = JSONObject(raw)
        return SubscriptionEntitlement(
            userId = json.optString("user_id"),
            planId = json.optString("plan_id"),
            status = json.optString("status"),
            source = json.optString("source"),
            renewsAt = json.optString("renews_at").ifBlank { null },
            expiresAt = json.optString("expires_at").ifBlank { null },
        )
    }

    private fun parseRenderJobResponse(raw: String): RenderJobResponse {
        val json = JSONObject(raw)
        return RenderJobResponse(
            id = json.getString("id"),
            status = json.getString("status"),
            provider = json.getString("provider"),
            providerModel = json.getString("provider_model"),
            outputUrl = if (json.isNull("output_url")) null else json.getString("output_url"),
            errorCode = if (json.isNull("error_code")) null else json.getString("error_code")
        )
    }

    private fun requestRaw(method: String, endpoint: URL): String {
        val connection = (endpoint.openConnection() as HttpURLConnection).apply {
            requestMethod = method
        }
        val responseCode = connection.responseCode
        val stream = if (responseCode in 200..299) connection.inputStream else connection.errorStream
        val raw = BufferedReader(InputStreamReader(stream)).readText()
        if (responseCode !in 200..299) {
            throw IllegalStateException("request failed: $responseCode $raw")
        }
        return raw
    }
}
