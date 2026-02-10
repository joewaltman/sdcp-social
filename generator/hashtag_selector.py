"""Intelligent hashtag selection for social media posts."""

from typing import Optional

# Core SDCP branded hashtags - always include some of these
CORE_HASHTAGS = [
    "#SanDiegoCustomPainting",
    "#SDCustomPainting",
    "#SanDiegoPainter",
    "#SanDiegoPainters",
    "#PaintersSanDiego",
    "#SDPainting",
    "#HomePainterSanDiego",
]

# Location-specific hashtags
LOCATION_HASHTAGS = {
    "la jolla": ["#LaJollaHomes", "#LaJolla", "#LaJollaCA"],
    "del mar": ["#DelMarHomes", "#DelMar", "#DelMarCA"],
    "encinitas": ["#EncinitasHomes", "#Encinitas", "#EncinitasCA"],
    "rancho santa fe": ["#RanchoSantaFe", "#RanchoSantaFeHomes", "#RSF"],
    "carlsbad": ["#CarlsbadHomes", "#Carlsbad", "#CarlsbadCA"],
    "san diego": ["#SanDiegoHomes", "#SanDiegoRealEstate", "#SanDiegoHomeImprovement"],
    "coronado": ["#CoronadoHomes", "#Coronado", "#CoronadoCA"],
    "point loma": ["#PointLoma", "#PointLomaHomes"],
    "pacific beach": ["#PacificBeach", "#PBHomes"],
    "mission hills": ["#MissionHills", "#MissionHillsSD"],
}

# Service-specific hashtags
SERVICE_HASHTAGS = {
    "interior": ["#InteriorPaintingSD", "#InteriorPainting", "#InteriorDesign"],
    "exterior": ["#ExteriorPaintingSD", "#ExteriorPainting", "#CurbAppeal"],
    "cabinet": ["#CabinetPainting", "#CabinetRefinishing", "#KitchenMakeover"],
    "kitchen": ["#KitchenPainting", "#KitchenMakeover", "#KitchenDesign"],
    "bathroom": ["#BathroomPainting", "#BathroomMakeover"],
    "bedroom": ["#BedroomPainting", "#BedroomMakeover"],
    "living room": ["#LivingRoomPainting", "#LivingRoomMakeover"],
    "trim": ["#TrimPainting", "#TrimWork", "#Millwork"],
    "stucco": ["#StuccoPainting", "#StuccoRepair"],
    "deck": ["#DeckStaining", "#DeckRefinishing"],
}

# Transformation hashtags for before/after posts
TRANSFORMATION_HASHTAGS = [
    "#BeforeAndAfter",
    "#HomeTransformation",
    "#PaintingTransformation",
    "#HomeMakeover",
    "#TransformationTuesday",
]

# General home improvement hashtags
GENERAL_HASHTAGS = [
    "#HomeImprovement",
    "#HouseGoals",
    "#HomeRenovation",
    "#PaintingContractor",
    "#ProfessionalPainter",
    "#HomeDesign",
    "#SanDiegoDesigner",
    "#HomeUpgrade",
    "#FreshPaint",
    "#PaintLife",
]


def select_hashtags(
    location: Optional[str] = None,
    project_type: Optional[str] = None,
    is_transformation: bool = False,
    max_hashtags: int = 20,
) -> list[str]:
    """Select appropriate hashtags based on project details.

    Args:
        location: Project location (e.g., "La Jolla")
        project_type: Type of work (e.g., "interior painting")
        is_transformation: Whether this is a before/after post
        max_hashtags: Maximum number of hashtags to return

    Returns:
        List of hashtags (including the # symbol)
    """
    selected: list[str] = []

    # Always include some core branded hashtags (3-5)
    selected.extend(CORE_HASHTAGS[:4])

    # Add location-specific hashtags
    if location:
        location_lower = location.lower()
        for loc_key, loc_tags in LOCATION_HASHTAGS.items():
            if loc_key in location_lower:
                selected.extend(loc_tags[:2])
                break
        else:
            # Default to San Diego if no specific match
            selected.extend(LOCATION_HASHTAGS["san diego"][:2])

    # Add service-specific hashtags
    if project_type:
        type_lower = project_type.lower()
        for service_key, service_tags in SERVICE_HASHTAGS.items():
            if service_key in type_lower:
                selected.extend(service_tags[:2])

    # Add transformation hashtags if applicable
    if is_transformation:
        selected.extend(TRANSFORMATION_HASHTAGS[:2])

    # Fill remaining slots with general hashtags
    remaining = max_hashtags - len(selected)
    if remaining > 0:
        for tag in GENERAL_HASHTAGS:
            if tag not in selected:
                selected.append(tag)
                remaining -= 1
                if remaining <= 0:
                    break

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for tag in selected:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)

    return unique[:max_hashtags]
