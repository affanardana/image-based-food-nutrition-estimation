"""Domain exceptions — business rule violations and error conditions.

All domain exceptions inherit from DomainError. Infrastructure exceptions
must never leak into the domain layer; they should be caught and translated
into these domain errors at the infrastructure boundary.
"""


class DomainError(Exception):
    """Base class for all domain-level errors."""


class FoodNotFoundError(DomainError):
    """Raised when a food item or canonical food cannot be found."""


class UnsupportedFoodError(DomainError):
    """Raised when a food is not supported by the current provider."""


class NutritionUnavailableError(DomainError):
    """Raised when nutrition data cannot be resolved for a given food."""


class MealNotFoundError(DomainError):
    """Raised when a meal with the given ID does not exist."""


class InvalidMealStateError(DomainError):
    """Raised when a meal state transition is invalid."""
