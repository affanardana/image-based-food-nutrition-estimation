# Architecture Decision Records (ADR)

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 1.0  
**Status:** Mutable  
**Last Updated:** 2026-07-30

---

# Purpose

This document records important architectural decisions made during the development of I-FNE.

Architecture Decision Records (ADR) preserve the reasoning behind significant choices.

The purpose is not only to record what was chosen, but also:

- why it was chosen
- what alternatives were considered
- what consequences exist

---

# ADR Rules

## Append Only

Previous decisions must never be modified.

If a decision changes, create a new ADR explaining the change.

---

## Historical Record

Some decisions may become outdated.

They should remain in this document because they explain the evolution of the system.

---

## Format

Each ADR follows:

```
ADR-NNN

Title

Status

Context

Decision

Alternatives Considered

Consequences
```

---

# ADR-001

## Title

Use Clean Architecture as the Primary System Architecture

---

## Status

Accepted

---

## Date

2026-07-30

---

## Context

The project combines multiple unstable components:

- computer vision models
- nutrition databases
- storage systems
- APIs

AI technologies change rapidly.

A tightly coupled architecture would make future changes expensive.

---

## Decision

The system will use Clean Architecture principles.

The application will be separated into:

- Domain
- Application
- Infrastructure
- Presentation

The Domain layer is the center of the system.

---

## Alternatives Considered

### Monolithic Application

Rejected.

Reason:

Would tightly couple AI, database, and business logic.

---

### Model-Centric Architecture

Rejected.

Reason:

The project is a software system, not only a machine learning experiment.

---

## Consequences

Positive:

- easier provider replacement
- better testing
- clearer responsibilities

Negative:

- additional abstraction layers
- more initial code

---

# ADR-002

## Title

Treat AI Models as Replaceable Providers

---

## Status

Accepted

---

## Date

2026-07-30

---

## Context

Food recognition technology changes frequently.

Possible implementations include:

- YOLO variants
- segmentation models
- vision-language models
- foundation models

The application should not depend on one model.

---

## Decision

All computer vision systems must implement a common interface.

Example:

```
VisionProvider
```

Implementations may include:

```
YOLOProvider

FlorenceProvider

MockVisionProvider
```

---

## Alternatives Considered

### Direct Model Integration

Rejected.

Reason:

Would couple business logic to a specific AI technology.

---

## Consequences

Positive:

- models can be replaced
- easier experimentation
- easier testing

Negative:

- requires adapter implementation

---

# ADR-003

## Title

Separate VisionClass from CanonicalFood

---

## Status

Accepted

---

## Date

2026-07-30

---

## Context

Computer vision datasets and nutrition databases use different naming systems.

Example:

AI dataset:

```
cheeseburger
```

Nutrition database:

```
burger
```

Direct mapping creates dependency between datasets and nutrition sources.

---

## Decision

Introduce a mapping layer.

Flow:

```
VisionClass

↓

CanonicalFood

↓

NutritionProvider
```

---

## Alternatives Considered

### Direct VisionClass Lookup

Rejected.

Reason:

Dataset labels are unstable and provider-specific.

---

## Consequences

Positive:

- supports multiple AI models
- supports multiple nutrition databases
- cleaner domain model

Negative:

- requires maintaining mappings

---

# ADR-004

## Title

Nutrition Providers Must Be Pluggable

---

## Status

Accepted

---

## Date

2026-07-30

---

## Context

Nutrition information may come from different sources.

Examples:

- Panganku
- USDA
- manually curated datasets

No single source is guaranteed to be complete.

---

## Decision

Nutrition access must use:

```
NutritionProvider
```

Possible implementations:

```
PangankuProvider

USDAProvider

ManualNutritionProvider
```

---

## Alternatives Considered

### Hardcoded Nutrition Database

Rejected.

Reason:

Difficult to update and maintain.

---

## Consequences

Positive:

- easy database replacement
- easier country-specific support

Negative:

- requires data normalization

---

# ADR-005

