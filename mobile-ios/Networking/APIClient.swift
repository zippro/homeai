import Foundation

enum APIError: Error {
    case requestFailed
    case decodeFailed
    case encodeFailed
    case unauthorized
}

enum RenderOperation: String, CaseIterable, Codable {
    case restyle
    case replace
    case remove
    case repaint
}

enum RenderTier: String, Codable {
    case preview
    case final
}

enum ImagePart: String, Codable {
    case fullRoom = "full_room"
    case walls
    case floor
    case furniture
    case decor
}

enum RenderStatus: String, Codable {
    case queued
    case inProgress = "in_progress"
    case completed
    case failed
    case canceled
}

struct RenderJobCreateRequest: Encodable {
    let userId: String?
    let platform: String?
    let projectId: String
    let imageURL: String
    let styleId: String
    let operation: RenderOperation
    let tier: RenderTier
    let targetParts: [ImagePart]

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case platform
        case projectId = "project_id"
        case imageURL = "image_url"
        case styleId = "style_id"
        case operation
        case tier
        case targetParts = "target_parts"
    }
}

struct RenderJobResponse: Decodable {
    let id: String
    let status: RenderStatus
    let provider: String
    let providerModel: String
    let outputURL: String?
    let errorCode: String?

    enum CodingKeys: String, CodingKey {
        case id
        case status
        case provider
        case providerModel = "provider_model"
        case outputURL = "output_url"
        case errorCode = "error_code"
    }
}

struct UserBoardResponse: Decodable {
    let userId: String
    let projects: [BoardProject]

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case projects
    }
}

struct BoardProject: Decodable, Identifiable {
    let projectId: String
    let coverImageURL: String?
    let generationCount: Int
    let lastJobId: String?
    let lastStyleId: String?
    let lastStatus: RenderStatus?
    let lastOutputURL: String?
    let lastUpdatedAt: String?

    var id: String { projectId }

    enum CodingKeys: String, CodingKey {
        case projectId = "project_id"
        case coverImageURL = "cover_image_url"
        case generationCount = "generation_count"
        case lastJobId = "last_job_id"
        case lastStyleId = "last_style_id"
        case lastStatus = "last_status"
        case lastOutputURL = "last_output_url"
        case lastUpdatedAt = "last_updated_at"
    }
}

struct DiscoverFeedResponse: Decodable {
    let tabs: [String]
    let sections: [DiscoverSection]
}

struct DiscoverSection: Decodable, Identifiable {
    let key: String
    let title: String
    let items: [DiscoverItem]

    var id: String { key }
}

struct DiscoverItem: Decodable, Identifiable {
    let id: String
    let title: String
    let subtitle: String
    let category: String
    let beforeImageURL: String
    let afterImageURL: String

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case subtitle
        case category
        case beforeImageURL = "before_image_url"
        case afterImageURL = "after_image_url"
    }
}

struct CreditBalanceResponse: Decodable {
    let userId: String
    let balance: Int

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case balance
    }
}

struct SubscriptionEntitlement: Decodable {
    let userId: String
    let planId: String
    let status: String
    let source: String
    let productId: String?
    let renewsAt: String?
    let expiresAt: String?

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case planId = "plan_id"
        case status
        case source
        case productId = "product_id"
        case renewsAt = "renews_at"
        case expiresAt = "expires_at"
    }
}

struct ProfileOverviewResponse: Decodable {
    let userId: String
    let credits: CreditBalanceResponse
    let entitlement: SubscriptionEntitlement
    let effectivePlan: Plan
    let nextCreditResetAt: String?

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case credits
        case entitlement
        case effectivePlan = "effective_plan"
        case nextCreditResetAt = "next_credit_reset_at"
    }
}

struct ExperimentAssignment: Decodable, Identifiable {
    let experimentId: String
    let userId: String
    let variantId: String
    let fromCache: Bool
    let assignedAt: String

    var id: String { "\(experimentId):\(userId)" }

    enum CodingKeys: String, CodingKey {
        case experimentId = "experiment_id"
        case userId = "user_id"
        case variantId = "variant_id"
        case fromCache = "from_cache"
        case assignedAt = "assigned_at"
    }
}

struct ActiveExperimentAssignmentsPayload: Decodable {
    let userId: String
    let assignments: [ExperimentAssignment]

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case assignments
    }
}

