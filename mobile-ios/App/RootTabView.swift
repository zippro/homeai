import SwiftUI

@MainActor
final class AppSession: ObservableObject {
    private static let userIdKey = "homeai.session.user_id"
    private static let defaultUserId = "homeai_demo_user"

    @Published var userId: String {
        didSet {
            UserDefaults.standard.set(userId, forKey: Self.userIdKey)
        }
    }

    let client: APIClient

    init(client: APIClient = APIClient(baseURL: AppConfig.apiBaseURL)) {
        self.client = client
        let saved = UserDefaults.standard.string(forKey: Self.userIdKey)
        let normalized = (saved?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false)
            ? saved!
            : Self.defaultUserId
        self.userId = normalized
    }

    func updateUserId(_ value: String) {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        userId = trimmed.isEmpty ? Self.defaultUserId : trimmed
    }
}

struct RootTabView: View {
    @StateObject private var session = AppSession()

    var body: some View {
        TabView {
            ToolsHomeView(session: session)
                .tabItem {
                    Image(systemName: "wand.and.stars")
                    Text("Tools")
                }

            CreateHomeView(session: session)
                .tabItem {
                    Image(systemName: "square.stack.3d.up")
                    Text("Create")
                }

            DiscoverHomeView(session: session)
                .tabItem {
                    Image(systemName: "sparkles")
                    Text("Discover")
                }

            ProfileHomeView(session: session)
                .tabItem {
                    Image(systemName: "person.fill")
                    Text("My Profile")
                }
        }
    }
}
