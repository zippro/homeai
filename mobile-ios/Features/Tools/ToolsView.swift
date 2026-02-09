import SwiftUI

@MainActor
final class ToolsViewModel: ObservableObject {
    @Published var imageURL: String = ""
    @Published var styleId: String = "modern_minimal"
    @Published var selectedOperation: RenderOperation = .restyle
    @Published var selectedTier: RenderTier = .preview
    @Published var isLoading: Bool = false
    @Published var lastJob: RenderJobResponse?
    @Published var errorMessage: String?

    private let session: AppSession

    init(session: AppSession) {
        self.session = session
    }

    func generate() async {
        guard !imageURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            errorMessage = "Image URL is required"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let userId = session.userId
            try await session.client.ensureSession(userId: userId)
            let createPayload = RenderJobCreateRequest(
                userId: userId,
                platform: "ios",
                projectId: "mobile_project",
                imageURL: imageURL,
                styleId: styleId,
                operation: selectedOperation,
                tier: selectedTier,
                targetParts: [.fullRoom]
            )

            let created = try await session.client.createRenderJob(payload: createPayload)
            lastJob = created

            // Poll quickly for non-terminal states.
            if created.status == .queued || created.status == .inProgress {
                for _ in 0..<8 {
                    try await Task.sleep(nanoseconds: 1_500_000_000)
                    let refreshed = try await session.client.fetchRenderJob(jobId: created.id)
                    lastJob = refreshed
                    if refreshed.status == .completed || refreshed.status == .failed || refreshed.status == .canceled {
                        break
                    }
                }
            }
        } catch {
            errorMessage = "Render request failed. Check API URL and image URL."
        }

        isLoading = false
    }
}

struct ToolsHomeView: View {
    @ObservedObject var session: AppSession
    @StateObject private var viewModel: ToolsViewModel

    init(session: AppSession) {
        self.session = session
        _viewModel = StateObject(wrappedValue: ToolsViewModel(session: session))
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Input") {
                    TextField("Image URL", text: $viewModel.imageURL)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)

                    TextField("Style ID", text: $viewModel.styleId)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                }

                Section("Options") {
                    Picker("Operation", selection: $viewModel.selectedOperation) {
                        ForEach(RenderOperation.allCases, id: \.self) { item in
                            Text(item.rawValue).tag(item)
                        }
                    }

                    Picker("Tier", selection: $viewModel.selectedTier) {
                        Text("preview").tag(RenderTier.preview)
                        Text("final").tag(RenderTier.final)
                    }
                    .pickerStyle(.segmented)
                }

                Section {
                    Button(viewModel.isLoading ? "Generating..." : "Generate") {
                        Task {
                            await viewModel.generate()
                        }
                    }
                    .disabled(viewModel.isLoading)
                }

                if let job = viewModel.lastJob {
                    Section("Result") {
                        Text("Job ID: \(job.id)")
                        Text("Status: \(job.status.rawValue)")
                        Text("Provider: \(job.provider)")
                        Text("Model: \(job.providerModel)")
                        if let outputURL = job.outputURL {
                            Text(outputURL)
                                .font(.footnote)
                                .textSelection(.enabled)
                        }
                        if let errorCode = job.errorCode {
                            Text("Error: \(errorCode)")
                                .foregroundStyle(.red)
                        }
                    }
                }

                if let errorMessage = viewModel.errorMessage {
                    Section("Error") {
                        Text(errorMessage)
                            .foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Tools")
        }
    }
}
