import SwiftUI

@MainActor
final class ProfileViewModel: ObservableObject {
    @Published var isLoading: Bool = false
    @Published var balance: Int = 0
    @Published var planId: String = "free"
    @Published var status: String = "inactive"
    @Published var renewsAt: String?
    @Published var catalog: [Plan] = []
    @Published var experiments: [ExperimentAssignment] = []
    @Published var errorMessage: String?

    private let session: AppSession

    init(session: AppSession) {
        self.session = session
    }

    func loadProfile() async {
        isLoading = true
        errorMessage = nil
        do {
            let userId = session.userId
            try await session.client.ensureSession(userId: userId)
            let bootstrap = try await session.client.fetchSessionBootstrap()
            balance = bootstrap.profile.credits.balance
            planId = bootstrap.profile.effectivePlan.planId
            status = bootstrap.profile.entitlement.status
            renewsAt = bootstrap.profile.entitlement.renewsAt
            catalog = bootstrap.catalog
            experiments = bootstrap.experiments.assignments
        } catch {
            errorMessage = "Failed to load profile."
        }
        isLoading = false
    }
}

struct ProfileHomeView: View {
    @ObservedObject var session: AppSession
    @StateObject private var viewModel: ProfileViewModel
    @State private var userIdInput: String

    init(session: AppSession) {
        self.session = session
        _viewModel = StateObject(wrappedValue: ProfileViewModel(session: session))
        _userIdInput = State(initialValue: session.userId)
    }

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
                        Section("Account") {
                            TextField("User ID", text: $userIdInput)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                            Button("Use This User") {
                                let trimmed = userIdInput.trimmingCharacters(in: .whitespacesAndNewlines)
                                session.updateUserId(trimmed)
                                userIdInput = session.userId
                                Task {
                                    await viewModel.loadProfile()
                                }
                            }
                        }

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

                        if !viewModel.catalog.isEmpty {
                            Section("Plans Catalog") {
                                ForEach(viewModel.catalog, id: \.planId) { plan in
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(plan.displayName)
                                            .font(.headline)
                                        Text("ID: \(plan.planId)")
                                            .font(.footnote)
                                        Text("Credits/day: \(plan.dailyCredits)")
                                            .font(.footnote)
                                        if let monthlyPrice = plan.monthlyPriceUSD {
                                            Text(String(format: "Price: $%.2f / month", monthlyPrice))
                                                .font(.footnote)
                                        }
                                    }
                                }
                            }
                        }

                        if !viewModel.experiments.isEmpty {
                            Section("Active Experiments") {
                                ForEach(viewModel.experiments) { assignment in
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(assignment.experimentId)
                                            .font(.headline)
                                        Text("Variant: \(assignment.variantId)")
                                            .font(.footnote)
                                        Text(assignment.fromCache ? "source: cached" : "source: new assignment")
                                            .font(.footnote)
                                    }
                                }
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
            .task(id: session.userId) {
                await viewModel.loadProfile()
            }
        }
    }
}
