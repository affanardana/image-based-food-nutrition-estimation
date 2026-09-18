# Changelog

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 0.1.0  
**Status:** Mutable  
**Last Updated:** 2026-09-03

---

# Purpose

This document records user-visible and development-significant changes throughout the lifecycle of the project.

The changelog should describe:

- new features
- architecture changes that affect usage
- removed functionality
- bug fixes
- important improvements

---

# Changelog Format

This project follows a simplified changelog format.

Each version contains:

```
Added

Changed

Fixed

Removed

Deprecated
```

---

# Unreleased

## Added

- Initial project documentation structure.
- Spec-Driven Development workflow.
- Immutable and mutable documentation separation.
- AI agent development guidelines.
- Architecture decision record system.
- Project scaffolding: `.gitignore`, `pyproject.toml`, package structure (Phase 0).
- Domain layer: all value objects, entities, interfaces, and exceptions (Phase 1).
- Canonical food mapping configuration with 10 foods and vision label mappings.
- Domain unit tests: 13 test files covering value objects, entities, business rules, and meal state lifecycle (Phase 2).
- Application configuration via environment variables (`app/shared/config.py`).
- Application layer: `NutritionResolver` and `MeasurementEstimator` services (Phase 3).
- Application use cases: analyze, update, get, delete, and search meals.
- `CanonicalFoodCatalog` domain interface for vision mapping and food search.
- Application tests: 7 test files with in-memory fakes for all domain interfaces.
- Segment-first pipeline decision (ADR-010): SAM3 segmentation + depth, human labeling as the core mapping step.
- Documentation updated: DOMAIN_MODEL (Segment entity, labeling rules 8–10), ARCHITECTURE (vision + labeling pipelines), PRD (workflow, FR-04, FR-06).
- API spec: `POST /meals/analyze` now returns segments with optional suggestions; new `POST /meals/{meal_id}/label` endpoint; `suggest_labels` form flag.
- Domain reworked to segment-first: `Segment` entity, `meal.label_segments` grouping (crops never merged), `VisionProvider.segment(image, suggest_labels)` interface; `VisionPrediction` removed (Step 2).
- Application reworked: `SegmentMealUseCase`, `LabelSegmentsUseCase`, paper-based `MeasurementEstimator` (γ height, Σ volume, density weight); `AnalyzeMealUseCase` removed (Step 3).
- Infrastructure: `MockSegmentationProvider`, `ManualNutritionProvider`, `YamlCanonicalFoodCatalog`, `LocalStorageProvider` (Step 4).
- Dummy data: `nutrition_database.yaml` (per-100g, 12 foods) and `canonical_foods.yaml` extended with γ calibration factors and density.
- REST API v1: analyze/label/get/patch/delete meal endpoints, food search, health check, standard response envelope, domain-to-API error mapping, PNG/JPEG dimension parsing (Phase 6).
- In-memory meal repository for development; development entry point `uv run uvicorn app.main:app --reload`.
- Frontend MVP: React + Vite + JavaScript + Tailwind — upload, label (bbox overlays, multi-select, suggestion quick-assign), result screens.
- Backend: CORS middleware and `image_url` in meal responses for the frontend.
- Real vision provider: `SAM3SegmentationProvider` (SAM3 semantic prompts + YOLO depth, crop saving, Eq 2–3 mask stats) with `YOLODepthEstimator` and numpy-only `mask_stats` helpers; installed via `uv sync --extra vision`.
- Real-pipeline verification tool: `scripts/verify_real_pipeline.py` — runs the SAM3 + YOLO depth providers on one image and prints the Eq 2–7 summary; `--show` renders separated crops with matplotlib (added to the vision extras).
- Remote vision inference: `RemoteVisionProvider` (`VISION_PROVIDER=remote` + `VISION_REMOTE_URL`) delegates SAM3 + depth to a remote GPU service while keeping Eq 2–3 math and crop saving local; `scripts/remote_vision_server.py` runs the inference side (Colab-ready, cloudflared tunnel support).
- Modal.com deployment for vision inference: `scripts/modal_vision_server.py` (model volume; CPU by default so it runs on free credits, GPU optional) serving the same `/segment` contract, plus `inference/vision_service.py` as the shared, deployment-independent service used by both hosts.
- Supabase/Postgres food database: `SqlCanonicalFoodCatalog` and `SqlNutritionProvider` behind `CATALOG_PROVIDER=sql` / `NUTRITION_PROVIDER=sql`, with `data/nutrition.csv` (1,346 foods) merged into the curated foods and loaded by `scripts/seed_food_database.py`.
- Catalog interface gains `list_detectable_foods()` so vision providers prompt only with foods that carry VisionClass mappings, never the full catalog.
- Meal persistence: `SqlMealRepository` stores the whole Meal aggregate (segments, food items, segment groupings, ingredients, corrections) in the same database as the food data; selectable with `MEAL_REPOSITORY=sql`.
- Meal history: `GET /meals` lists past analyses, and `PUT /meals/{meal_id}/labels` re-labels a stored meal (the history edit flow). The frontend gains a History screen and an "Edit labels" action on the result screen.
- Crop files are namespaced per meal (`crops/{meal_id}_seg_001.jpg`) so analyses can no longer overwrite each other's crops.
- Deleting a meal now removes its crops as well as its image.
- Meals can be named: `PATCH /meals/{meal_id}` accepts an optional `name`, and the history list shows it with a rename action.
- Labeling screen reworked for clarity: step-by-step instructions, a selection bar with "Clear selection", per-crop "Label just this crop as …" buttons, labeled crops showing their food, and a warning when unlabeled crops would be excluded.
- Accepting predictions in bulk: selecting crops with the same predicted label offers one button to label them all, so no search is needed.
- Segments can be discarded — singly or in bulk (`POST /meals/{meal_id}/segments/discard`) — when the segmentation is wrong or the food is missing from the catalog; the crop files are deleted and only the affected food items are recalculated.
- Meals can be named from the labeling screen as well as the history list. The labeling screen has no separate save step for the name: it is applied by "Save and calculate nutrition" (the label endpoints accept an optional `name`), so a typed name cannot be lost. An unnamed meal stays "Untitled meal".
- History is paged: 20 meals load at a time with a "Load more" button, instead of every meal in one scroll.
- The hosted stack is now the default and mandatory: Supabase for food data and meals, Modal for vision. `DATABASE_URL` and `VISION_REMOTE_URL` have no defaults, and startup fails with one message listing every missing setting. The local providers remain available for tests but must be selected explicitly.
- Food search is a real autocomplete: suggestions appear as you type in a dropdown that closes on pick, on clearing the input, on clicking outside, and on Escape, with arrow-key navigation. The search button is gone.
- Food search ranks names starting with the query first ("ri" suggests "Rice" before "Keripik"), in every catalog implementation.
- Frontend is deployable to Vercel: the API origin is configurable with `VITE_API_BASE_URL`, image and crop URLs are resolved against it (they are returned as paths), and `vercel.json` rewrites unknown paths to `index.html`.
- Result page shows the analyzed photo and the meal's title beneath the "Nutrition result" heading.
- Images and crops can be stored in Supabase Storage (`STORAGE_PROVIDER=supabase`, the default), so the backend runs without a persistent disk. References become public URLs; the local filesystem provider remains for tests.
- Deployment configuration: `render.yaml` for the backend (frontend on Vercel, database and storage on Supabase, inference on Modal).
- Free-tier housekeeping: a scheduled GitHub Action queries the food search endpoint every three days so Supabase does not pause the project after seven idle days, and the frontend shows a "waking up the demo server" notice when a request takes longer than six seconds.