struct SessionBootstrapPayload: Decodable {
    let me: AuthMePayload
    let profile: ProfileOverviewResponse
    let board: UserBoardResponse
    let experiments: ActiveExperimentAssignmentsPayload
    let catalog: [Plan]
    let variables: [String: CodableValue]
    let providerDefaults: ProviderDefaults

    enum CodingKeys: String, CodingKey {
        case me
        case profile
        case board
        case experiments
        case catalog
        case variables
        case providerDefaults = "provider_defaults"
    }
}

struct DevLoginRequest: Encodable {
    let userId: String
    let platform: String
    let ttlHours: Int

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case platform
        case ttlHours = "ttl_hours"
    }
}

struct AuthSessionPayload: Decodable {
    let accessToken: String
    let tokenType: String
    let userId: String
    let expiresAt: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case userId = "user_id"
        case expiresAt = "expires_at"
    }
}

struct AuthMePayload: Decodable {
    let userId: String
    let platform: String?
    let expiresAt: String

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case platform
        case expiresAt = "expires_at"
    }
}

final class APIClient {
    private let baseURL: URL
    private let session: URLSession
    private var sessionToken: String?

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func ensureSession(userId: String, platform: String = "ios") async throws {
        if sessionToken != nil {
            do {
                let endpoint = baseURL.appendingPathComponent("v1/auth/me")
                let request = URLRequest(url: endpoint)
                let me = try await send(request, responseType: AuthMePayload.self)
                if me.userId == userId {
                    return
                }
                sessionToken = nil
            } catch {
                sessionToken = nil
            }
        }
        let endpoint = baseURL.appendingPathComponent("v1/auth/login-dev")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let payload = DevLoginRequest(userId: userId, platform: platform, ttlHours: 24 * 30)
        do {
            request.httpBody = try JSONEncoder().encode(payload)
        } catch {
            throw APIError.encodeFailed
        }
        let auth = try await send(request, responseType: AuthSessionPayload.self)
        sessionToken = auth.accessToken
    }

    func fetchBootstrapConfig() async throws -> BootstrapConfig {
        let endpoint = baseURL.appendingPathComponent("v1/config/bootstrap")
        let request = URLRequest(url: endpoint)
        return try await send(request, responseType: BootstrapConfig.self)
    }

    func createRenderJob(payload: RenderJobCreateRequest) async throws -> RenderJobResponse {
        let endpoint = baseURL.appendingPathComponent("v1/ai/render-jobs")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        do {
            request.httpBody = try JSONEncoder().encode(payload)
        } catch {
            throw APIError.encodeFailed
        }

        return try await send(request, responseType: RenderJobResponse.self)
    }

    func fetchRenderJob(jobId: String) async throws -> RenderJobResponse {
        let endpoint = baseURL.appendingPathComponent("v1/ai/render-jobs/\(jobId)")
        let request = URLRequest(url: endpoint)
        return try await send(request, responseType: RenderJobResponse.self)
    }

    func fetchUserBoard(userId: String, limit: Int = 30) async throws -> UserBoardResponse {
        var components = URLComponents(url: baseURL.appendingPathComponent("v1/projects/board/\(userId)"), resolvingAgainstBaseURL: false)
        components?.queryItems = [URLQueryItem(name: "limit", value: String(limit))]
        guard let endpoint = components?.url else {
            throw APIError.requestFailed
        }
        let request = URLRequest(url: endpoint)
        return try await send(request, responseType: UserBoardResponse.self)
    }

    func fetchDiscoverFeed(tab: String? = nil) async throws -> DiscoverFeedResponse {
        var components = URLComponents(url: baseURL.appendingPathComponent("v1/discover/feed"), resolvingAgainstBaseURL: false)
        if let tab, !tab.isEmpty {
            components?.queryItems = [URLQueryItem(name: "tab", value: tab)]
        }
        guard let endpoint = components?.url else {
            throw APIError.requestFailed
        }
        let request = URLRequest(url: endpoint)
        return try await send(request, responseType: DiscoverFeedResponse.self)
    }

    func fetchCreditBalance(userId: String) async throws -> CreditBalanceResponse {
        let endpoint = baseURL.appendingPathComponent("v1/credits/balance/\(userId)")
        let request = URLRequest(url: endpoint)
        return try await send(request, responseType: CreditBalanceResponse.self)
    }

