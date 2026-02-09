import Foundation

enum AppConfig {
    private static let fallbackAPIBaseURL = "http://localhost:8000"

    static var apiBaseURL: URL {
        if let fromEnvironment = ProcessInfo.processInfo.environment["HOMEAI_API_BASE_URL"],
           let url = URL(string: fromEnvironment),
           !fromEnvironment.isEmpty {
            return url
        }

        if let fromInfoPlist = Bundle.main.object(forInfoDictionaryKey: "APIBaseURL") as? String,
           let url = URL(string: fromInfoPlist),
           !fromInfoPlist.isEmpty {
            return url
        }

        return URL(string: fallbackAPIBaseURL)!
    }
}
