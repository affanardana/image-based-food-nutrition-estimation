# Current Implementation

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 0.1.0  
**Status:** Mutable  
**Last Updated:** 2026-09-03

---

# Implemented Components (Phases 1–3 Complete)

## Domain Layer

### Value Objects
- `ConfidenceScore` — bounded float 0.0–1.0 with validation
- `BoundingBox` — (x, y, width, height) with area and center properties
- `Area`, `Volume`, `Weight` — physical measurement value objects
- `NutritionValue` — single nutrient value with unit
- `NutritionProfile` — complete nutritional profile with scale and add operations

### Entities
- `VisionClass` — raw AI prediction label (immutable)
- `CanonicalFood` — standardized food identity with typical weight and physical properties
- `VisionPrediction` — AI prediction with confidence, bbox, provider metadata
- `Ingredient` — food component with predicted/manual source
- `PhysicalProperty` — food density and estimation coefficients
- `Measurement` — mutable geometric estimates (area, volume, weight)
- `NutritionSource` — external nutrition database reference
- `NutritionEntry` — nutrition record from a source for a canonical food
- `NutritionSummary` — aggregated meal totals with recalculation
- `UserCorrection` — immutable audit record of user modifications
- `FoodItem` — core entity with correction operations
- `Meal` — aggregate root with full state lifecycle

### Interfaces (ABCs)
- `VisionProvider` — `analyze(image_path) → list[VisionPrediction]`
- `NutritionProvider` — `get_nutrition_per_100g(canonical_food) → NutritionProfile`
- `CanonicalFoodCatalog` — vision mapping, lookup, and search
- `MealRepository` — `save`, `get_by_id`, `delete`, `exists`
- `StorageProvider` — `store`, `retrieve`, `delete`

### Domain Exceptions
- `DomainError`, `FoodNotFoundError`, `UnsupportedFoodError`, `NutritionUnavailableError`, `MealNotFoundError`, `InvalidMealStateError`

### Configuration
- `mappings/canonical_foods.yaml` — 10 canonical foods with vision label mappings and physical properties

### Tests
- 13 test files covering all value objects, entities, and business rules
- Meal state lifecycle fully tested (uploaded → draft → corrected → finalized)

## Application Layer

### Services
- `NutritionResolver` — scales provider per-100g data to measured weight (falls back to typical weight)
- `MeasurementEstimator` — paper-based portion formulas: h = γ × max D_norm, V = Σ(A_norm × h), W = ρ × V, fallback to typical weight
- `FoodItemNutritionService` — the one place a food item is measured and resolved, shared by labeling, re-labeling, and discarding

### Use Cases
- `SegmentMealUseCase` — store image → segment (suggest_labels flag) → draft meal with segments
- `LabelSegmentsUseCase` — resolves food IDs via catalog → labels (or replaces the labeling of) segments → estimate → resolve → corrected meal
- `UpdateMealUseCase` — applies corrections to labeled items (and renames the meal), re-resolves nutrition
- `GetMealUseCase` — meal retrieval
- `ListMealsUseCase` — meal history, newest first
- `DiscardSegmentsUseCase` — drops one or more badly segmented crops, deletes their files, recalculates the affected food items
- `DeleteMealUseCase` — meal deletion with image and crop cleanup
- `SearchFoodsUseCase` — canonical food search

### Shared
- `generate_id` — prefixed unique identifier helper

### Tests
- In-memory fakes for all five domain interfaces
- 8 test files: resolver scaling, paper-formula estimator, and every use case

## Infrastructure Layer

### Providers
- `MockSegmentationProvider` — deterministic segments, honors the suggest_labels toggle
- `SAM3SegmentationProvider` — real segmentation (SAM3 semantic predictor with catalog prompts + YOLO depth); saves crops via storage; heavy deps deferred/lazy; selectable via `VISION_PROVIDER=sam3`
- `RemoteVisionProvider` — delegates inference to a remote service (Modal GPU or a local host) while keeping Eqs 2–3 math and crop saving local; selectable via `VISION_PROVIDER=remote` + `VISION_REMOTE_URL`
- `YOLODepthEstimator` — yolo26x-depth model, resizes maps to image dimensions
- `mask_stats` — pure numpy Eqs 2–3 helpers (A_norm clamped to ≤ 1.0, depth normalization, max depth in mask, bbox clamping)
- `crop_utils` / `prompts` — shared crop saving and prompt vocabulary used by the SAM3 and remote providers
- `SAM3SegmentationProvider` hardening — bboxes clamped to image bounds, missing confidence scores default to 1.0, `auto` device resolved to cpu/cuda via torch
- `ManualNutritionProvider` — per-100g data from `data/nutrition_database.yaml` (curated values)
- `YamlCanonicalFoodCatalog` — loads `mappings/canonical_foods.yaml` (12 foods with γ and density)
- `SqlNutritionProvider` — per-100g data from the SQL food database (Supabase/Postgres; SQLite in tests); prefers the configured source and falls back to any other entry
- `SqlMealRepository` — persists the Meal aggregate (segments, food items, groupings, ingredients, corrections) and lists the meal history
- `SqlCanonicalFoodCatalog` — canonical foods from the SQL database; searchable across all 1,346 foods, with `list_detectable_foods` returning the calibrated subset that carries VisionClass mappings
- `food_seed` — builds seed rows from `data/nutrition.csv` merged with the curated YAML files, and applies them as a full refresh
- `LocalStorageProvider` — filesystem storage for images and crops