    func fetchEntitlement(userId: String) async throws -> SubscriptionEntitlement {
        let endpoint = baseURL.appendingPathComponent("v1/subscriptions/entitlements/\(userId)")
        let request = URLRequest(url: endpoint)
        return try await send(request, responseType: SubscriptionEntitlement.self)
    }

    func fetchProfileOverview(userId: String) async throws -> ProfileOverviewResponse {
        let endpoint = baseURL.appendingPathComponent("v1/profile/overview/\(userId)")
        let request = URLRequest(url: endpoint)
        return try await send(request, responseType: ProfileOverviewResponse.self)
    }

    func fetchSubscriptionCatalog() async throws -> [Plan] {
        let endpoint = baseURL.appendingPathComponent("v1/subscriptions/catalog")
        let request = URLRequest(url: endpoint)
        return try await send(request, responseType: [Plan].self)
    }

    func fetchActiveExperiments(userId: String) async throws -> [ExperimentAssignment] {
        let endpoint = baseURL.appendingPathComponent("v1/experiments/active/\(userId)")
        let request = URLRequest(url: endpoint)
        let payload = try await send(request, responseType: ActiveExperimentAssignmentsPayload.self)
        return payload.assignments
    }

    func fetchSessionBootstrap(
        boardLimit: Int = 30,
        experimentLimit: Int = 50
    ) async throws -> SessionBootstrapPayload {
        var components = URLComponents(
            url: baseURL.appendingPathComponent("v1/session/bootstrap/me"),
            resolvingAgainstBaseURL: false
        )
        components?.queryItems = [
            URLQueryItem(name: "board_limit", value: String(boardLimit)),
            URLQueryItem(name: "experiment_limit", value: String(experimentLimit)),
        ]
        guard let endpoint = components?.url else {
            throw APIError.requestFailed
        }
        let request = URLRequest(url: endpoint)
        return try await send(request, responseType: SessionBootstrapPayload.self)
    }

    private func send<T: Decodable>(_ request: URLRequest, responseType: T.Type) async throws -> T {
        var authorizedRequest = request
        if let token = sessionToken {
            authorizedRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: authorizedRequest)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            if let http = response as? HTTPURLResponse, http.statusCode == 401 {
                sessionToken = nil
                throw APIError.unauthorized
            }
            throw APIError.requestFailed
        }

        do {
            return try JSONDecoder().decode(responseType, from: data)
        } catch {
            throw APIError.decodeFailed
        }
    }
}

struct BootstrapConfig: Decodable {
    let activePlans: [Plan]
    let variables: [String: CodableValue]
    let providerDefaults: ProviderDefaults

    enum CodingKeys: String, CodingKey {
        case activePlans = "active_plans"
        case variables
        case providerDefaults = "provider_defaults"
    }
}

struct Plan: Decodable {
    let planId: String
    let displayName: String
    let isActive: Bool
    let dailyCredits: Int
    let previewCostCredits: Int?
    let finalCostCredits: Int?
    let monthlyPriceUSD: Double?
    let iosProductId: String?
    let androidProductId: String?
    let webProductId: String?
    let features: [String]?

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case displayName = "display_name"
        case isActive = "is_active"
        case dailyCredits = "daily_credits"
        case previewCostCredits = "preview_cost_credits"
        case finalCostCredits = "final_cost_credits"
        case monthlyPriceUSD = "monthly_price_usd"
        case iosProductId = "ios_product_id"
        case androidProductId = "android_product_id"
        case webProductId = "web_product_id"
        case features
    }
}

struct ProviderDefaults: Decodable {
    let defaultProvider: String
    let fallbackChain: [String]
    let version: Int

    enum CodingKeys: String, CodingKey {
        case defaultProvider = "default_provider"
        case fallbackChain = "fallback_chain"
        case version
    }
}

enum CodableValue: Decodable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let value = try? container.decode(Bool.self) {
            self = .bool(value)
            return
        }
        if let value = try? container.decode(Int.self) {
            self = .int(value)
            return
        }
        if let value = try? container.decode(Double.self) {
            self = .double(value)
            return
        }
        if let value = try? container.decode(String.self) {
            self = .string(value)
            return
        }
        throw APIError.decodeFailed
    }
}