---

## Changed

- `compute_normalized_area` (Eq 2) now clamps to at most 1.0 so rounding never violates the Segment invariant.
- SAM3 bounding boxes are clamped to the image bounds before crop extraction.
- `data/nutrition.csv` moved from the repository root to `backend/data/` alongside the curated nutrition database.
- Vision prompts are built from detectable foods only (curated subset), so a catalog holding thousands of foods cannot flood the segmentation prompts.
- Frontend: browser title is now "Food Nutrition Estimation" and the header subtitle was removed.
- `Meal` gains `replace_labels`; `label_segments` keeps rejecting already-labeled segments, so the initial labeling keeps its guarantee.
- Meal responses now include `created_at` and `updated_at`.
- `PATCH /meals/{meal_id}` fields are now both optional, so a request may carry only a name.

---

## Fixed

- Crop references returned by the API are now public URLs (`/api/v1/images/...`), converted from the storage filesystem paths stored by real providers — crops display correctly in the frontend with `VISION_PROVIDER=sam3`.
- SAM3 results without confidence scores no longer crash label suggestions (missing scores default to 1.0).
- `LocalStorageProvider.store` now creates intermediate directories for nested destinations (e.g. `crops/`), so crop saving works on a fresh storage directory.
- `VISION_DEVICE=auto` now resolves to `cpu` on machines without CUDA (previously SAM3 rejected `auto`); unhandled server errors are now logged with their traceback.

---

## Removed

Nothing yet.

---

# v0.1.0 — Project Foundation

Release Date

```
2026-07-30
```

---

## Added

### Documentation

Added complete project documentation.

Included:

- Product Requirements Document
- Domain Model
- Architecture Documentation
- AI Development Guide
- Coding Standards
- API Specification
- Implementation Tracking
- Development Roadmap
- Architecture Decision Records

---

### Architecture

Established initial architecture principles.

Added:

- Clean Architecture
- Domain-driven design
- Provider-based integrations
- Interface-driven development

---

### AI Development Workflow

Added support for AI-assisted development through:

- AGENTS.md
- immutable documentation rules
- mutable documentation rules

---

## Changed

Nothing.

---

## Fixed

Nothing.

---

## Removed

Nothing.

---

# Future Releases

Future versions should be added using this format.

Example:

```
# v0.2.0

## Added

- Core domain entities
- Provider interfaces

## Changed

- Updated architecture

## Fixed

- Bug descriptions

## Removed

- Deprecated features
```

---

# Versioning Policy

Version numbers follow:

```
MAJOR.MINOR.PATCH
```

## MAJOR

Used for breaking architectural or API changes.

Example:

```
v2.0.0
```

---

## MINOR

Used for new features.

Example:

```
v0.3.0
```

---

## PATCH

Used for fixes and small improvements.

Example:

```
v0.3.1
```

---

# Release Checklist

Before creating a release:

- Update version number.
- Update CHANGELOG.md.
- Update ROADMAP.md.
- Verify API documentation.
- Verify tests.
- Verify implementation documentation.
- Ensure no immutable documents changed unintentionally.

---

# Maintenance

This file should grow over time.

Previous release history should never be deleted.

The changelog represents the evolution of the project.
