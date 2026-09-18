"""Verify the real SAM 3 + YOLO depth pipeline on a single image.

Development tool, not part of the API. Runs the production vision
providers end-to-end and prints the paper-methodology summary
(Eqs 2-7): mask-area normalization, depth normalization, calibrated
height, volume, weight, and nutrition per detected food group.

Reuses the same infrastructure components and application services as
the web app — nothing here duplicates pipeline logic.

Usage (from the backend directory):

    uv run python scripts/verify_real_pipeline.py path/to/meal.jpg
    uv run python scripts/verify_real_pipeline.py path/to/meal.jpg --show

Model paths default to VISION_SAM_MODEL_PATH / VISION_DEPTH_MODEL_PATH
(same environment variables the API reads).
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.application.services.measurement_estimator import MeasurementEstimator
from app.application.services.nutrition_resolver import NutritionResolver
from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.segment import Segment
from app.domain.entities.vision_class import VisionClass
from app.domain.values.nutrition_values import NutritionProfile
from app.infrastructure.catalog.yaml_canonical_food_catalog import (
    YamlCanonicalFoodCatalog,
)
from app.infrastructure.nutrition.manual_nutrition_provider import (
    ManualNutritionProvider,
)
from app.infrastructure.storage.local_storage_provider import (
    LocalStorageProvider,
)
from app.infrastructure.vision.depth import YOLODepthEstimator
from app.infrastructure.vision.sam3_segmentation_provider import (
    SAM3SegmentationProvider,
)
from app.shared.config import Config

BASE_DIR = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments, defaulting model paths to the app's env vars."""
    defaults = Config.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="Path to the meal image to analyze")
    parser.add_argument(
        "--sam-model",
        default=defaults.vision.sam_model_path,
        help="SAM 3 checkpoint path (default: VISION_SAM_MODEL_PATH)",
    )
    parser.add_argument(
        "--depth-model",
        default=defaults.vision.depth_model_path,
        help="YOLO depth checkpoint path (default: VISION_DEPTH_MODEL_PATH)",
    )
    parser.add_argument(
        "--device",
        default=defaults.vision.device,
        help="Inference device (default: VISION_DEVICE or 'auto')",
    )
    parser.add_argument(
        "--storage",
        default=defaults.storage.base_path,
        help="Directory for saved crops (default: STORAGE_PATH or './storage')",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display the separated crop images with matplotlib",
    )
    return parser.parse_args()


def build_services(
    args: argparse.Namespace,
) -> tuple[
    SAM3SegmentationProvider,
    YamlCanonicalFoodCatalog,
    MeasurementEstimator,
    NutritionResolver,
]:
    """Wire the production providers and services for a standalone run."""
    if not args.sam_model or not args.depth_model:
        raise SystemExit(
            "Missing model paths. Pass --sam-model/--depth-model or set "
            "VISION_SAM_MODEL_PATH/VISION_DEPTH_MODEL_PATH."
        )
    catalog = YamlCanonicalFoodCatalog(
        str(BASE_DIR / "mappings" / "canonical_foods.yaml")
    )
    nutrition_provider = ManualNutritionProvider(
        str(BASE_DIR / "data" / "nutrition_database.yaml")
    )
    storage_provider = LocalStorageProvider(args.storage)
    depth_estimator = YOLODepthEstimator(
        args.depth_model,
        device=args.device,
    )
    provider = SAM3SegmentationProvider(
        sam_model_path=args.sam_model,
        depth_estimator=depth_estimator,
        storage_provider=storage_provider,
        catalog=catalog,
        device=args.device,
    )
    return (
        provider,
        catalog,
        MeasurementEstimator(),
        NutritionResolver(nutrition_provider),
    )


def group_segments(segments: list[Segment]) -> dict[str, list[Segment]]:
    """Group segments by their suggested label (reference-style aggregation)."""
    groups: dict[str, list[Segment]] = defaultdict(list)
    for segment in segments:
        label = (
            segment.suggestion.vision_class.label
            if segment.suggestion is not None
            else "unlabeled"
        )
        groups[label].append(segment)
    return dict(groups)


def print_segment_report(
    provider: SAM3SegmentationProvider,
    segments: list[Segment],
) -> None:
    """Print per-segment mask statistics (Eqs 2-3 inputs)."""
    print("=== 1. SAM 3 Segmentation + YOLO Depth ===")
    print(f"Provider : {provider.provider_name} {provider.provider_version}")
    print(f"Segments : {len(segments)}")
    print()
    for segment in segments:
        label = "?"
        if segment.suggestion is not None:
            label = f"{segment.suggestion.vision_class.label} " \
                f"(conf {segment.suggestion.confidence.value:.2f})"
        print(f"[{segment.segment_id}] suggestion={label}")
        print(f"  A_mask      = {segment.mask_area_px:,.0f} px")
        print(f"  A_norm      = {segment.normalized_area:.4f}")
        print(f"  max D_norm  = {segment.max_normalized_depth:.4f}")
        print(f"  crop saved  : {segment.crop_image_ref}")
        print()