### Vision extras
- Real vision dependencies install via `uv sync --extra vision` (torch, ultralytics, opencv, numpy, matplotlib)
- CPU-only machines: torch/torchvision are pinned to the PyTorch CPU wheelhouse in `pyproject.toml` (`[tool.uv.sources]` + `[[tool.uv.index]]`) so `uv sync` never pulls CUDA wheels
- Configuration: `VISION_PROVIDER` (mock | sam3 | remote), `VISION_SAM_MODEL_PATH`, `VISION_DEPTH_MODEL_PATH`, `VISION_REMOTE_URL`, `VISION_DEVICE`
- Known limitation: SAM's semantic predictor always uses the catalog prompts internally; the toggle only controls whether suggestions are attached. True class-agnostic auto-mask mode is a future change.

### Dummy Data
- `mappings/canonical_foods.yaml` — canonical foods with physical properties (density ρ, calibration γ) and vision labels
- `data/nutrition_database.yaml` — per-100g nutrition for all 12 canonical foods (curated values)
- `data/nutrition.csv` — the broad food database (1,346 Indonesian foods, per-100g values + image URLs)

### Food Database

Status

```
Implemented (SQL-backed catalog + nutrition)
```

- Schema (`app/infrastructure/persistence/schema.py`): `canonical_foods`, `nutrition_entries` (keyed by food + source), `vision_labels`
- Seeding: `uv run python scripts/seed_food_database.py` (full refresh; `--dry-run` reports counts)
- Portion estimation needs calibrated γ/ρ: the 12 curated foods have them; other foods fall back to `typical_weight_g` (default 150 g), which can be calibrated per food directly in the database
- Vision prompts come from `list_detectable_foods` (the curated subset), never the full catalog

### Tests
- 4 test files: catalog mapping/lookup/search, nutrition profiles, mock provider toggle, storage roundtrip
- SAM3 provider tests with stubbed model output (not_food filtering, prompts, suggestions, crop saving, bbox clamping, confidence fallback)
- SQL catalog / SQL nutrition / food seed tests (in-memory SQLite, no server required)

### Development Tools
- `scripts/verify_real_pipeline.py` — standalone CLI that runs the real SAM3 + YOLO depth pipeline on one image and prints the paper-methodology summary (Eqs 2–7); `--show` renders the separated crops with matplotlib
- `inference/vision_service.py` — the shared SAM3 + depth FastAPI service (`/segment`, `/health`) behind `RemoteVisionProvider`
- `scripts/remote_vision_server.py` — runs the inference service on a local GPU host; `--tunnel` exposes it via cloudflared
- `scripts/modal_vision_server.py` — deploys the inference service to Modal.com (model volume; CPU by default so it runs on free credits, GPU optional — see ADR-014); the recommended host
- `scripts/seed_food_database.py` — creates and loads the food database
- `scripts/create_schema.py` — creates any missing tables; `--drop-meal-tables` recreates the meal tables after a schema change (destroys saved meals, leaves the food catalog alone)

## Presentation Layer

### API
- FastAPI app factory (`create_app`) with dependency container wiring mock/dummy providers
- Endpoints: `POST /meals/analyze` (multipart + suggest_labels), `GET /meals` (history), `POST /meals/{id}/label`, `PUT /meals/{id}/labels` (replace labeling), `GET /meals/{id}`, `PATCH /meals/{id}`, `POST /meals/{id}/segments/discard` (discard crops), `DELETE /meals/{id}`, `GET /foods/search`, `GET /health`
- Response envelope: `{status, data}` / `{status, error: {code, message}}`
- Domain errors mapped to API error codes (MEAL_NOT_FOUND, FOOD_NOT_FOUND, NUTRITION_UNAVAILABLE, UNSUPPORTED_IMAGE, IMAGE_TOO_LARGE, INVALID_REQUEST, VALIDATION_ERROR, INTERNAL_ERROR)
- PNG/JPEG dimension parsing for the analyze response
- Static file mount for stored images at `/api/v1/images`
- Crop references serialized as public URLs (storage path → `/api/v1/images/...` conversion in mappers)

