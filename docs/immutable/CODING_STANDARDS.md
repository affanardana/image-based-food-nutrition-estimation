# Coding Standards

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 1.0  
**Status:** Immutable  
**Last Updated:** 2026-07-30

---

# Purpose

This document defines the coding conventions, architectural rules, and development standards for the repository.

Its purpose is to ensure that the codebase remains:

- Consistent
- Readable
- Maintainable
- Testable
- Extensible

These standards apply to both human contributors and AI coding agents.

---

# General Principles

The repository follows these principles:

- Clean Architecture
- SOLID
- Domain-Driven Design (DDD)
- Explicit over Implicit
- Composition over Inheritance
- Dependency Inversion
- Interface-based Design

Whenever two implementations are equally valid, choose the simpler one.

---

# Technology Stack

The current recommended stack is:

| Component | Standard |
|-----------|----------|
| Language | Python 3.12+ |
| Package Manager | uv |
| API | FastAPI |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Database | PostgreSQL |
| Testing | pytest |
| Formatting | Ruff |
| Type Checking | mypy |

Future implementations may replace technologies without changing the Domain layer.

---

# Project Structure

Recommended structure

```text
app/

├── domain/
│
├── application/
│
├── infrastructure/
│
├── presentation/
│
└── shared/
```

Each layer should have a single clear responsibility.

---

# Naming Conventions

## Files

Use

```text
snake_case.py
```

Examples

```text
meal_service.py
nutrition_provider.py
vision_mapper.py
```

Avoid

```text
MealService.py
Meal_Service.py
MEALSERVICE.py
```

---

## Classes

Use PascalCase.

Examples

```python
MealService

NutritionProvider

CanonicalFood

VisionPrediction
```

---

## Functions

Use snake_case.

Examples

```python
calculate_nutrition()

estimate_weight()

resolve_food()
```

---

## Variables

Use snake_case.

Examples

```python
meal

food_item

nutrition_profile
```

Avoid abbreviations unless universally understood.

Bad

```python
m

obj

tmp
```

Good

```python
meal

prediction

ingredient
```

---

## Constants

Use UPPER_SNAKE_CASE.

Example

```python
MAX_IMAGE_SIZE_MB = 10
```

---

## Private Members

Use a leading underscore.

```python
_load_model()

_repository
```

---

# Type Hints

Public functions should always include type annotations.

Good

```python
def calculate_weight(volume: float, density: float) -> float:
```

Avoid

```python
def calculate_weight(volume, density):
```

---

# Documentation

Every public module should contain a short module docstring.

Example

```python
"""
Nutrition calculation services.
"""
```

Public classes should also include concise docstrings.

Avoid writing comments that merely repeat the code.

Bad

```python
# Increment i
i += 1
```

Prefer code that explains itself.

---

# Function Design

Functions should have one responsibility.

Prefer

```python
calculate_volume()

calculate_weight()

calculate_nutrition()
```

Instead of

```python
calculate_everything()
```

---

# Function Length

Recommended

- under 30 lines

Acceptable

- under 50 lines

If a function exceeds this size, consider extracting smaller functions.

---

# Class Design

Classes should represent one concept.

Avoid "manager" or "utility" classes containing unrelated logic.

Bad

```text
AIManager
```

Good

```text
VisionProvider

NutritionResolver

MealService
```

---

# Dependency Rules

Allowed

```text
Presentation

↓

Application

↓

Domain

↑

Infrastructure
```

Not allowed

```text
Domain

↓

Infrastructure
```

```text
Presentation

↓

Database
```

```text
Business Logic

↓

PyTorch
```

---

# Domain Rules

Domain entities should:

- represent business concepts
- contain business rules
- avoid framework dependencies

The Domain layer must never import:

- FastAPI
- SQLAlchemy
- OpenCV
- PyTorch
- NumPy (unless mathematically essential)
- PostgreSQL drivers

---

# Application Rules

Application layer coordinates workflows.

It should not:

- access HTTP requests directly
- execute SQL
- load AI models

Instead, it should orchestrate services through interfaces.

---

# Infrastructure Rules

Infrastructure implements interfaces defined by the Domain.

Infrastructure may contain:

- AI models
- database repositories
- external APIs
- storage adapters

Infrastructure should not contain business rules.

---

# Presentation Rules

Presentation layer handles:

- HTTP
- validation
- serialization
- authentication
- request parsing

It should never perform:

- nutrition calculation
- business validation
- AI inference orchestration

---

# Interfaces

Depend on abstractions.

Bad

```python
YOLOProvider()
```

Good

```python
VisionProvider
```

Application should only know the interface.

---

# Dependency Injection

Prefer constructor injection.

Good

```python
MealService(
    nutrition_provider,
    vision_provider,
)
```

Avoid

```python
service = MealService()

service.provider = provider
```

Avoid global singletons.

---

# Error Handling

Raise domain-specific exceptions whenever possible.

Examples

```text
FoodNotFoundError

UnsupportedFoodError

NutritionUnavailableError
```

Avoid exposing low-level exceptions to upper layers.

---

# Logging

Use structured logging.

Log meaningful events.

Examples

- image uploaded
- prediction completed
- nutrition calculated
- user correction applied

Never log:

- passwords
- tokens
- secrets
- personal information

---

# Configuration

Configuration belongs outside the source code.

Use environment variables for:

- database connection
- API keys
- model paths
- storage credentials

Avoid hardcoded values.

---

# Magic Numbers

Avoid

```python
weight = volume * 0.87
```

Prefer

```python
DEFAULT_DENSITY = 0.87

weight = volume * DEFAULT_DENSITY
```

---

# Testing Standards

Prefer testing business behavior instead of implementation details.

Testing priority

1. Domain
2. Application
3. Infrastructure
4. Presentation

Every new business rule should have corresponding tests.

---

# AI Provider Standards

Every provider should implement the same interface.

Example

```text
VisionProvider

├── MockVisionProvider

├── FlorenceProvider

├── YOLOProvider

└── Future Providers
```

Upper layers should never detect which implementation is used.

---

# Nutrition Provider Standards

Every nutrition source should implement the same interface.

Examples

```text
NutritionProvider

├── PangankuProvider

├── USDAProvider

├── ManualProvider

└── Future Providers
```

The provider receives CanonicalFood.

It must never receive VisionClass.

---

# Imports

Prefer standard library first.

Example

```python
# Standard Library

from pathlib import Path

# Third-party

from fastapi import APIRouter

# Local

from app.domain.entities import Meal
```

Group imports consistently.

---

# Code Style

Prefer

- early returns
- explicit names
- immutable objects
- readable code

Avoid

- deeply nested conditions
- unnecessary inheritance
- premature optimization

Code is read far more often than it is written.

Optimize for readability first.

---

# Pull Request Checklist

Before merging code, verify:

- Architecture remains consistent.
- No dependency rule is violated.
- Public APIs are typed.
- Tests pass.
- Documentation is updated.
- Mutable documentation is synchronized.
- No immutable documentation was modified unintentionally.

---

# Immutable Policy

This document defines repository-wide coding standards.

It MUST NOT be modified automatically by AI agents.

Changes require explicit approval from the repository owner because they affect the consistency of the entire codebase.