def resolve_group_food(
    label: str,
    catalog: YamlCanonicalFoodCatalog,
) -> CanonicalFood | None:
    """Map a suggested label to its canonical food, warning when unmapped."""
    food = catalog.map_from_vision_class(VisionClass(label=label))
    if food is None:
        print(f"[{label.upper()}] no canonical food mapping — skipped")
    return food


def print_group_report(
    label: str,
    food: CanonicalFood,
    segments: list[Segment],
    estimator: MeasurementEstimator,
    resolver: NutritionResolver,
) -> NutritionProfile:
    """Print the Eq 2-7 summary for one food group, return its profile."""
    measurement = estimator.estimate(food, segments)
    profile = resolver.resolve(food, measurement)

    properties = food.physical_properties
    total_area_px = sum(segment.mask_area_px for segment in segments)
    total_area_norm = sum(segment.normalized_area for segment in segments)
    volume = (
        measurement.volume.value_cm3 if measurement.volume is not None else 0.0
    )
    weight = (
        measurement.weight.value_g if measurement.weight is not None else 0.0
    )

    print(f"[{label.upper()}]  gamma={properties.calibration_factor} "
          f"density={properties.density_g_per_cm3} g/cm3")
    print(f"- Raw Mask Area    : {total_area_px:,.0f} px")
    print(f"- Normalized Area  : {total_area_norm:.4f}")
    print(f"- Volume Est. (V)  : {volume:.2f} cm3")
    print(f"- Weight Est. (W)  : {weight:.1f} grams")
    print(f"- Total Energy     : {profile.calories_kcal:.1f} kcal")
    print(
        "- Macronutrients   : "
        f"Protein {profile.protein_g:.1f}g | "
        f"Fat {profile.fat_g:.1f}g | "
        f"Carbs {profile.carbohydrates_g:.1f}g"
    )
    print()
    return profile


def print_nutrition_report(
    groups: dict[str, list[Segment]],
    catalog: YamlCanonicalFoodCatalog,
    estimator: MeasurementEstimator,
    resolver: NutritionResolver,
) -> None:
    """Print per-group portion and nutrient results, then the meal total."""
    print("=== 2. Portion & Nutrient Estimation (Eqs 2-7) ===")
    total_calories = 0.0
    for label, segments in groups.items():
        if label == "unlabeled":
            print(f"[UNLABELED] {len(segments)} segment(s) without a "
                  "suggestion — run with suggestions enabled or label them")
            print()
            continue
        food = resolve_group_food(label, catalog)
        if food is None:
            continue
        profile = print_group_report(
            label, food, segments, estimator, resolver
        )
        total_calories += profile.calories_kcal

    print("--------------------------------------------------")
    print(f"TOTAL MEAL CALORIES: {total_calories:.1f} kcal")


def show_crops(segments: list[Segment]) -> None:
    """Render the separated crop images in a matplotlib grid."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit(
            "matplotlib is required for --show. "
            "Install the vision extras: uv sync --extra vision"
        ) from exc
    import cv2

    crops = [
        (segment.segment_id, segment.crop_image_ref)
        for segment in segments
        if segment.crop_image_ref
    ]
    if not crops:
        print("No crops to display.")
        return

    figure, axes = plt.subplots(1, len(crops), figsize=(3 * len(crops), 3))
    if len(crops) == 1:
        axes = [axes]
    for axis, (segment_id, crop_ref) in zip(axes, crops, strict=True):
        crop = cv2.imread(crop_ref)
        if crop is None:
            axis.text(0.5, 0.5, f"{segment_id}\nmissing", ha="center")
        else:
            axis.imshow(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        axis.set_title(segment_id)
        axis.axis("off")

    figure.suptitle("Separated Segmented Objects", fontsize=14)
    plt.tight_layout()
    plt.show()


def main() -> int:
    args = parse_args()
    if not Path(args.image).exists():
        raise SystemExit(f"Image not found: {args.image}")
    provider, catalog, estimator, resolver = build_services(args)

    segments = provider.segment(args.image, suggest_labels=True)
    print_segment_report(provider, segments)

    groups = group_segments(segments)
    print_nutrition_report(groups, catalog, estimator, resolver)

    if args.show:
        show_crops(segments)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
