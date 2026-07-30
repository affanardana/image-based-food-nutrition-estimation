# Domain Model

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 1.0  
**Status:** Immutable  
**Last Updated:** 2026-07-30

---

# Purpose

This document defines the **business domain** of the application.

The domain model intentionally avoids implementation details such as:

- AI models
- Machine learning frameworks
- Databases
- REST APIs
- Programming languages

The domain should remain stable even when the implementation changes completely.

---

# Domain Philosophy

The application is centered around **Meals**, not AI models.

Computer vision only produces observations.

Business entities represent the application's source of truth.

```
Image

↓

Vision Prediction

↓

Business Domain

↓

Nutrition

↓

User
```

The AI model is not the domain.

The meal is.

---

# Core Domain

The central entity is **Meal**.

```
Meal
│
├── Image
├── FoodItem[]
├── NutritionSummary
└── Metadata
```

Everything in the application belongs to a Meal.

---

# Entity Overview

```
Meal
│
├── FoodItem
│      │
│      ├── VisionPrediction
│      ├── Measurement
│      ├── Ingredient[]
│      ├── NutritionProfile
│      └── UserCorrection
│
├── NutritionSummary
│
└── ImageMetadata
```

---

# Entity: Meal

Represents a single eating session.

A Meal owns all information related to one uploaded image.

## Attributes

- meal_id
- image
- food_items
- nutrition_summary
- created_at
- updated_at

## Responsibilities

- stores uploaded image
- stores detected foods
- stores nutrition summary
- stores user corrections

---

# Entity: FoodItem

Represents one food object inside a meal.

A meal may contain multiple FoodItems.

Examples:

- burger
- rice
- fried chicken
- salad

## Attributes

- food_item_id
- vision_prediction
- canonical_food
- segmentation
- measurement
- ingredients
- nutrition_profile
- correction_state

---

## Responsibilities

A FoodItem

- represents one food object
- stores AI prediction
- stores user modifications
- stores nutrition information

---

# Entity: VisionPrediction

Represents raw computer vision output.

This entity belongs to Infrastructure but is stored inside the domain for traceability.

## Attributes

- vision_class
- confidence
- bounding_box
- segmentation_mask
- provider_name
- provider_version

## Examples

```
burger

confidence

0.96
```

or

```
fried_rice

confidence

0.89
```

---

## Important Rule

VisionPrediction is NOT a nutrition category.

It is only an observation.

---

# Entity: VisionClass

Represents the class predicted by the AI model.

Examples

```
burger

pizza

fried_rice

sushi
```

VisionClass depends entirely on the selected dataset.

It must never be used directly for nutrition lookup.

---

# Entity: CanonicalFood

Represents the standardized food used by the application.

Examples

```
Burger

Pizza

Nasi Goreng

Sushi
```

CanonicalFood is independent from

- datasets
- model outputs
- nutrition databases

It is the language spoken by the application.

---

# Vision Mapping

```
VisionClass

↓

CanonicalFood
```

Example

```
cheeseburger

↓

Burger
```

Another example

```
hamburger

↓

Burger
```

Multiple VisionClasses may map into one CanonicalFood.

---

# Entity: Ingredient

Represents optional food composition.

Ingredients may be

- predicted
- manually added
- manually removed

Examples

Burger

```
Bun
Patty
Cheese
Tomato
Onion
```

Salad

```
Lettuce
Tomato
Carrot
Corn
```

Ingredients are optional.

The application must function without ingredient information.

---

# Entity: Measurement

Represents physical properties estimated by the system.

## Attributes

- area
- height
- volume
- weight

These values may be

- estimated
- manually corrected

Measurement is independent from nutrition.

---

# Entity: PhysicalProperty

Represents known physical constants.

Examples

- density
- calibration factor
- volume coefficient

These values belong to CanonicalFood.

They do NOT belong to VisionClass.

---

# Entity: NutritionProfile

Represents nutritional values.

Examples

- calories
- protein
- fat
- carbohydrates
- fiber
- sodium
- vitamins
- minerals

NutritionProfile contains no information about where the data originated.

---

# Entity: NutritionSource

Represents an external nutrition database.

Examples

```
Panganku

USDA

Manual Dataset
```

NutritionSource provides nutrition information.

It does not define business entities.

---

# Entity: NutritionEntry

Represents one nutrition record retrieved from a NutritionSource.

Examples

```
Panganku

↓

Nasi Goreng Ayam
```

or

```
USDA

↓

Cheeseburger
```

Multiple NutritionEntries may correspond to the same CanonicalFood.

---

# Entity: NutritionSummary

Represents the total nutritional values for an entire meal.

Contains aggregated values.

Examples

- total calories
- total protein
- total fat
- total carbohydrates

---

# Entity: UserCorrection

Represents modifications performed by the user.

Examples

- change food category
- delete food item
- add food item
- edit ingredients
- edit weight

Corrections are considered first-class domain objects.

---

# Entity Relationships

```
Meal

│

├──────────────┐

▼              ▼

FoodItem   NutritionSummary

│

├──────────────┐

▼              ▼

VisionPrediction

↓

VisionClass

↓

CanonicalFood

↓

PhysicalProperty

↓

NutritionSource

↓

NutritionEntry

↓

NutritionProfile
```

---

# Mapping Hierarchy

The application follows this hierarchy.

```
VisionClass

↓

CanonicalFood

↓

NutritionEntry

↓

NutritionProfile
```

This hierarchy must never be bypassed.

---

# Business Rules

## Rule 1

VisionClass must never be used directly for nutrition lookup.

---

## Rule 2

CanonicalFood is the language of the application.

All business logic depends on CanonicalFood.

---

## Rule 3

Nutrition providers must never know VisionClass.

---

## Rule 4

Multiple VisionClasses may map into one CanonicalFood.

---

## Rule 5

One CanonicalFood may have multiple NutritionEntries.

---

## Rule 6

User corrections override AI predictions.

---

## Rule 7

Nutrition is always calculated from the final corrected meal.

---

# Aggregate Root

The aggregate root is:

```
Meal
```

Everything else belongs to a Meal.

FoodItem should never exist without a Meal.

NutritionSummary should never exist without a Meal.

---

# Value Objects

The following concepts should preferably be immutable value objects.

- BoundingBox
- SegmentationMask
- Area
- Volume
- Weight
- NutritionValue
- ConfidenceScore

---

# Domain Events (Future)

Possible future domain events include:

- MealCreated
- FoodDetected
- PredictionCorrected
- NutritionCalculated
- MealFinalized

These events are not required in the current implementation but should be considered during architecture design.

---

# Ubiquitous Language

The following terminology should be used consistently throughout the repository.

| Term | Meaning |
|-------|---------|
| Meal | One eating session |
| FoodItem | One detected food object |
| VisionClass | Raw AI prediction |
| CanonicalFood | Standardized business food entity |
| Ingredient | Food composition |
| Measurement | Estimated geometric properties |
| PhysicalProperty | Known food constants |
| NutritionSource | External nutrition database |
| NutritionEntry | One nutrition record from a source |
| NutritionProfile | Nutritional values |
| NutritionSummary | Aggregated meal nutrition |
| UserCorrection | Manual user modification |

---

# Immutable Policy

This document defines the business language of the project.

AI agents MUST NOT modify this document automatically.

Changes require explicit approval from the repository owner because they affect every architectural layer of the application.
