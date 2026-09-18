"""Meal, segment, and food item response/request schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class BoundingBoxOut(BaseModel):
    x: int
    y: int
    width: int
    height: int


class SuggestionOut(BaseModel):
    label: str
    confidence: float


class SegmentOut(BaseModel):
    id: str
    crop_url: str
    bbox: BoundingBoxOut
    suggestion: SuggestionOut | None = None


class CanonicalFoodOut(BaseModel):
    id: str
    name: str


class MeasurementOut(BaseModel):
    estimated_volume_cm3: float | None = None
    estimated_weight_g: float | None = None


class NutritionOut(BaseModel):
    calories_kcal: float
    protein_g: float
    fat_g: float
    carbohydrates_g: float
    fiber_g: float = 0.0
    sodium_mg: float = 0.0


class FoodItemOut(BaseModel):
    id: str
    canonical_food: CanonicalFoodOut | None = None
    segment_ids: list[str] = Field(default_factory=list)
    measurement: MeasurementOut | None = None
    nutrition: NutritionOut | None = None
    ingredients: list[str] = Field(default_factory=list)


class SummaryOut(BaseModel):
    total_calories_kcal: float
    total_protein_g: float
    total_fat_g: float
    total_carbohydrates_g: float
    total_fiber_g: float = 0.0
    total_sodium_mg: float = 0.0


class ImageInfoOut(BaseModel):
    width: int | None = None
    height: int | None = None


class MealData(BaseModel):
    meal_id: str
    state: str
    name: str = ""
    image_url: str | None = None
    segments: list[SegmentOut] = Field(default_factory=list)
    food_items: list[FoodItemOut] = Field(default_factory=list)
    summary: SummaryOut | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HistoryEntryOut(BaseModel):
    """One row of the meal history list."""

    meal_id: str
    state: str
    name: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    image_url: str | None = None
    total_calories_kcal: float
    food_item_count: int
    segment_count: int


class AnalyzeMealData(MealData):
    processing_time_ms: int
    image: ImageInfoOut


class SegmentLabelAssignmentIn(BaseModel):
    canonical_food_id: str
    segment_ids: list[str]


class LabelMealRequest(BaseModel):
    assignments: list[SegmentLabelAssignmentIn]
    name: str | None = None


class FoodItemCorrectionIn(BaseModel):
    id: str
    canonical_food: str | None = None
    estimated_weight_g: float | None = None
    ingredients: list[str] | None = None


class CorrectionRequest(BaseModel):
    food_items: list[FoodItemCorrectionIn] = Field(default_factory=list)
    name: str | None = None


class DiscardSegmentsRequest(BaseModel):
    segment_ids: list[str]


class DeletedData(BaseModel):
    deleted: bool