## Title

Human-in-the-loop is a Core Workflow

---

## Status

Accepted

---

## Date

2026-07-30

---

## Context

Food images contain uncertainty.

Examples:

- hidden ingredients
- similar-looking foods
- mixed dishes
- unknown portion sizes

Fully automated prediction is unreliable.

---

## Decision

User correction is considered part of the normal workflow.

The system must support:

- adding food
- removing food
- changing food category
- changing weight
- editing ingredients

---

## Alternatives Considered

### Fully Automated System

Rejected.

Reason:

Creates false confidence and limits practical usability.

---

## Consequences

Positive:

- better real-world usability
- transparent uncertainty

Negative:

- requires additional UI and workflow handling

---

# ADR-006

## Title

Nutrition Calculation Uses Final Corrected Meal State

---

## Status

Accepted

---

## Date

2026-07-30

---

## Context

AI predictions may be wrong.

Users may modify predictions.

Nutrition should represent the user's confirmed meal.

---

## Decision

Nutrition calculation occurs after correction.

Flow:

```
AI Prediction

↓

User Correction

↓

Final Meal

↓

Nutrition Calculation
```

---

## Alternatives Considered

### Calculate Immediately After AI Prediction

Rejected.

Reason:

Would produce misleading results.

---

## Consequences

Positive:

- more accurate user experience
- correction workflow becomes natural

Negative:

- requires recalculation support

---

# ADR-007

## Title

Use Interfaces Before Implementations

---

## Status

Accepted

---

## Date

2026-07-30

---

## Context

The project contains many external dependencies.

Examples:

- AI frameworks
- databases
- APIs

Direct usage creates coupling.

---

## Decision

All major external dependencies must be accessed through interfaces.

Examples:

```
VisionProvider

NutritionProvider

StorageProvider

MealRepository
```

---

## Alternatives Considered

### Direct Dependency Injection of Concrete Classes

Rejected.

Reason:

Still exposes implementation details.

---

## Consequences

Positive:

- easier testing
- easier replacement

Negative:

- more initial design effort

---

# ADR-008

## Title

Documentation is Divided into Immutable and Mutable Categories

---

## Status

Accepted

---

## Date

2026-07-30

---

## Context

AI coding agents can unintentionally modify important project decisions.

The project requires documentation that is both:

- stable
- continuously updated

---

## Decision

Documentation is separated.

Immutable:

```
docs/immutable/
```

Mutable:

```
docs/mutable/
```

AI agents may update mutable documents but must not modify immutable documents without explicit instruction.

---

## Alternatives Considered

### Single Documentation Folder

Rejected.

Reason:

No distinction between stable requirements and evolving implementation.

---

## Consequences

Positive:

- safer AI-assisted development
- clearer project history

Negative:

- requires maintaining document boundaries

---

# ADR-009

## Title

The Project Prioritizes System Engineering Over Model Accuracy

---

## Status

Accepted

---

## Date

2026-07-30

---

## Context

The project is intended as a portfolio system.

A highly accurate model without proper engineering does not demonstrate production capability.

---

## Decision

Success is measured by:

- architecture quality
- modularity
- maintainability
- extensibility
- complete workflow

Model accuracy is important but not the only objective.

---

## Alternatives Considered

### Benchmark-Oriented Development

Rejected.

Reason:

Would shift focus away from building a complete system.

---

## Consequences

Positive:

- stronger portfolio value
- easier long-term development

Negative:

- may not achieve maximum benchmark scores

---

# ADR-010

## Title

Segment-First Pipeline with Human Labeling

---

## Status

Accepted

---

## Date

2026-08-24

---

## Context

SAM 3 performs class-agnostic segmentation and accepts text prompts.

A reference implementation combines SAM 3 segmentation with YOLO depth estimation to estimate portions using calibrated heuristics (mask-area normalization, depth normalization, per-class gamma height factor, density-based weight, per-gram nutrient constants).

The previous design classified food automatically and treated correction as a secondary step.

