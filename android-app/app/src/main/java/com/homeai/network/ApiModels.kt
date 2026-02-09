package com.homeai.network

enum class RenderOperation {
    restyle,
    replace,
    remove,
    repaint
}

enum class RenderTier {
    preview,
    final
}

data class RenderJobCreateRequest(
    val userId: String?,
    val platform: String?,
    val projectId: String,
    val imageUrl: String,
    val styleId: String,
    val operation: RenderOperation,
    val tier: RenderTier,
    val targetParts: List<String>
)

data class RenderJobResponse(
    val id: String,
    val status: String,
    val provider: String,
    val providerModel: String,
    val outputUrl: String?,
    val errorCode: String?
)

data class BoardProject(
    val projectId: String,
    val coverImageUrl: String?,
    val generationCount: Int,
    val lastStyleId: String?,
    val lastStatus: String?,
    val lastOutputUrl: String?,
    val lastUpdatedAt: String?
)

data class UserBoardResponse(
    val userId: String,
    val projects: List<BoardProject>
)

data class DiscoverItem(
    val id: String,
    val title: String,
    val subtitle: String,
    val category: String,
    val beforeImageUrl: String,
    val afterImageUrl: String
)

data class DiscoverSection(
    val key: String,
    val title: String,
    val items: List<DiscoverItem>
)

data class DiscoverFeedResponse(
    val tabs: List<String>,
    val sections: List<DiscoverSection>
)

data class CreditBalanceResponse(
    val userId: String,
    val balance: Int
)

data class SubscriptionEntitlement(
    val userId: String,
    val planId: String,
    val status: String,
    val source: String,
    val renewsAt: String?,
    val expiresAt: String?
)

data class PlanConfig(
    val planId: String,
    val displayName: String,
    val dailyCredits: Int,
    val previewCostCredits: Int? = null,
    val finalCostCredits: Int? = null,
    val monthlyPriceUsd: Double? = null,
    val iosProductId: String? = null,
    val androidProductId: String? = null,
    val webProductId: String? = null,
    val features: List<String> = emptyList()
)

data class ProfileOverviewResponse(
    val userId: String,
    val credits: CreditBalanceResponse,
    val entitlement: SubscriptionEntitlement,
    val effectivePlan: PlanConfig,
    val nextCreditResetAt: String?
)

data class ExperimentAssignment(
    val experimentId: String,
    val userId: String,
    val variantId: String,
    val fromCache: Boolean,
    val assignedAt: String
)

data class AuthMePayload(
    val userId: String,
    val platform: String?,
    val expiresAt: String
)

data class ProviderDefaultsPayload(
    val defaultProvider: String,
    val fallbackChain: List<String>,
    val version: Int
)

data class SessionBootstrapResponse(
    val me: AuthMePayload,
    val profile: ProfileOverviewResponse,
    val board: UserBoardResponse,
    val experiments: List<ExperimentAssignment>,
    val catalog: List<PlanConfig>,
    val variables: Map<String, Any?>,
    val providerDefaults: ProviderDefaultsPayload
)
