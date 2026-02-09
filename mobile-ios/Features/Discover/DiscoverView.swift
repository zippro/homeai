import SwiftUI

@MainActor
final class DiscoverViewModel: ObservableObject {
    @Published var isLoading: Bool = false
    @Published var tabs: [String] = []
    @Published var selectedTab: String = ""
    @Published var sections: [DiscoverSection] = []
    @Published var errorMessage: String?

    private let session: AppSession

    init(session: AppSession) {
        self.session = session
    }

    func loadFeed() async {
        isLoading = true
        errorMessage = nil
        do {
            try await session.client.ensureSession(userId: session.userId)
            let feed = try await session.client.fetchDiscoverFeed()
            tabs = feed.tabs
            selectedTab = feed.tabs.first ?? ""
            sections = feed.sections
        } catch {
            errorMessage = "Failed to load discover feed."
        }
        isLoading = false
    }

    func loadFeed(tab: String) async {
        isLoading = true
        errorMessage = nil
        do {
            try await session.client.ensureSession(userId: session.userId)
            let feed = try await session.client.fetchDiscoverFeed(tab: tab)
            tabs = feed.tabs
            selectedTab = tab
            sections = feed.sections
        } catch {
            errorMessage = "Failed to load discover feed."
        }
        isLoading = false
    }
}

struct DiscoverHomeView: View {
    @ObservedObject var session: AppSession
    @StateObject private var viewModel: DiscoverViewModel

    init(session: AppSession) {
        self.session = session
        _viewModel = StateObject(wrappedValue: DiscoverViewModel(session: session))
    }

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading {
                    ProgressView("Loading discover...")
                } else if let errorMessage = viewModel.errorMessage {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                } else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {
                            if !viewModel.tabs.isEmpty {
                                Picker("Category", selection: $viewModel.selectedTab) {
                                    ForEach(viewModel.tabs, id: \.self) { tab in
                                        Text(tab).tag(tab)
                                    }
                                }
                                .pickerStyle(.segmented)
                                .onChange(of: viewModel.selectedTab) { newValue in
                                    guard !newValue.isEmpty else { return }
                                    Task {
                                        await viewModel.loadFeed(tab: newValue)
                                    }
                                }
                            }

                            ForEach(viewModel.sections) { section in
                                VStack(alignment: .leading, spacing: 10) {
                                    Text(section.title)
                                        .font(.title3)
                                        .fontWeight(.bold)

                                    ScrollView(.horizontal, showsIndicators: false) {
                                        HStack(spacing: 12) {
                                            ForEach(section.items) { item in
                                                VStack(alignment: .leading, spacing: 6) {
                                                    if let url = URL(string: item.afterImageURL) {
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
                                                                    .foregroundStyle(.secondary)
                                                            @unknown default:
                                                                EmptyView()
                                                            }
                                                        }
                                                        .frame(width: 180, height: 180)
                                                        .clipped()
                                                        .clipShape(RoundedRectangle(cornerRadius: 16))
                                                    }

                                                    Text(item.title)
                                                        .font(.headline)
                                                    Text(item.subtitle)
                                                        .font(.footnote)
                                                        .foregroundStyle(.secondary)
                                                        .lineLimit(2)
                                                }
                                                .frame(width: 180, alignment: .leading)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        .padding()
                    }
                }
            }
            .navigationTitle("Discover")
            .task(id: session.userId) {
                await viewModel.loadFeed()
            }
        }
    }
}
