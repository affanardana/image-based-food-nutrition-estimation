"""SQL schema for the food data and meal domains.

Food data: canonical foods, their nutrition entries, and the VisionClass
mappings that make a food detectable. Nutrition is a separate table
because one canonical food may have entries from several sources (domain
rule 5).

Meals: the persisted Meal aggregate — segments, food items, their
segment groupings, ingredients, and the user-correction audit trail.

The schema is dialect-neutral: Supabase/Postgres in production, SQLite
in tests.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

canonical_foods = Table(
    "canonical_foods",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("name", String(255), nullable=False, index=True),
    Column("image_url", Text, nullable=True),
    Column("typical_weight_g", Float, nullable=False, default=150.0),
    Column("density_g_per_cm3", Float, nullable=True),
    Column("calibration_factor", Float, nullable=True),
)

nutrition_entries = Table(
    "nutrition_entries",
    metadata,
    Column(
        "canonical_food_id",
        String(128),
        ForeignKey("canonical_foods.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("source", String(64), primary_key=True),
    Column("calories_kcal", Float, nullable=False, default=0.0),
    Column("protein_g", Float, nullable=False, default=0.0),
    Column("fat_g", Float, nullable=False, default=0.0),
    Column("carbohydrates_g", Float, nullable=False, default=0.0),
    Column("fiber_g", Float, nullable=False, default=0.0),
    Column("sodium_mg", Float, nullable=False, default=0.0),
)

vision_labels = Table(
    "vision_labels",
    metadata,
    Column("label", String(128), primary_key=True),
    Column(
        "canonical_food_id",
        String(128),
        ForeignKey("canonical_foods.id", ondelete="CASCADE"),
        nullable=False,
    ),
)

# ── Meal aggregate ─────────────────────────────────────────────────────

meals = Table(
    "meals",
    metadata,
    Column("meal_id", String(128), primary_key=True),
    Column("image_path", Text, nullable=False),
    Column("name", String(255), nullable=False, default=""),
    Column("state", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    # Meal-level totals are stored, not derived on read: the summary is
    # part of the aggregate and is what a history list shows.
    Column("total_calories_kcal", Float, nullable=False, default=0.0),
    Column("total_protein_g", Float, nullable=False, default=0.0),
    Column("total_fat_g", Float, nullable=False, default=0.0),
    Column("total_carbohydrates_g", Float, nullable=False, default=0.0),
    Column("total_fiber_g", Float, nullable=False, default=0.0),
    Column("total_sodium_mg", Float, nullable=False, default=0.0),
)

segments = Table(
    "segments",
    metadata,
    # Segment ids are only unique within a meal (seg_001, seg_002, ...),
    # so the meal id is part of the key.
    Column(
        "meal_id",
        String(128),
        ForeignKey("meals.meal_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    Column("segment_id", String(64), primary_key=True),
    Column("crop_image_ref", Text, nullable=False),
    Column("mask_area_px", Float, nullable=False),
    Column("normalized_area", Float, nullable=False),
    Column("bbox_x", Integer, nullable=False),
    Column("bbox_y", Integer, nullable=False),
    Column("bbox_width", Integer, nullable=False),
    Column("bbox_height", Integer, nullable=False),
    Column("max_normalized_depth", Float, nullable=False),
    Column("provider_name", String(128), nullable=False),
    Column("provider_version", String(64), nullable=False),
    Column("suggestion_label", String(128), nullable=True),
    Column("suggestion_confidence", Float, nullable=True),
)

food_items = Table(
    "food_items",
    metadata,
    Column("food_item_id", String(128), primary_key=True),
    Column(
        "meal_id",
        String(128),
        ForeignKey("meals.meal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    # Preserves the order the items were labeled in; without it a
    # reloaded meal could list its items in any order.
    Column("position", Integer, nullable=False, default=0),
    # CanonicalFood is stored as a snapshot rather than a reference: a
    # past meal must keep its meaning when the food catalog is re-seeded
    # or a food is renamed.
    Column("canonical_food_id", String(128), nullable=True),
    Column("canonical_food_name", String(255), nullable=True),
    Column("canonical_food_typical_weight_g", Float, nullable=True),
    Column("canonical_food_density_g_per_cm3", Float, nullable=True),
    Column("canonical_food_calibration_factor", Float, nullable=True),
    Column("correction_state", String(32), nullable=False),
    Column("area_cm2", Float, nullable=True),
    Column("volume_cm3", Float, nullable=True),
    Column("weight_g", Float, nullable=True),
    Column("calories_kcal", Float, nullable=False, default=0.0),
    Column("protein_g", Float, nullable=False, default=0.0),
    Column("fat_g", Float, nullable=False, default=0.0),
    Column("carbohydrates_g", Float, nullable=False, default=0.0),
    Column("fiber_g", Float, nullable=False, default=0.0),
    Column("sodium_mg", Float, nullable=False, default=0.0),
)

food_item_segments = Table(
    "food_item_segments",
    metadata,
    Column(
        "food_item_id",
        String(128),
        ForeignKey("food_items.food_item_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "meal_id",
        String(128),
        ForeignKey("meals.meal_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    Column("segment_id", String(64), primary_key=True),
)

food_item_ingredients = Table(
    "food_item_ingredients",
    metadata,
    Column(
        "food_item_id",
        String(128),
        ForeignKey("food_items.food_item_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("position", Integer, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("source", String(32), nullable=False),
)

food_item_corrections = Table(
    "food_item_corrections",
    metadata,
    Column("correction_id", Integer, primary_key=True, autoincrement=True),
    Column(
        "food_item_id",
        String(128),
        ForeignKey("food_items.food_item_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("field", String(64), nullable=False),
    Column("old_value", Text, nullable=False),
    Column("new_value", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