### Tests
- 4 test files: full API workflow (analyze → label → correct → delete), search, health, image parsing
- Development entry point: `uv run uvicorn app.main:app --reload`

## Frontend

### Stack
- React 19 + Vite 6 + JavaScript + Tailwind CSS v4
- Dev proxy forwards `/api` to the backend at `127.0.0.1:8000`

### Screens
- Upload — file picker with label-suggestion toggle
- Label — source image with bbox overlays, crop cards, multi-select with clear-selection, one-click acceptance of predictions for every selected crop sharing a label, discard for a single crop or the whole selection, meal naming (applied by the submit button, not a separate save), food search, pending assignment list; in edit mode it starts from the meal's current labeling and saves via `PUT /meals/{id}/labels`
- Result — nutrition summary cards, food items with volume/weight/macros, weight correction (PATCH), edit labels, meal deletion
- History — saved meals (thumbnail, date, calories, item count) with open and delete

### Run
- `npm install` then `npm run dev` (http://localhost:5173)
- Backend CORS origins configurable via `CORS_ORIGINS` (default: localhost:5173 variants)

### Deployment

| Piece | Host |
|-------|------|
| Frontend | Vercel (`frontend/vercel.json`) |
| Backend | Render free tier (`render.yaml`) |
| Database | Supabase Postgres |
| Images and crops | Supabase Storage |
| Vision inference | Modal |

Frontend:

- Import the repository into Vercel with **Root Directory** `frontend`;
  the Vite preset is detected automatically.
- `VITE_API_BASE_URL` = the backend's public origin, no trailing slash.
  Left unset in development, where Vite proxies `/api` to the backend.
- Image and crop URLs are resolved against that origin by `assetUrl`
  (`src/api.js`); without it they would resolve against the Vercel domain.
- Add the deployed origin to the backend's `CORS_ORIGINS`.

Backend (Render):

- The blueprint installs uv, syncs the locked environment, and serves
  with uvicorn on `$PORT`.
- Free instances spin down after about 15 minutes idle, so the first
  request afterwards waits for the container to boot — and a Modal cold
  start can add to that. Slow, not broken.
- No persistent disk is required: images and crops live in Supabase
  Storage, and meals live in Supabase Postgres.

Why the backend is not on Vercel: its filesystem is read-only apart from
an ephemeral `/tmp`, and the Hobby plan caps a function at 60 s — which a
Modal cold start can exceed.

Keeping the free tiers awake:

- `.github/workflows/keep-alive.yml` queries the food search endpoint
  every three days. Supabase pauses a Free project after seven days
  without database activity, and a health check does not count — the
  request must actually read a table, which that endpoint does. Set the
  repository secret `IFNE_API_URL` to the backend origin.
- Do **not** add a Render keep-alive ping. A month is about 730 hours,
  and a permanently warm service would exhaust the 750 free instance
  hours and suspend the service until the next month.
- The frontend shows a "waking up the demo server" notice when a request
  exceeds six seconds (`onSlowRequestsChange` in `api.js`), which is what
  a Render or Modal cold start looks like from the browser.

---

# Purpose

This document tracks the current implementation status of the project.

Unlike the PRD or Architecture documents, this file evolves continuously throughout development.

Whenever implementation changes, this document should be updated accordingly.

---

# Project Status

Current Phase

```
Application Layer Implementation
```

Overall Progress

```
██████████████████████░░░░░░ 75%
```

Current Milestone

```
v0.4 — Nutrition Pipeline (Complete) / v0.5 — Human Correction (Complete) / v0.6 — Persistence (Complete) / v0.7 — API Stabilization (Next)
```

---

# Current Stack

## Language

```
Python 3.12+
```

---

## Package Manager

```
uv
```

---

## API Framework

```
FastAPI
```

---

## Validation

```
Pydantic v2
```

---

## ORM

```
SQLAlchemy 2.x
```

---

## Database

```
PostgreSQL
```

Development environments may temporarily use SQLite.

---

## Testing

```
pytest
```

---

## Formatting

```
Ruff
```

---

## Type Checking

```
mypy
```

---

# Repository Structure

Current target structure

```text
backend/
├──app/
│   ├── domain/
│   │
│   ├── application/
│   │
│   ├── infrastructure/
│   │
│   ├── presentation/
│   │
│   └── shared/
└── tests/
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── presentation/

frontend/
├──src/
└── public/

docs/
├── immutable/
└── mutable/

```

---

# Frontend and Backend Tools
Backend
↓

FastAPI

Frontend
↓

React

Communication
↓

REST API

---

# Vision Pipeline

Status

```
Implemented (segment-first)
```

Target abstraction

```text
VisionProvider

↓

Segment (crop + mask statistics + optional suggestion)

↓

User Labels

↓

FoodItem
```

Planned providers

- MockSegmentationProvider
- SAM3SegmentationProvider (optional extras, GPU)
- YOLO depth estimation (optional extras, GPU)

The application must never depend on a specific provider.

---

# Nutrition Pipeline

Status

```
In Progress
```

Target abstraction

```text
NutritionProvider

↓

NutritionResolver

↓

NutritionProfile
```

Planned providers

- PangankuProvider
- USDAProvider
- ManualProvider

---

# Canonical Mapping

Status

```
Implemented (suggestion-only)
```

Purpose

Pre-map suggested vision labels into business entities for user review.

```
VisionClass (suggestion)

↓

User Review

↓

CanonicalFood
```

The mapping layer supports suggestions.

Business logic must never consume VisionClass directly.

---

# Measurement Pipeline

Status

```
Implemented (paper-based method)
```

Responsibilities

- area estimation — mask-area normalization A_norm = A_mask / A_bbox
- height estimation — h = γ × max(D_norm in mask)
- volume estimation — V = Σ(A_norm × h)
- weight estimation — W = density × V

Implementation details are provider-dependent.

Business logic only consumes standardized measurements.

---

# Human Correction Pipeline

Status

```
Implemented (labeling-first)
```

The primary workflow is labeling segments after segmentation.

Users will be able to

- label segments (assign CanonicalFood)
- group segments under one food item
- remove detected food
- add missing food
- change food category
- modify estimated weight
- modify ingredients

Corrections override AI predictions.

---

# Persistence

Status

```
Implemented (SQL meal repository + history)
```

Primary database

```
PostgreSQL
```

Development database

```
SQLite
```

Repositories should be interface-driven.

The Meal aggregate is persisted by `SqlMealRepository` (tables: `meals`,
`segments`, `food_items`, `food_item_segments`, `food_item_ingredients`,
`food_item_corrections`). Canonical foods are stored as a snapshot per
food item so a past meal keeps its meaning when the catalog changes.
Meals also carry a user-editable `name` (ADR-016).
`InMemoryMealRepository` remains the default and the test double.

---

# Storage

Status

```
Implemented (Supabase Storage + local filesystem)
```

Initial implementation

```
Local File System
```

Future support

- S3-compatible storage
- Cloud storage providers

---

# API

Status

```
Implemented (v1, mock and real SAM3/YOLO providers)
```

Current version

```
v1
```

The API is documented in

```
docs/mutable/API_SPEC.md
```

---

# Authentication

Status

```
Not Implemented
```

Authentication is outside the scope of the MVP.

Future versions may include

- JWT
- OAuth2
- Session-based authentication

---

# Background Processing

Status

```
Not Planned
```

Future candidates

- Celery
- Dramatiq
- RQ

Current implementation should remain synchronous unless performance becomes a bottleneck.

---

# Configuration

Status

```
Implemented (environment variables)
```

Configuration should be managed through

- environment variables
- configuration objects

No hardcoded infrastructure configuration.

Current variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | Supabase Postgres connection string | **required** |
| `MEAL_REPOSITORY` | Meal storage (`memory` \| `sql`) | `sql` |
| `CATALOG_PROVIDER` | Canonical food source (`yaml` \| `sql`) | `sql` |
| `NUTRITION_PROVIDER` | Nutrition source (`manual` \| `sql`) | `sql` |
| `NUTRITION_SOURCE` | Preferred source within the database | `nutrition_csv` |
| `VISION_PROVIDER` | Vision source (`remote` \| `sam3` \| `mock`) | `remote` |
| `VISION_REMOTE_URL` | Modal inference endpoint | **required** for `remote` |
| `VISION_SAM_MODEL_PATH` / `VISION_DEPTH_MODEL_PATH` | Model checkpoints for `sam3` | — |
| `VISION_DEVICE` | Inference device (`auto` \| `cpu` \| `cuda`) | `auto` |
| `STORAGE_PROVIDER` | Image storage (`supabase` \| `local`) | `supabase` |
| `SUPABASE_URL` | Supabase project URL | **required** for `supabase` |
| `SUPABASE_SERVICE_KEY` | Supabase service-role key (server-side secret) | **required** for `supabase` |
| `SUPABASE_BUCKET` | Storage bucket name | `ifne` |
| `STORAGE_PATH` | Upload/crop directory for the `local` provider | `./storage` |
| `MAX_UPLOAD_SIZE_MB` | Upload limit | `10` |
| `CORS_ORIGINS` | Allowed frontend origins | localhost:5173 |

### Startup requirements

The defaults describe the hosted deployment: Supabase holds the food
data and the meals, and Modal serves vision inference. `build_dependencies`
validates the configuration before wiring anything and refuses to start,
listing every missing setting at once, when:

- any of `CATALOG_PROVIDER`, `NUTRITION_PROVIDER`, `MEAL_REPOSITORY` is
  `sql` (the default) and `DATABASE_URL` is empty
- `VISION_PROVIDER=remote` (the default) and `VISION_REMOTE_URL` is empty
- `VISION_PROVIDER=sam3` without both model checkpoint paths
- `STORAGE_PROVIDER=supabase` (the default) without `SUPABASE_URL` and
  `SUPABASE_SERVICE_KEY`

Nothing falls back to a local database, a mock model, or the local disk,
so a misconfiguration surfaces at startup instead of silently writing to
local state.

The local providers (`mock` vision, `yaml` catalog, `manual` nutrition,
`memory` meals, `local` storage) are still implemented and are what the
test suite uses; they just have to be selected explicitly.

Images and crops are stored in Supabase Storage
(`SupabaseStorageProvider`), so the backend needs no persistent disk.
The bucket is read-public: `store` returns an object's public URL and
that URL is the reference kept in the database. The service key that
authorises writes is a server-side secret and is read from the
environment only.

---

# Logging

Status

```
Implemented (structured logging in use cases and providers)
```

Logging should be structured.

Important events

- image uploaded
- inference completed
- nutrition resolved
- meal saved
- correction applied

---

# Error Handling

Status

```
Implemented (domain errors mapped to API error codes)
```

Domain errors

Examples

- UnsupportedFoodError
- NutritionUnavailableError
- MealNotFoundError

Infrastructure errors should be translated before reaching the Presentation layer.

---

# Testing Status

| Layer | Status |
|---------|--------|
| Domain | Implemented |
| Application | Implemented |
| Infrastructure | Implemented (mock/dummy + SAM3/YOLO with stubbed model tests) |
| Presentation | Implemented (REST API v1) |

Target priority

```
Domain

↓

Application

↓

Infrastructure

↓

Presentation
```

---

# Current Interfaces

## VisionProvider

Status

```
Implemented (Interface, being reworked to segment-first)
```

Purpose

Standard interface for all computer vision providers.

Returns Segments (crops + mask statistics + optional suggestions).

---

## NutritionProvider

Status

```
Implemented (Interface)
```

Purpose

Standard interface for all nutrition providers.

---

## MealRepository

Status

```
Implemented (Interface)
```

Purpose

Persistence abstraction for Meal aggregates.

---

## StorageProvider

Status

```
Implemented (Interface)
```

Purpose

Image storage abstraction.

---

# External Dependencies

Planned

| Dependency | Purpose |
|------------|---------|
| Panganku | Nutrition data |
| FastAPI | REST API |
| PostgreSQL | Persistence |
| SQLAlchemy | ORM |

The exact AI framework is intentionally omitted because providers are interchangeable.

---

# Known Limitations

Current assumptions

- Single-image input only
- No video support
- No authentication
- No distributed inference
- No active learning
- No meal recommendation
- No medical functionality

---

# Implementation Milestones

## v0.1

- Project initialization
- Documentation
- Architecture
- Project structure

Status

```
In Progress
```

---

## v0.2

Planned

- Domain entities
- Value objects
- Interfaces
- Dependency injection

---

## v0.3

Planned

- VisionProvider abstraction
- Mock implementation
- Meal analysis use case

---

## v0.4

Planned

- NutritionProvider
- Canonical mapping
- Nutrition calculation

---

## v0.5

Planned

- Human correction workflow
- Persistence
- Meal history

---

## v1.0

Target MVP

Expected features

- Image upload
- Vision provider
- Canonical mapping
- Nutrition provider
- User correction
- Meal persistence
- REST API
- Documentation
- Automated tests

---

# Notes for Contributors

When implementation changes

Update this document.

Examples include

- new providers
- new interfaces
- architecture refinements
- completed milestones
- infrastructure changes
- implementation status

This document should always reflect the current state of the repository.

It is acceptable for this document to change frequently throughout development.
