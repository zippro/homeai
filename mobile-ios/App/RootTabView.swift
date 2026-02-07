import SwiftUI

struct RootTabView: View {
    var body: some View {
        TabView {
            ToolsHomeView()
                .tabItem {
                    Image(systemName: "wand.and.stars")
                    Text("Tools")
                }

            CreateHomeView()
                .tabItem {
                    Image(systemName: "square.stack.3d.up")
                    Text("Create")
                }

            DiscoverHomeView()
                .tabItem {
                    Image(systemName: "sparkles")
                    Text("Discover")
                }

            ProfileHomeView()
                .tabItem {
                    Image(systemName: "person.fill")
                    Text("My Profile")
                }
        }
    }
}
