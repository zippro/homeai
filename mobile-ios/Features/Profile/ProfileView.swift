import SwiftUI

@MainActor
final class ProfileViewModel: ObservableObject {
    @Published var isLoading: Bool = false
    @Published var balance: Int = 0
    @Published var planId: String = "free"
    @Published var status: String = "inactive"
    @Published var renewsAt: String?
    @Published var errorMessage: String?

    private let client: APIClient
    private let userId: String

    init(client: APIClient, userId: String = "ios_user_demo") {
        self.client = client
        self.userId = userId
    }

    func loadProfile() async {
        isLoading = true
        errorMessage = nil
        do {
            async let credit = client.fetchCreditBalance(userId: userId)
            async let entitlement = client.fetchEntitlement(userId: userId)
            let (creditResult, entitlementResult) = try await (credit, entitlement)

            balance = creditResult.balance
            planId = entitlementResult.planId
            status = entitlementResult.status
            renewsAt = entitlementResult.renewsAt
        } catch {
            errorMessage = "Failed to load profile."
        }
        isLoading = false
    }
}

struct ProfileHomeView: View {
    @StateObject private var viewModel = ProfileViewModel(
        client: APIClient(baseURL: URL(string: "http://localhost:8000")!)
    )

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading {
                    ProgressView("Loading profile...")
                } else if let errorMessage = viewModel.errorMessage {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                } else {
                    Form {
                        Section("Credits") {
                            Text("Balance: \(viewModel.balance)")
                        }

                        Section("Subscription") {
                            Text("Plan: \(viewModel.planId.uppercased())")
                            Text("Status: \(viewModel.status)")
                            if let renewsAt = viewModel.renewsAt {
                                Text("Renews at: \(renewsAt)")
                                    .font(.footnote)
                            }
                        }

                        Section("Actions") {
                            Button("Refresh") {
                                Task {
                                    await viewModel.loadProfile()
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("My Profile")
            .task {
                await viewModel.loadProfile()
            }
        }
    }
}
