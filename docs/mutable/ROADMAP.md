# Roadmap

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 1.0  
**Status:** Mutable  
**Last Updated:** 2026-07-30

---

# Purpose

This roadmap describes the planned evolution of the project.

Unlike the PRD, this document is expected to change frequently as development progresses.

Features, priorities, and milestones may be reordered as new requirements emerge.

---

# Overall Vision

```
Project Setup
        │
        ▼
Core Domain
        │
        ▼
Vision Pipeline
        │
        ▼
Nutrition Pipeline
        │
        ▼
Human Correction
        │
        ▼
Persistence
        │
        ▼
Production-ready MVP
```

---

# Milestones

| Version | Status | Goal |
|----------|--------|------|
| v0.1 | 🚧 In Progress | Project foundation |
| v0.2 | ⏳ Planned | Core Domain (Backend Domain + Backend API + Frontend MVP + Integration) |
| v0.3 | ⏳ Planned | Vision Pipeline |
| v0.4 | ⏳ Planned | Nutrition Pipeline |
| v0.5 | ⏳ Planned | Human Correction |
| v0.6 | ⏳ Planned | Persistence |
| v0.7 | ⏳ Planned | API Stabilization |
| v0.8 | ⏳ Planned | Testing & Quality |
| v0.9 | ⏳ Planned | Production Hardening |
| v1.0 | ⏳ Planned | MVP Release |

---

# v0.1 — Project Foundation

Status

```
In Progress
```

Objectives

- Repository initialization
- Documentation
- Clean Architecture
- Project structure
- Development workflow
- CI preparation

Deliverables

- Immutable documentation
- Mutable documentation
- Initial project structure
- AGENTS.md

Exit Criteria

- Documentation completed
- Repository structure finalized

---

# v0.2 — Core Domain

Status

```
Planned
```

Objectives

Implement the business domain.

Deliverables

- Meal entity
- FoodItem entity
- NutritionProfile
- Measurement
- Value Objects
- Repository interfaces
- Provider interfaces
- Domain exceptions

Exit Criteria

- Domain contains no infrastructure dependency
- Unit tests for domain layer

---

# v0.3 — Vision Pipeline

Status

```
Planned
```

Objectives

Introduce provider-independent computer vision.

Deliverables

- VisionProvider interface
- MockVisionProvider
- VisionPrediction model
- Canonical mapper
- AnalyzeMeal use case

Stretch Goals

- First real provider implementation
- Segmentation support

Exit Criteria

- Vision providers can be swapped without changing Application layer

---

# v0.4 — Nutrition Pipeline

Status

```
Planned
```

Objectives

Transform recognized foods into nutrition information.

Deliverables

- NutritionProvider interface
- PangankuProvider
- NutritionResolver
- NutritionProfile generation
- NutritionSummary aggregation

Stretch Goals

- USDAProvider

Exit Criteria

- Nutrition provider interchangeable
- Canonical mapping completed

---

# v0.5 — Human Correction

Status

```
Planned
```

Objectives

Introduce human-in-the-loop workflow.

Deliverables

- Food replacement
- Food deletion
- Food addition
- Ingredient editing
- Weight adjustment
- Nutrition recalculation

Exit Criteria

- User corrections override AI predictions

---

# v0.6 — Persistence

Status

```
Planned
```

Objectives

Persist meal history.

Deliverables

- MealRepository implementation
- PostgreSQL support
- SQLite development support
- Image storage abstraction

Stretch Goals

- Object storage support

Exit Criteria

- Meals can be retrieved and updated

---

# v0.7 — API Stabilization

Status

```
Planned
```

Objectives

Expose stable REST APIs.

Deliverables

- Analyze endpoint
- Update endpoint
- Search endpoint
- Validation
- Error responses
- OpenAPI documentation

Exit Criteria

- API specification synchronized with implementation

---

# v0.8 — Testing & Quality

Status

```
Planned
```

Objectives

Improve reliability.

Deliverables

- Domain tests
- Application tests
- Integration tests
- Provider tests
- Static analysis
- Linting

Stretch Goals

- Coverage reporting

Exit Criteria

- Stable automated test suite

---

# v0.9 — Production Hardening

Status

```
Planned
```

Objectives

Prepare for deployment.

Deliverables

- Docker
- Configuration management
- Structured logging
- Health checks
- Performance improvements
- Error monitoring

Stretch Goals

- Metrics
- Distributed tracing

Exit Criteria

- Deployable backend service

---

# v1.0 — MVP Release

Status

```
Planned
```

Objectives

Deliver the first complete working system.

Features

- Image upload
- Food detection
- Food segmentation
- Canonical mapping
- Nutrition estimation
- Human correction
- Meal persistence
- REST API
- Automated tests

Success Criteria

- End-to-end workflow operational
- Modular provider architecture
- Clean documentation
- Stable API

---

# Future Roadmap

These features are intentionally outside the MVP.

## v1.1

Potential improvements

- Better portion estimation
- Improved correction UX
- Multiple nutrition providers
- Better ingredient editing

---

## v1.2

Potential improvements

- Vision-language models
- Confidence-aware UI
- Better canonical mapping
- Batch image analysis

---

## v1.5

Potential improvements

- Active learning pipeline
- User feedback collection
- Provider benchmarking
- Automatic model selection

---

## v2.0

Long-term vision

- Foundation vision models
- Ingredient-level reasoning
- Multiple image support
- Personalized nutrition
- Continual learning
- Plugin ecosystem

---

# Backlog

Ideas that may be implemented in the future.

## Computer Vision

- Foundation models
- Open-vocabulary detection
- Better segmentation
- Depth estimation improvements
- Portion estimation improvements

---

## Nutrition

- Multiple nutrition databases
- Nutrition source comparison
- Food density calibration
- Country-specific nutrition providers

---

## Backend

- Authentication
- Background jobs
- Caching
- Rate limiting
- Provider configuration
- Admin dashboard

---

## Developer Experience

- CLI tools
- Provider templates
- Local demo dataset
- Mock providers
- Benchmark utilities

---

# Definition of Done

A milestone is considered complete when:

- Feature implemented
- Tests added
- Documentation updated
- API updated (if applicable)
- Changelog updated
- No architectural rules violated

---

# Maintenance

Whenever implementation changes:

- Update milestone progress.
- Move completed items to previous milestones if necessary.
- Keep future milestones realistic.
- Do not delete historical milestones.

This roadmap should evolve together with the project while preserving the long-term architectural vision defined by the immutable documents.
