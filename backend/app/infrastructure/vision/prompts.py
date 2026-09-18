"""Shared prompt vocabulary for semantic-segmentation vision providers."""

from app.domain.interfaces.canonical_food_catalog import CanonicalFoodCatalog

NOT_FOOD_LABEL = "not_food"


def build_prompts(catalog: CanonicalFoodCatalog) -> list[str]:
    """The prompt vocabulary: detectable food names plus 'not_food'.

    Only foods with VisionClass mappings are prompted: a catalog may
    hold thousands of foods, which no semantic predictor can handle.
    """
    return [food.name for food in catalog.list_detectable_foods()] + [
        NOT_FOOD_LABEL
    ]
