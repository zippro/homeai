import SwiftUI

@MainActor
final class CreateViewModel: ObservableObject {
    @Published var isLoading: Bool = false
    @Published var projects: [BoardProject] = []
    @Published var errorMessage: String?

    private let client: APIClient
    private let userId: String

    init(client: APIClient, userId: String = "ios_user_demo") {
        self.client = client
        self.userId = userId
    }

    func loadBoard() async {
        isLoading = true
        errorMessage = nil
        do {
            let board = try await client.fetchUserBoard(userId: userId)
            projects = board.projects
        } catch {
            errorMessage = "Failed to load your board."
        }
        isLoading = false
    }
}

struct CreateHomeView: View {
    @StateObject private var viewModel = CreateViewModel(
        client: APIClient(baseURL: URL(string: "http://localhost:8000")!)
    )

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading {
                    ProgressView("Loading board...")
                } else if let errorMessage = viewModel.errorMessage {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                } else if viewModel.projects.isEmpty {
                    Text("No projects yet. Generate from Tools to see your board.")
                        .foregroundStyle(.secondary)
                        .padding()
                } else {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(viewModel.projects) { project in
                                VStack(alignment: .leading, spacing: 8) {
                                    ZStack {
                                        RoundedRectangle(cornerRadius: 20)
                                            .fill(Color(.systemGray5))
                                            .frame(height: 220)

                                        if let imageURL = project.lastOutputURL ?? project.coverImageURL,
                                           let url = URL(string: imageURL) {
                                            AsyncImage(url: url) { phase in
                                                switch phase {
                                                case .empty:
                                                    ProgressView()
                                                case .success(let image):
                                                    image
                                                        .resizable()
                                                        .scaledToFill()
                                                case .failure:
                                                    Image(systemName: "photo")
                                                        .font(.largeTitle)
                                                        .foregroundStyle(.secondary)
                                                @unknown default:
                                                    EmptyView()
                                                }
                                            }
                                            .frame(height: 220)
                                            .clipped()
                                            .clipShape(RoundedRectangle(cornerRadius: 20))
                                        }
                                    }

                                    Text(project.lastStyleId ?? "Untitled Style")
                                        .font(.title3)
                                        .fontWeight(.bold)
                                    Text("Project: \(project.projectId)")
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                    Text("Generations: \(project.generationCount)")
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                                .padding()
                                .background(Color(.systemGray6))
                                .clipShape(RoundedRectangle(cornerRadius: 24))
                            }
                        }
                        .padding()
                    }
                }
            }
            .navigationTitle("Create")
            .task {
                await viewModel.loadBoard()
            }
        }
    }
}
