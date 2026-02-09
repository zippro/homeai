package com.homeai.network

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URLEncoder
import java.net.URL

class ApiClient(private val baseUrl: String = "http://10.0.2.2:8000") {
    private var accessToken: String? = null

    fun ensureSession(userId: String, platform: String = "android") {
        if (!accessToken.isNullOrBlank()) {
            try {
                val endpoint = URL("$baseUrl/v1/auth/me")
                val me = JSONObject(requestRaw("GET", endpoint))
                if (me.optString("user_id") == userId) {
                    return
                }
                accessToken = null
            } catch (_: Exception) {
                accessToken = null
            }
        }

        val endpoint = URL("$baseUrl/v1/auth/login-dev")
        val body = JSONObject()
            .put("user_id", userId)
            .put("platform", platform)
            .put("ttl_hours", 24 * 30)
            .toString()
        val raw = requestRaw("POST", endpoint, body)
        val json = JSONObject(raw)
        accessToken = json.optString("access_token").ifBlank { null }
        if (accessToken.isNullOrBlank()) {
            throw IllegalStateException("login failed: missing access token")
        }
    }

    fun createRenderJob(payload: RenderJobCreateRequest): RenderJobResponse {
        val renderUserId = payload.userId ?: "homeai_demo_user"
        ensureSession(renderUserId)
        val endpoint = URL("$baseUrl/v1/ai/render-jobs")
        val body = JSONObject()
            .put("user_id", payload.userId)
            .put("platform", payload.platform)
            .put("project_id", payload.projectId)
            .put("image_url", payload.imageUrl)
            .put("style_id", payload.styleId)
            .put("operation", payload.operation.name)
            .put("tier", payload.tier.name)
            .put("target_parts", payload.targetParts)
            .toString()

        val raw = requestRaw("POST", endpoint, body)
        return parseRenderJobResponse(raw)
    }

    fun fetchRenderJob(jobId: String): RenderJobResponse {
        val endpoint = URL("$baseUrl/v1/ai/render-jobs/$jobId")
        val raw = requestRaw("GET", endpoint)
        return parseRenderJobResponse(raw)
    }

    fun fetchUserBoard(userId: String, limit: Int = 30): UserBoardResponse {
        ensureSession(userId)
        val endpoint = URL("$baseUrl/v1/projects/board/$userId?limit=$limit")
        val raw = requestRaw("GET", endpoint)
        return parseUserBoardJson(JSONObject(raw))
    }

    fun fetchDiscoverFeed(userId: String, tab: String? = null): DiscoverFeedResponse {
        ensureSession(userId)
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
        ensureSession(userId)
        val endpoint = URL("$baseUrl/v1/credits/balance/$userId")
        val raw = requestRaw("GET", endpoint)
        val json = JSONObject(raw)
        return CreditBalanceResponse(
            userId = json.optString("user_id"),
            balance = json.optInt("balance"),
        )
    }

