# Current Implementation

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 0.1.0  
**Status:** Mutable  
**Last Updated:** 2026-07-30

---

# Purpose

This document tracks the current implementation status of the project.

Unlike the PRD or Architecture documents, this file evolves continuously throughout development.

Whenever implementation changes, this document should be updated accordingly.

---

# Project Status

Current Phase

```
Project Initialization
```

Overall Progress

```
██████░░░░░░░░░░░░░░░░░░░░░░ 20%
```

Current Milestone

```
Project Foundation
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

docs/

├── immutable/
└── mutable/

tests/

├── domain/
├── application/
├── infrastructure/
└── presentation/
```

---

# Vision Pipeline

Status

```
Planning
```

Target abstraction

```text
VisionProvider

↓

VisionPrediction

↓

CanonicalFood
```

Planned providers

- MockVisionProvider
- FlorenceProvider
- YOLO-based Provider
- Future Vision-Language Models

The application must never depend on a specific provider.

---

# Nutrition Pipeline

Status

```
Planning
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
Planning
```

Purpose

Convert provider-specific prediction labels into business entities.

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

The mapping layer is mandatory.

Business logic must never consume VisionClass directly.

---

# Measurement Pipeline

Status

```
Planning
```

Responsibilities

- area estimation
- volume estimation
- weight estimation

Implementation details are provider-dependent.

Business logic only consumes standardized measurements.

---

# Human Correction Pipeline

Status

```
Planned
```

Users will be able to

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
Planning
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

---

# Storage

Status

```
Planning
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
Planning
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
Planning
```

Configuration should be managed through

- environment variables
- configuration objects

No hardcoded infrastructure configuration.

---

# Logging

Status

```
Planning
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
Planning
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
| Domain | Planned |
| Application | Planned |
| Infrastructure | Planned |
| Presentation | Planned |

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
Not Implemented
```

Purpose

Standard interface for all computer vision providers.

---

## NutritionProvider

Status

```
Not Implemented
```

Purpose

Standard interface for all nutrition providers.

---

## MealRepository

Status

```
Not Implemented
```

Purpose

Persistence abstraction for Meal aggregates.

---

## StorageProvider

Status

```
Not Implemented
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