The owner decided the system should segment the image into crops and let the user label every crop, keeping the reference implementation's portion math.

---

## Decision

The vision pipeline becomes segment-first.

- Vision providers return Segments (crops + mask statistics + optional suggestions).
- The user labels segments; segments sharing one label form one FoodItem.
- Crop images are never merged; only the computation aggregates.
- Portion estimation uses the calibrated method: V = Σ(A_norm × γ × max D_norm), W = density × V.
- Label suggestions are a per-request toggle: enabled runs the catalog names as text prompts; disabled is pure class-agnostic segmentation.

---

## Alternatives Considered

### Automatic Classification Pipeline

Partially superseded.

Reason:

Labeling is the core workflow; suggestions remain optional.

### Fully Manual Labeling Only

Rejected as the only mode.

Reason:

Suggestions reduce user effort; the toggle keeps them optional.

---

## Consequences

Positive:

- human-in-the-loop becomes the core mapping step
- crop-level traceability
- no extra classifier model required for suggestions

Negative:

- VisionPrediction superseded by Segment
- labeling becomes a required workflow step
- real providers require GPU dependencies (kept in optional extras)

---

# ADR-011

## Title

Remote Vision Inference for GPU-less Development Machines

---

## Status

Accepted

---

## Date

2026-09-03

---

## Context

The real vision pipeline (SAM3, ~3.2 GB checkpoint) requires a GPU or
substantial RAM. The owner's development machine is CPU-only with ~3.5 GB
RAM, so local inference is impossible (OOM during model load).

Running models on a remote GPU (e.g. Google Colab) is a common workflow,
but hardcoding such a service into the application would violate the
provider-independence principle.

---

## Decision

Introduce a RemoteVisionProvider implementing the existing
VisionProvider interface:

- The backend POSTs the image and the prompt vocabulary to a remote
  inference URL.
- The remote runs SAM3 + YOLO depth and returns raw observations
  (masks, boxes, class names, confidences, depth map).
- The backend keeps all paper-methodology math (Eqs 2-3), mask
  statistics, and crop saving local — the remote is a dumb model
  runner with no business logic.
- Configuration: VISION_PROVIDER=remote + VISION_REMOTE_URL.
- A self-contained server script (scripts/remote_vision_server.py)
  hosts the inference side, with cloudflared tunnel support for Colab.

---

## Alternatives Considered

### Replicate the full pipeline remotely

Rejected.

Reason:

Would duplicate measurement and crop logic outside the codebase,
creating two sources of truth.

### Force local inference only

Rejected.

Reason:

The owner's hardware cannot run the models; blocking on hardware would
stall the project.

---

## Consequences

Positive:

- vision providers remain interchangeable (mock, sam3, remote)
- business logic untouched by the deployment topology
- GPU-speed inference available during development

Negative:

- remote service availability depends on Colab/tunnel
- image bytes leave the machine during development

---

# ADR-012

## Title

Store Food Data (Catalog and Nutrition) in a SQL Database

---

## Status

Accepted

---

## Date

2026-09-17

---

## Context

Food data lived in YAML files: a 12-food curated catalog with physical
properties, and a placeholder nutrition database. A real food database
(1,346 Indonesian foods with per-100g nutrition) became available, which
YAML cannot serve: it must be searchable, queryable, and maintainable.

Supabase (hosted Postgres) is the owner's chosen host.

Constraint: the domain must not learn about the database. The catalog
and nutrition providers are already interfaces, so a SQL implementation
is an adapter, not an architecture change.

---

## Decision

Food data moves to SQL behind the existing domain interfaces:

- Schema: `canonical_foods`, `nutrition_entries` (keyed by food and
  source), `vision_labels`.
- `SqlCanonicalFoodCatalog` and `SqlNutritionProvider` implement the
  existing `CanonicalFoodCatalog` and `NutritionProvider` interfaces.
  Selected via `CATALOG_PROVIDER=sql` / `NUTRITION_PROVIDER=sql`; the
  YAML providers remain available and are still the default.
