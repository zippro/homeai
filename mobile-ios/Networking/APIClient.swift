import Foundation

enum APIError: Error {
    case requestFailed
    case decodeFailed
    case encodeFailed
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
    let projectId: String
    let imageURL: String
    let styleId: String
    let operation: RenderOperation
    let tier: RenderTier
    let targetParts: [ImagePart]

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
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

final class APIClient {
    private let baseURL: URL
    private let session: URLSession

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
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

    private func send<T: Decodable>(_ request: URLRequest, responseType: T.Type) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
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

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case displayName = "display_name"
        case isActive = "is_active"
        case dailyCredits = "daily_credits"
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
