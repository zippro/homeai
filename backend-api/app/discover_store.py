from __future__ import annotations

from app.schemas import DiscoverFeedResponse, DiscoverItem, DiscoverSection

_DEFAULT_TABS = ["Home", "Garden", "Exterior Design"]


def get_discover_feed(tab: str | None = None) -> DiscoverFeedResponse:
    sections = [
        DiscoverSection(
            key="kitchen",
            title="Kitchen",
            items=[
                DiscoverItem(
                    id="kitchen-soft-pastel",
                    title="Soft Pastel Kitchen",
                    subtitle="Light pink minimal cabinetry and clean counters",
                    category="Home",
                    before_image_url="https://picsum.photos/id/1060/1024/1024",
                    after_image_url="https://picsum.photos/id/1068/1024/1024",
                ),
                DiscoverItem(
                    id="kitchen-modern-wood",
                    title="Modern Wood Kitchen",
                    subtitle="Warm oak + matte black fixtures",
                    category="Home",
                    before_image_url="https://picsum.photos/id/1080/1024/1024",
                    after_image_url="https://picsum.photos/id/1081/1024/1024",
                ),
            ],
        ),
        DiscoverSection(
            key="living-room",
            title="Living Room",
            items=[
                DiscoverItem(
                    id="living-art-deco",
                    title="Art Deco Lounge",
                    subtitle="Bold geometry and brass accents",
                    category="Home",
                    before_image_url="https://picsum.photos/id/1038/1024/1024",
                    after_image_url="https://picsum.photos/id/1043/1024/1024",
                ),
                DiscoverItem(
                    id="living-tropical",
                    title="Tropical Retreat",
                    subtitle="Wood textures and biophilic details",
                    category="Home",
                    before_image_url="https://picsum.photos/id/1025/1024/1024",
                    after_image_url="https://picsum.photos/id/1015/1024/1024",
                ),
            ],
        ),
        DiscoverSection(
            key="garden",
            title="Garden",
            items=[
                DiscoverItem(
                    id="garden-pool-refresh",
                    title="Poolside Refresh",
                    subtitle="Greenery, deck cleanup, and colorful flowers",
                    category="Garden",
                    before_image_url="https://picsum.photos/id/100/1024/1024",
                    after_image_url="https://picsum.photos/id/101/1024/1024",
                ),
                DiscoverItem(
                    id="garden-modern-minimal",
                    title="Modern Minimal Yard",
                    subtitle="Structured pathways with low-water planting",
                    category="Garden",
                    before_image_url="https://picsum.photos/id/102/1024/1024",
                    after_image_url="https://picsum.photos/id/103/1024/1024",
                ),
            ],
        ),
        DiscoverSection(
            key="exterior",
            title="Exterior Design",
            items=[
                DiscoverItem(
                    id="exterior-cozy-holiday",
                    title="Cozy Holiday Facade",
                    subtitle="Warm lights, wreath accents, clean curb style",
                    category="Exterior Design",
                    before_image_url="https://picsum.photos/id/104/1024/1024",
                    after_image_url="https://picsum.photos/id/105/1024/1024",
                ),
                DiscoverItem(
                    id="exterior-scandi",
                    title="Scandi Exterior",
                    subtitle="Neutral palette with timber and matte black trims",
                    category="Exterior Design",
                    before_image_url="https://picsum.photos/id/106/1024/1024",
                    after_image_url="https://picsum.photos/id/107/1024/1024",
                ),
            ],
        ),
    ]

    normalized_tab = (tab or "").strip().lower()
    if normalized_tab:
        filtered_sections = []
        for section in sections:
            filtered_items = [item for item in section.items if item.category.lower() == normalized_tab]
            if filtered_items:
                filtered_sections.append(DiscoverSection(key=section.key, title=section.title, items=filtered_items))
        sections = filtered_sections

    return DiscoverFeedResponse(tabs=list(_DEFAULT_TABS), sections=sections)