- The CSV supplies the broad food list and nutrition; the curated YAML
  files supply physical properties (density, calibration factor) and
  VisionClass mappings, merged by food id during seeding.
- Seeding is a full refresh (`scripts/seed_food_database.py`).
- The catalog interface gains `list_detectable_foods()`: only foods
  carrying VisionClass mappings may be used as vision prompts.
- Foods without calibrated physical properties fall back to
  `typical_weight_g` (default 150 g) for portion estimation.

---

## Alternatives Considered

### Supabase client library (REST)

Rejected.

Reason:

Couples the application to one vendor's API. Plain SQL over
SQLAlchemy works against any Postgres and is testable on SQLite.

### Nutrition columns on the canonical food row

Rejected.

Reason:

Violates domain rule 5 — one CanonicalFood may have entries from
several nutrition sources.

### Prompting the vision model with every catalog food

Rejected.

Reason:

Thousands of text prompts are unusable for semantic segmentation and
produce duplicate masks for the same object.

---

## Consequences

Positive:

- food coverage grows from 12 curated foods to 1,346 searchable foods
- nutrition comes from a real dataset instead of placeholders
- providers remain interchangeable; tests need no server (SQLite)

Negative:

- requires `DATABASE_URL` and the psycopg driver at runtime
- portion estimation is coarse (150 g default) for uncalibrated foods
  until they are calibrated in the database
- re-seeding discards calibration edits made directly in the database

---

# ADR-013

## Title

Host Remote Vision Inference on Modal.com

---

## Status

Accepted

---

## Date

2026-09-17

---

## Context

ADR-011 delegated SAM3 + depth inference to a remote GPU. The chosen
host was Google Colab with a cloudflared tunnel, which works but is
ephemeral: sessions expire, URLs change, and the tunnel must be
restarted, which makes the backend's `VISION_REMOTE_URL` a moving
target during development.

The development machine has ~3.5 GB RAM and cannot run the models
locally (SAM3 checkpoint alone is 3.2 GB).

---

## Decision

Serve the remote inference service on Modal.com:

- `scripts/modal_vision_server.py` runs the service on a GPU with the
  model checkpoints kept in a Modal Volume; the deployed URL is stable.
- The service itself is extracted into `inference/vision_service.py`,
  shared by the Modal app and the local runner
  (`scripts/remote_vision_server.py`), so the `/segment` contract
  cannot drift between hosts.
- `RemoteVisionProvider` is unchanged: deployment topology stays behind
  the provider interface (ADR-011 still holds).

---

## Alternatives Considered

### Keep Colab as the default host

Superseded.

Reason:

Ephemeral sessions and rotating tunnel URLs make repeated development
cycles fragile. The local runner remains available for GPU hosts.

### Duplicate the service inside the Modal app

Rejected.

Reason:

Two copies of the wire contract drift; the backend must not depend on
which host is serving.

### Local inference

Rejected.

Reason:

Model memory requirements exceed the development machine.

---

## Consequences

Positive:

- stable inference URL; no tunnel or session management
- model checkpoints live in the Modal volume (~3.3 GB freed locally)
- one service definition serves every host

Negative:

- cold starts (~1 minute) after the container scales down
- inference runs on Modal's GPU billing
- internet connectivity is required for analysis

---

# ADR-014

## Title

Run Modal Inference on CPU Under the Free Tier

---

## Status

Accepted

---

## Date

2026-09-17

---

## Context

ADR-013 selected Modal.com as the host for remote vision inference.
Modal requires a payment method on file for GPU functions, even when
the usage is covered by the free monthly credits; the owner's account
is on the free tier without one. Deploying a T4 function fails with
"Please add a payment method to use T4 GPU functions."

The models cannot run locally (ADR-011), so remote inference must
remain available without a payment method.

---

## Decision

The Modal app defaults to CPU:

