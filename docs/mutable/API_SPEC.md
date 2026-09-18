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
| POST | `/meals/analyze` | Segment meal image |
| GET | `/meals` | List stored meals (history) |
| POST | `/meals/{meal_id}/label` | Assign labels to segments |
| PUT | `/meals/{meal_id}/labels` | Replace the labeling of a stored meal |
| GET | `/meals/{meal_id}` | Retrieve meal |
| PATCH | `/meals/{meal_id}` | Apply user corrections |
| POST | `/meals/{meal_id}/segments/discard` | Discard one or more segments |
| DELETE | `/meals/{meal_id}` | Delete meal |
| GET | `/foods/search` | Search canonical foods |
| GET | `/health` | Health check |

---

# POST /meals/analyze

Segment an uploaded meal image.

Creates a draft meal containing segments (crops) awaiting labels.

The returned result is intended for user review before being finalized.

---

## Request

Content-Type

```
multipart/form-data
```

Fields

| Name | Type | Required | Description |
|------|------|----------|-------------|
| image | File | Yes | Meal image |
| suggest_labels | Boolean | No | Attach label suggestions (default false) |

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
    "segments": [
      {
        "id": "seg_001",
        "crop_url": "/api/v1/meals/meal_01HJ2ABCD/crops/seg_001.jpg",
        "bbox": {
          "x": 10,
          "y": 20,
          "width": 300,
          "height": 120
        },
        "suggestion": {
          "label": "sate",
          "confidence": 0.87
        }
      },
      {
        "id": "seg_002",
        "crop_url": "/api/v1/meals/meal_01HJ2ABCD/crops/seg_002.jpg",
        "bbox": {
          "x": 320,
          "y": 15,
          "width": 280,
          "height": 130
        },
        "suggestion": {
          "label": "lontong",
          "confidence": 0.81
        }
      }
    ],
    "food_items": [],
    "summary": {}
  }
}
```

When `suggest_labels` is false, `suggestion` is `null` for every segment.

---

# POST /meals/{meal_id}/label

Assign canonical food labels to segments.

Segments sharing one label become a single FoodItem.

Crop images are never merged.

Nutrition is calculated from the aggregated measurements.

---

## Path Parameters

| Name | Type |
|------|------|
| meal_id | String |

---

## Request

```json
{
  "assignments": [
    {
      "canonical_food_id": "sate",
      "segment_ids": ["seg_001", "seg_002", "seg_003"]
    },
    {
      "canonical_food_id": "lontong",
      "segment_ids": ["seg_004"]
    }
  ],
  "name": "Lunch with the team"
}
```

| Field | Type | Description |
|-------|------|-------------|
| assignments | Array | Label groups; required |
| name | String | Optional meal name saved in the same operation; omit it to leave the current name alone, send an empty string to clear it |

---

## Success Response

```json
{
  "status": "success",
  "data": {
    "meal_id": "meal_01HJ2ABCD",
    "state": "corrected",
    "food_items": [
      {
        "id": "food_001",
        "canonical_food": {
          "id": "sate",
          "name": "Sate"
        },
        "segment_ids": ["seg_001", "seg_002", "seg_003"],
        "measurement": {
          "estimated_weight_g": 185.2
        },
        "nutrition": {
          "calories_kcal": 403.7,
          "protein_g": 45.4,
          "fat_g": 20.7,
          "carbohydrates_g": 8.9
        }
      }
    ],
    "summary": {
      "total_calories_kcal": 403.7
    }
  }
}
```

---

# GET /meals

List stored meals, newest first — the meal history.

Each entry is a compact summary; retrieve a full meal with
`GET /meals/{meal_id}`.

---

## Query Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| limit | Integer | 20 | Page size (1–100) |
| offset | Integer | 0 | Number of meals to skip |

---

## Response

```json
{
  "status": "success",
  "data": [
    {
      "meal_id": "meal_01HJ2ABCD",
      "state": "corrected",
      "name": "Lunch with the team",
      "created_at": "2026-09-17T10:15:00Z",
      "updated_at": "2026-09-17T10:16:12Z",
      "image_url": "/api/v1/images/meal_01HJ2ABCD_plate.jpg",
      "total_calories_kcal": 403.7,
      "food_item_count": 2,
      "segment_count": 5
    }
  ]
}
```

---

# PUT /meals/{meal_id}/labels

Replace the labeling of a stored meal.

Unlike `POST /meals/{meal_id}/label`, segments that already carry a
label may be reassigned, because the labeling as a whole is replaced.
Segments omitted from the request become unlabeled again.

Measurements and nutrition are recalculated for the new grouping. The
optional `name` is applied in the same operation, exactly as on
`POST /meals/{meal_id}/label`.

---

## Request

Identical to `POST /meals/{meal_id}/label`.

```json
{
  "assignments": [
    {
      "canonical_food_id": "lontong",
      "segment_ids": ["seg_001", "seg_002"]
    }
  ],
  "name": "Leftovers"
}
```

---

## Success Response

The updated meal, in the same shape as the label endpoint.

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
    "name": "",
    "created_at": "2026-09-17T10:15:00Z",
    "updated_at": "2026-09-17T10:15:04Z",
    "food_items": [],
    "summary": {}
  }
}
```

Meal responses include `name`, `created_at`, and `updated_at`.

---

# PATCH /meals/{meal_id}

Apply user corrections.

Corrections replace AI predictions.

Nutrition is recalculated automatically.

Both request fields are optional; send the ones you are changing. A
request containing only `name` renames the meal without touching its
food items.

---

## Path Parameters

| Name | Type |
|------|------|
| meal_id | String |

---

## Request

```json
{
  "name": "Lunch with the team",
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

| Field | Type | Description |
|-------|------|-------------|
| name | String | Optional meal name; an empty string clears it |
| food_items | Array | Optional food item corrections |

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

# POST /meals/{meal_id}/segments/discard

Discard one or more segments.

Used when a segmentation is wrong or a food cannot be described by the
catalog. Each segment is removed from its food item — and an item left
with no segments disappears — its crop image is deleted, and the
affected items' measurements and nutrition are recalculated. Other food
items are left untouched, so corrected weights survive.

The whole request is validated before anything is discarded: if any
segment id is unknown, nothing changes.

---

## Request

```json
{
  "segment_ids": ["seg_002", "seg_005"]
}
```

---

## Response

The updated meal, in the same shape as `GET /meals/{meal_id}`.

---

## Errors

| Code | Cause |
|------|-------|
| INVALID_REQUEST | No segment ids, an unknown segment id, or a finalized meal |

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

Used by the correction interface, including autocomplete: matches are
substring-based, but names that start with the query rank first, so
"ri" suggests "Rice" before "Keripik".

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
| draft | Image segmented; crops await labels |
| corrected | User has labeled or modified the meal |
| finalized | Nutrition confirmed |

---

# Business Rules

## Meal Analysis

Returns a draft with segments.

The client should allow users to review and label the segments.

---

## Meal Labeling

The user assigns CanonicalFood to segments.

Suggestions are optional and never authoritative.

Segments sharing one label form one FoodItem.

Crop images are never merged.

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
