"""YamlCanonicalFoodCatalog — loads the canonical food registry from YAML."""

from pathlib import Path
from typing import Any

import yaml

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.physical_property import PhysicalProperty
from app.domain.entities.vision_class import VisionClass
from app.domain.interfaces.canonical_food_catalog import CanonicalFoodCatalog


def _relevance(food: CanonicalFood, keyword: str) -> tuple[int, str]:
    """Sort key: names starting with the keyword first, then by name."""
    starts_with = 0 if food.name.lower().startswith(keyword) else 1
    return (starts_with, food.name)


class YamlCanonicalFoodCatalog(CanonicalFoodCatalog):
    """Canonical food catalog backed by a YAML configuration file.

    The file defines each canonical food, its physical properties
    (density, calibration factor), and the vision labels that map to it.
    """

    def __init__(self, config_path: str) -> None:
        raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(
                f"Invalid canonical foods config '{config_path}': "
                "expected a mapping"
            )
        foods_raw = raw.get("canonical_foods")
        if not isinstance(foods_raw, dict):
            raise ValueError(
                f"Invalid canonical foods config '{config_path}': "
                "missing 'canonical_foods' mapping"
            )
        self._foods, self._vision_mapping = self._parse(foods_raw)

    @staticmethod
    def _parse(
        foods_raw: dict[str, Any],
    ) -> tuple[dict[str, CanonicalFood], dict[str, str]]:
        foods: dict[str, CanonicalFood] = {}
        vision_mapping: dict[str, str] = {}
        for food_id, spec in foods_raw.items():
            if not isinstance(spec, dict):
                raise ValueError(
                    f"Invalid canonical food '{food_id}': expected a mapping"
                )
            props = spec.get("physical_properties")
            if props is None:
                props = {}
            if not isinstance(props, dict):
                raise ValueError(
                    f"Invalid canonical food '{food_id}': "
                    "'physical_properties' must be a mapping"
                )
            foods[food_id] = CanonicalFood(
                id=food_id,
                name=spec["name"],
                typical_weight_g=float(spec.get("typical_weight_g", 150.0)),
                physical_properties=PhysicalProperty(
                    density_g_per_cm3=props.get("density_g_per_cm3"),
                    calibration_factor=props.get("calibration_factor"),
                    volume_coefficient=props.get("volume_coefficient"),
                ),
            )
            for label in spec.get("vision_labels", []):
                vision_mapping[label] = food_id
        return foods, vision_mapping

    def map_from_vision_class(
        self,
        vision_class: VisionClass,
    ) -> CanonicalFood | None:
        canonical_id = self._vision_mapping.get(vision_class.label)
        if canonical_id is None:
            return None
        return self._foods.get(canonical_id)

    def get_by_id(self, canonical_food_id: str) -> CanonicalFood | None:
        return self._foods.get(canonical_food_id)

    def search(self, query: str, limit: int = 20) -> list[CanonicalFood]:
        keyword = query.strip().lower()
        results = [
            food
            for food in self._foods.values()
            if keyword in food.id.lower() or keyword in food.name.lower()
        ]
        results.sort(key=lambda food: _relevance(food, keyword))
        return results[:limit]

    def list_detectable_foods(self) -> list[CanonicalFood]:
        detectable_ids = set(self._vision_mapping.values())
        results = [
            food
            for food_id, food in self._foods.items()
            if food_id in detectable_ids
        ]
        results.sort(key=lambda food: food.name)
        return results