- `GPU_TYPE = None`, with 8 cores and 16 GiB memory — Modal's default
  (0.125 cores / 128 MiB) cannot hold the models.
- The image installs CPU-only torch wheels on the CPU path, so it does
  not carry ~2.5 GB of unusable CUDA libraries.
- GPU execution remains one constant away (`GPU_TYPE = "T4"`) for when
  a payment method is added; GPU containers return to Modal's default
  CPU allocation so the GPU is not billed alongside idle CPU.
- The service contract is unchanged: slower inference, same interface.

---

## Alternatives Considered

### Add a payment method to Modal

Held in reserve.

Reason:

Would enable GPU inference within the free credits, but the owner has
not chosen to attach one.

### Return to Google Colab (ADR-011)

Rejected.

Reason:

Ephemeral sessions and rotating tunnel URLs were the reason ADR-013
moved to Modal in the first place.

### Local inference

Rejected.

Reason:

Model memory requirements exceed the development machine.

---

## Consequences

Positive:

- no payment method required; runs on free credits
- CPU-only image builds faster and smaller
- switching to a GPU is a one-line change

Negative:

- inference takes tens of seconds per image instead of seconds
- cold starts still apply after the container scales down
- the 8-core / 16 GiB allocation is billed against free credits while
  the container is warm

---

# ADR-015

## Title

Persist Meals and Add a Meal History

---

## Status

Accepted

---

## Date

2026-09-17

---

## Context

Meals lived only in process memory, so every analysis was lost when the
backend restarted. The owner asked for a history of past analyses that
can be viewed, edited, and deleted — the v0.6 Persistence milestone.

The food catalog already lives in Supabase (ADR-012), so the same
database can hold meals.

The owner explicitly decided **against** accounts: the application stays
single-user, with no login, no users, and no ownership. The immutable
DOMAIN_MODEL.md therefore stays untouched.

---

## Decision

Persist the Meal aggregate in SQL behind the existing MealRepository
interface:

- `SqlMealRepository` writes meals, segments, food items, segment
  groupings, ingredients, and corrections across six tables. The whole
  aggregate is rewritten on save, so the stored meal always equals the
  domain object.
- CanonicalFood is stored as a snapshot per food item (id, name, typical
  weight, density, γ). A past meal must not change meaning when the food
  catalog is re-seeded or renamed.
- Child rows are deleted explicitly in dependency order instead of
  relying on `ON DELETE CASCADE`, because SQLite (the test database)
  does not enforce foreign keys by default — cascades would behave
  differently in tests than in production.
- `MealRepository` gains `list_recent(limit, offset)`, returning full
  aggregates rather than introducing a read-model type. The domain stays
  free of invented concepts, and `list_recent` uses one query per table
  for the page instead of N+1 per meal.
- Re-labeling is a separate domain operation (`Meal.replace_labels`),
  exposed as `PUT /meals/{meal_id}/labels`. `label_segments` keeps
  rejecting already-labeled segments, so the initial labeling flow keeps
  its safety property. Both modes share one use case, so the estimation
  and nutrition workflow is not duplicated.
- Crops are namespaced by meal (`crops/{meal_id}_seg_001.jpg`). Without
  this, a second analysis overwrote the first one's crop files and the
  history would have shown the wrong images. `VisionProvider.segment`
  gains an additive `namespace` parameter, so existing callers and tests
  are unaffected.
- Deleting a meal also removes its crops.
- Configuration: `MEAL_REPOSITORY=memory|sql`, defaulting to `memory`
  (`InMemoryMealRepository` remains the default and the test double).

---

## Alternatives Considered

### Store the meal as a JSON document

Rejected.

Reason:

Opaque to queries and constraints, and it hides the aggregate's real
shape from the database.

### Rely on foreign-key cascades for deletion

Rejected.

Reason:

SQLite does not enforce foreign keys by default, so behaviour would
diverge between the test database and production.

### A dedicated read-model type for the history list

Rejected.

Reason:

Would introduce a new domain concept for a query concern. Batched
loading is sufficient at this scale; a projection remains a future
optimization if history grows large.

