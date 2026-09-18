"""InMemoryMealRepository — development-only meal repository backed by a dict."""

import threading

from app.domain.entities.meal import Meal
from app.domain.interfaces.meal_repository import MealRepository


class InMemoryMealRepository(MealRepository):
    """Stores meals in process memory.

    Intended for development and the mock/dummy provider setup. Meals are
    lost on restart. Replaced by a database-backed repository in the
    persistence phase.
    """

    def __init__(self) -> None:
        self._meals: dict[str, Meal] = {}
        self._lock = threading.Lock()

    def save(self, meal: Meal) -> None:
        with self._lock:
            self._meals[meal.meal_id] = meal

    def get_by_id(self, meal_id: str) -> Meal | None:
        with self._lock:
            return self._meals.get(meal_id)

    def list_recent(self, limit: int = 20, offset: int = 0) -> list[Meal]:
        with self._lock:
            meals = sorted(
                self._meals.values(),
                key=lambda meal: meal.created_at,
                reverse=True,
            )
            return meals[offset : offset + limit]

    def delete(self, meal_id: str) -> None:
        with self._lock:
            self._meals.pop(meal_id, None)

    def exists(self, meal_id: str) -> bool:
        with self._lock:
            return meal_id in self._meals
