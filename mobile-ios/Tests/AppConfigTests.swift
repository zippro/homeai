import XCTest
@testable import HomeAI

final class AppConfigTests: XCTestCase {
    func testDefaultAPIBaseURLExists() {
        let url = AppConfig.apiBaseURL
        XCTAssertFalse(url.absoluteString.isEmpty)
        XCTAssertNotNil(url.scheme)
        XCTAssertNotNil(url.host)
    }
}