### A separate use case for replacing labels

Rejected.

Reason:

It would duplicate the assignment translation and nutrition resolution
steps. A `replace` mode on the existing use case keeps one workflow.

### Authentication and per-user meals

Rejected by the owner.

Reason:

Out of scope for a single-user tool; the domain model defines no User
entity.

---

## Consequences

Positive:

- analyses survive restarts and can be reopened, re-labeled, and deleted
- history entries are self-contained: catalog changes cannot rewrite the past
- the domain model is unchanged; no immutable documentation was touched

Negative:

- six more tables to maintain
- the history list loads full aggregates, which will need a projection if the number of meals grows large
- re-seeding the food database does not affect stored meals, by design,
  which means a food renamed upstream keeps its old name in old meals

---

# ADR-016

## Title

Give Meals a User-Editable Name

---

## Status

Accepted

---

## Date

2026-09-17

---

## Context

The meal history listed meals by id and timestamp, which is hard to
scan. The owner asked to be able to rename entries.

`docs/immutable/DOMAIN_MODEL.md` enumerates the Meal attributes
(meal_id, image, food_items, nutrition_summary, created_at, updated_at)
and defines no title or note. `AI_GUIDE.md` forbids inventing domain
concepts without explicit instruction from the repository owner; the
owner has instructed this change.

---

## Decision

The Meal aggregate gains `name: str = ""` and a `rename(name)` method:

- Renaming is metadata: allowed in any meal state, and it does not
  affect measurements, nutrition, or the aggregate's state.
- An empty string clears the name; names are trimmed.
- Persisted as a `meals.name` column and surfaced in meal responses and
  history entries.
- Edited through the existing `PATCH /meals/{meal_id}` (both of its
  fields are now optional), rather than a separate endpoint.

`docs/immutable/DOMAIN_MODEL.md` is deliberately **not** modified. It may
only be changed on the owner's explicit instruction, and the divergence
is recorded here instead: the domain model document lists Meal
attributes without `name`.

---

## Alternatives Considered

### Keep the title outside the aggregate

Rejected.

Reason:

The Meal is the aggregate root; storing its name elsewhere splits the
aggregate and complicates every read.

### A dedicated PATCH /meals/{id}/name endpoint

Rejected.

Reason:

`PATCH /meals/{meal_id}` is already the meal-update endpoint and is
naturally partial; a second endpoint would add surface without benefit.

### Record renaming as a UserCorrection

Rejected.

Reason:

Corrections are per-food-item audit records about food properties;
a meal-level display name is not a nutrition correction.

---

## Consequences

Positive:

- history entries are recognisable at a glance
- renaming never risks the nutrition data

Negative:

- the domain model document and the code now diverge on one attribute
  until the owner chooses to update it
- one more column to carry through the persistence mapping

---

# ADR-017

## Title

Require the Hosted Providers (Supabase and Modal) by Default

---

## Status

Accepted

---

## Date

2026-09-18

---

## Context

The application originally defaulted to local stand-ins: a mock vision
provider, the YAML food catalog, the manual nutrition database, an
in-memory meal repository, and a SQLite `DATABASE_URL`. Those defaults
made sense while Supabase (ADR-012) and Modal (ADR-013, ADR-014) were
being built, but they left two divergent ways to run the system.

Running the defaults meant the application silently used local state:
meals disappeared on restart, the food catalog was a 12-food sample
rather than the 1,346-food database, and inference returned demo
segments. The owner asked for the hosted services to be mandatory.

---

## Decision

The defaults describe the hosted deployment, and startup validates it:

- `VISION_PROVIDER=remote`, `CATALOG_PROVIDER=sql`,
  `NUTRITION_PROVIDER=sql`, `MEAL_REPOSITORY=sql`.
- `DATABASE_URL` and `VISION_REMOTE_URL` have no default value.
- `build_dependencies` validates before wiring anything and raises one
  error listing every missing setting, naming the provider that needs it.
