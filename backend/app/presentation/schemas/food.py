"""Food search schemas."""

from app.presentation.schemas.meal import CanonicalFoodOut

FoodSearchData = list[CanonicalFoodOut]
