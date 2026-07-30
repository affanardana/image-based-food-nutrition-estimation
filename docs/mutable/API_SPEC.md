# API Specification

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 1.0  
**Status:** Mutable  
**API Style:** REST  
**Content-Type:** `application/json`

---

# Purpose

This document defines the public REST API exposed by the I-FNE backend.

The API is intentionally independent from any computer vision model or nutrition provider.

Clients should never know:

- which AI model is used
- which nutrition database is used
- how measurements are estimated

The API only exposes business objects.

---

# Base URL

```
/api/v1
```

---

# Response Format

Every endpoint should return the following wrapper.

Successful response

```json
{
  "status": "success",
  "data": {}
}
```

Error response

```json
{
  "status": "error",
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Meal not found."
  }
}
```

---

# Error Codes

| Code | Description |
|-------|-------------|
| INVALID_REQUEST | Invalid request payload |
| VALIDATION_ERROR | Validation failed |
| UNSUPPORTED_IMAGE | Unsupported image format |
| IMAGE_TOO_LARGE | Uploaded image exceeds limit |
| MEAL_NOT_FOUND | Meal does not exist |
| FOOD_NOT_FOUND | Food item not found |
| NUTRITION_UNAVAILABLE | Nutrition data unavailable |
| PROVIDER_ERROR | External provider failed |
| INTERNAL_ERROR | Unexpected server error |

---

# Endpoint Overview

| Method | Endpoint | Description |
|----------|----------|-------------|
| POST | `/meals/analyze` | Analyze meal image |
| GET | `/meals/{meal_id}` | Retrieve meal |
| PATCH | `/meals/{meal_id}` | Apply user corrections |
| DELETE | `/meals/{meal_id}` | Delete meal |
| GET | `/foods/search` | Search canonical foods |
| GET | `/health` | Health check |

---

# POST /meals/analyze

Analyze an uploaded meal image.

Creates a draft meal.

The returned result is intended for user review before being finalized.

---

## Request

Content-Type

```
multipart/form-data
```

Fields

| Name | Type | Required |
|------|------|----------|
| image | File | Yes |

---

## Supported Formats

- JPEG
- PNG

---

## Maximum File Size

```
10 MB
```

---

## Success Response

```json
{
  "status": "success",
  "data": {
    "meal_id": "meal_01HJ2ABCD",
    "state": "draft",
    "processing_time_ms": 428,
    "image": {
      "width": 1024,
      "height": 768
    },
    "food_items": [
      {
        "id": "food_001",
        "vision_prediction": {
          "label": "cheeseburger",
          "confidence": 0.94
        },
        "canonical_food": {
          "id": "burger",
          "name": "Burger"
        },
        "measurement": {
          "estimated_weight_g": 185.2
        },
        "nutrition": {
          "calories_kcal": 510,
          "protein_g": 22.3,
          "fat_g": 28.6,
          "carbohydrates_g": 39.7
        },
        "ingredients": [
          {
            "name": "Bun",
            "source": "predicted"
          },
          {
            "name": "Beef Patty",
            "source": "predicted"
          },
          {
            "name": "Cheese",
            "source": "predicted"
          }
        ]
      }
    ],
    "summary": {
      "total_calories_kcal": 510
    }
  }
}
```

---

# GET /meals/{meal_id}

Retrieve a previously analyzed meal.

---

## Path Parameters

| Name | Type |
|------|------|
| meal_id | String |

---

## Response

```json
{
  "status": "success",
  "data": {
    "meal_id": "meal_01HJ2ABCD",
    "state": "draft",
    "food_items": [],
    "summary": {}
  }
}
```

---

# PATCH /meals/{meal_id}

Apply user corrections.

Corrections replace AI predictions.

Nutrition is recalculated automatically.

---

## Path Parameters

| Name | Type |
|------|------|
| meal_id | String |

---

## Request

```json
{
  "food_items": [
    {
      "id": "food_001",
      "canonical_food": "burger",
      "estimated_weight_g": 210,
      "ingredients": [
        "Bun",
        "Beef Patty",
        "Cheese",
        "Tomato"
      ]
    }
  ]
}
```

---

## Success Response

```json
{
  "status": "success",
  "data": {
    "meal_id": "meal_01HJ2ABCD",
    "state": "corrected",
    "summary": {
      "total_calories_kcal": 575
    }
  }
}
```

---

# DELETE /meals/{meal_id}

Delete an existing meal.

---

## Success Response

```json
{
  "status": "success",
  "data": {
    "deleted": true
  }
}
```

---

# GET /foods/search

Search available CanonicalFood entries.

Used by the correction interface.

---

## Query Parameters

| Name | Type | Description |
|------|------|-------------|
| q | String | Search keyword |
| limit | Integer | Maximum results |

---

## Example

```
GET /foods/search?q=burger
```

---

## Response

```json
{
  "status": "success",
  "data": [
    {
      "id": "burger",
      "name": "Burger"
    },
    {
      "id": "chicken_burger",
      "name": "Chicken Burger"
    }
  ]
}
```

---

# GET /health

Simple service health endpoint.

---

## Response

```json
{
  "status": "success",
  "data": {
    "service": "healthy"
  }
}
```

---

# Resource States

Meals move through the following lifecycle.

```
Uploaded

↓

Draft

↓

Corrected

↓

Finalized
```

Definitions

| State | Description |
|---------|-------------|
| uploaded | Image received |
| draft | Initial AI prediction |
| corrected | User has modified prediction |
| finalized | Nutrition confirmed |

---

# Business Rules

## Meal Analysis

Returns a draft.

The client should allow users to review the result.

---

## User Corrections

Corrections always take precedence over AI predictions.

---

## Nutrition

Nutrition is recalculated after every correction.

---

## Canonical Food

Clients should only send CanonicalFood identifiers.

Clients should never send VisionClass labels.

Correct

```json
{
  "canonical_food": "burger"
}
```

Incorrect

```json
{
  "vision_class": "cheeseburger"
}
```

---

# Primary Client

Web Frontend

---

# Versioning

The API follows URI versioning.

```
/api/v1
```

Breaking changes require a new version.

Example

```
/api/v2
```

---

# Future Endpoints

Potential future additions.

| Endpoint | Purpose |
|----------|---------|
| POST /meals/{meal_id}/finalize | Finalize meal |
| GET /meals | Meal history |
| GET /nutrition/sources | Available nutrition providers |
| GET /vision/providers | Available AI providers |
| POST /feedback | Prediction feedback |
| GET /statistics | User statistics |

---

# Notes

This document intentionally specifies only the external contract.

Implementation details such as:

- computer vision models
- segmentation algorithms
- nutrition databases
- storage implementations

must remain hidden behind the API.