- The local providers stay implemented and selectable
  (`VISION_PROVIDER=mock`, `CATALOG_PROVIDER=yaml`,
  `NUTRITION_PROVIDER=manual`, `MEAL_REPOSITORY=memory`); the test suite
  depends on them, and provider replaceability is an architectural
  constraint (ARCHITECTURE.md, Constraint 6).

---

## Alternatives Considered

### Remove the local providers entirely

Rejected.

Reason:

The architecture requires every external dependency to be replaceable,
and the application tests are built on the in-process providers. Removing
them would couple the tests to network services.

### Keep local defaults and warn at startup

Rejected.

Reason:

A warning does not prevent the failure mode being fixed: silently
writing meals and analyses to local state that the user then cannot
find.

### Validate lazily on the first request

Rejected.

Reason:

Serving traffic before validating means the first user request is what
discovers a missing connection string.

---

## Consequences

Positive:

- one deployment mode; misconfiguration is loud and immediate
- no path silently writes to local state

Negative:

- a fully local run now requires four explicit environment variables
- uploaded images and crops still live on the backend host's filesystem
  (`STORAGE_PATH`); moving them to hosted object storage would be a
  separate change to `StorageProvider`

---

# ADR-018

## Title

Deploy to Vercel, Render, Supabase Storage, and Modal

---

## Status

Accepted

---

## Date

2026-09-18

---

## Context

The owner asked to deploy the application. The chosen shape is:

- Frontend: Vercel
- Backend: Render free tier
- Database: Supabase Postgres
- Images and crops: Supabase Storage
- Vision inference: Modal

Two constraints drive it. Render's free plan has no persistent disk, so
`LocalStorageProvider` cannot be used there; and Vercel functions have a
read-only filesystem apart from an ephemeral `/tmp`, plus a 60 s
execution cap on the Hobby plan that a Modal cold start can exceed.

---

## Decision

Images and crops move to Supabase Storage behind the existing
`StorageProvider` interface:

- `SupabaseStorageProvider` uploads through the Supabase Storage REST API
  (standard library only, no new dependency) and returns the object's
  **public URL** as the reference.
- The bucket is read-public. References stored in the database are
  therefore absolute URLs, which the presentation mapper and the frontend
  (`assetUrl`) already pass through untouched.
- `delete` and `retrieve` accept either that URL or a bare key, so
  references written by an earlier provider still resolve.
- `STORAGE_PROVIDER=local` keeps the filesystem provider for tests.

One application change was required: `SegmentMealUseCase` now hands the
vision provider the **local upload** rather than the storage reference,
because storage may return a URL that no model can read.

The backend deploys to Render from `render.yaml`; the frontend deploys to
Vercel from `frontend/vercel.json`.

---

## Alternatives Considered

### Keep local disk storage on a paid host

Rejected.

Reason:

It ties image availability to one machine's disk and needs a paid plan;
object storage removes the constraint entirely.

### Backend on Vercel serverless

Rejected.

Reason:

Read-only filesystem plus a 60 s cap that a Modal cold start exceeds.

### Hosted storage with signed URLs

Rejected.

Reason:

Signed URLs expire, so references stored in meals would rot. A
public-read bucket keeps stored meals permanently viewable.

---

## Consequences

Positive:

- the backend is stateless and can run on free tiers without a disk
- one storage interface, two providers, no domain changes

Negative:

- the storage bucket is publicly readable: anyone with a URL can view an
  image. Acceptable for food photos in a single-user tool; user accounts
  would change this
- the service-role key is a powerful secret and must stay in the
  environment
- meals stored before the switch point at local files that no longer
  resolve; those images are gone unless they are re-uploaded
- Render's free tier spins down after idle, so the first request
  afterwards is slow

---

# Future ADRs

New architectural decisions should be appended below.

Format:

```
ADR-NNN

Title

Status

Context

Decision

Alternatives Considered

Consequences
```

Never rewrite previous decisions.