    fun fetchEntitlement(userId: String): SubscriptionEntitlement {
        ensureSession(userId)
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

    fun fetchProfileOverview(userId: String): ProfileOverviewResponse {
        ensureSession(userId)
        val endpoint = URL("$baseUrl/v1/profile/overview/$userId")
        val raw = requestRaw("GET", endpoint)
        return parseProfileOverviewJson(JSONObject(raw))
    }

    fun fetchSubscriptionCatalog(): List<PlanConfig> {
        val endpoint = URL("$baseUrl/v1/subscriptions/catalog")
        val raw = requestRaw("GET", endpoint)
        return parsePlanConfigList(JSONArray(raw))
    }

    fun fetchActiveExperiments(userId: String): List<ExperimentAssignment> {
        ensureSession(userId)
        val endpoint = URL("$baseUrl/v1/experiments/active/$userId?limit=50")
        val raw = requestRaw("GET", endpoint)
        val json = JSONObject(raw)
        return parseExperimentAssignments(json.optJSONArray("assignments") ?: JSONArray())
    }

    fun fetchSessionBootstrap(
        userId: String,
        boardLimit: Int = 30,
        experimentLimit: Int = 50
    ): SessionBootstrapResponse {
        ensureSession(userId)
        val endpoint = URL("$baseUrl/v1/session/bootstrap/me?board_limit=$boardLimit&experiment_limit=$experimentLimit")
        val raw = requestRaw("GET", endpoint)
        val json = JSONObject(raw)

        val meJson = json.getJSONObject("me")
        val providerDefaultsJson = json.optJSONObject("provider_defaults") ?: JSONObject()
        val fallbackChainJson = providerDefaultsJson.optJSONArray("fallback_chain") ?: JSONArray()
        val fallbackChain = mutableListOf<String>()
        for (i in 0 until fallbackChainJson.length()) {
            fallbackChain.add(fallbackChainJson.optString(i))
        }

        val variablesJson = json.optJSONObject("variables") ?: JSONObject()
        val variables = mutableMapOf<String, Any?>()
        val variableKeys = variablesJson.keys()
        while (variableKeys.hasNext()) {
            val key = variableKeys.next()
            val value = variablesJson.opt(key)
            variables[key] = if (value == JSONObject.NULL) null else value
        }

        return SessionBootstrapResponse(
            me = AuthMePayload(
                userId = meJson.optString("user_id"),
                platform = meJson.optString("platform").ifBlank { null },
                expiresAt = meJson.optString("expires_at"),
            ),
            profile = parseProfileOverviewJson(json.getJSONObject("profile")),
            board = parseUserBoardJson(json.getJSONObject("board")),
            experiments = parseExperimentAssignments(
                (json.optJSONObject("experiments") ?: JSONObject()).optJSONArray("assignments") ?: JSONArray()
            ),
            catalog = parsePlanConfigList(json.optJSONArray("catalog") ?: JSONArray()),
            variables = variables,
            providerDefaults = ProviderDefaultsPayload(
                defaultProvider = providerDefaultsJson.optString("default_provider"),
                fallbackChain = fallbackChain,
                version = providerDefaultsJson.optInt("version"),
            ),
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

    private fun parseUserBoardJson(json: JSONObject): UserBoardResponse {
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

    private fun parseProfileOverviewJson(json: JSONObject): ProfileOverviewResponse {
        val creditsJson = json.getJSONObject("credits")
        val entitlementJson = json.getJSONObject("entitlement")
        val planJson = json.getJSONObject("effective_plan")
        return ProfileOverviewResponse(
            userId = json.optString("user_id"),
            credits = CreditBalanceResponse(
                userId = creditsJson.optString("user_id"),
                balance = creditsJson.optInt("balance"),
            ),
            entitlement = SubscriptionEntitlement(
                userId = entitlementJson.optString("user_id"),
                planId = entitlementJson.optString("plan_id"),
                status = entitlementJson.optString("status"),
                source = entitlementJson.optString("source"),
                renewsAt = entitlementJson.optString("renews_at").ifBlank { null },
                expiresAt = entitlementJson.optString("expires_at").ifBlank { null },
            ),
            effectivePlan = parsePlanConfig(planJson),
            nextCreditResetAt = json.optString("next_credit_reset_at").ifBlank { null },
        )
    }

    private fun parsePlanConfigList(plansArray: JSONArray): List<PlanConfig> {
        val plans = mutableListOf<PlanConfig>()
        for (i in 0 until plansArray.length()) {
            plans.add(parsePlanConfig(plansArray.getJSONObject(i)))
        }
        return plans
    }

    private fun parsePlanConfig(planJson: JSONObject): PlanConfig {
        val featuresArray = planJson.optJSONArray("features") ?: JSONArray()
        val features = mutableListOf<String>()
        for (i in 0 until featuresArray.length()) {
            features.add(featuresArray.optString(i))
        }
        return PlanConfig(
            planId = planJson.optString("plan_id"),
            displayName = planJson.optString("display_name"),
            dailyCredits = planJson.optInt("daily_credits"),
            previewCostCredits = if (planJson.has("preview_cost_credits")) planJson.optInt("preview_cost_credits") else null,
            finalCostCredits = if (planJson.has("final_cost_credits")) planJson.optInt("final_cost_credits") else null,
            monthlyPriceUsd = if (planJson.has("monthly_price_usd")) planJson.optDouble("monthly_price_usd") else null,
            iosProductId = planJson.optString("ios_product_id").ifBlank { null },
            androidProductId = planJson.optString("android_product_id").ifBlank { null },
            webProductId = planJson.optString("web_product_id").ifBlank { null },
            features = features,
        )
    }

    private fun parseExperimentAssignments(assignmentsArray: JSONArray): List<ExperimentAssignment> {
        val assignments = mutableListOf<ExperimentAssignment>()
        for (i in 0 until assignmentsArray.length()) {
            val item = assignmentsArray.getJSONObject(i)
            assignments.add(
                ExperimentAssignment(
                    experimentId = item.optString("experiment_id"),
                    userId = item.optString("user_id"),
                    variantId = item.optString("variant_id"),
                    fromCache = item.optBoolean("from_cache"),
                    assignedAt = item.optString("assigned_at"),
                )
            )
        }
        return assignments
    }

    private fun requestRaw(method: String, endpoint: URL, body: String? = null): String {
        val connection = (endpoint.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            setRequestProperty("Accept", "application/json")
            if (body != null) {
                setRequestProperty("Content-Type", "application/json")
            }
            accessToken?.let { setRequestProperty("Authorization", "Bearer $it") }
            doInput = true
        }

        if (body != null) {
            connection.doOutput = true
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(body)
                writer.flush()
            }
        }
        val responseCode = connection.responseCode
        val stream = if (responseCode in 200..299) connection.inputStream else connection.errorStream
        val raw = BufferedReader(InputStreamReader(stream)).readText()
        if (responseCode !in 200..299) {
            if (responseCode == 401) {
                accessToken = null
            }
            throw IllegalStateException("request failed: $responseCode $raw")
        }
        return raw
    }
}
