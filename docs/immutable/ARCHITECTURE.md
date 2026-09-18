# System Architecture

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 1.0  
**Status:** Immutable  
**Last Updated:** 2026-07-30

---

# Purpose

This document defines the high-level architecture of the Image-based Food Nutrition Estimation (I-FNE) system.

The architecture prioritizes:

- Maintainability
- Modularity
- Testability
- Extensibility
- Provider Independence

Implementation details (frameworks, models, databases, APIs) are intentionally excluded from this document.

---

# Architectural Philosophy

The application is **NOT** an AI model.

The application is a software system that happens to use AI.

Computer vision is treated as one infrastructure component among many.

The software architecture should remain stable even if every AI model is replaced.

---

# Architectural Principles

## 1. Domain First

The business domain is the center of the application.

Everything else exists to support the domain.

```
Infrastructure

↓

Application

↓

Domain
```

The Domain must never depend on Infrastructure.

---

## 2. AI as Infrastructure

Computer vision is considered an infrastructure service.

The Domain must never know:

- YOLO
- Florence
- SAM
- EfficientNet
- MiDaS
- OpenCV
- PyTorch

Instead, it depends only on interfaces.

---

## 3. External Providers are Replaceable

External dependencies should always be hidden behind adapters.

Examples include:

- Vision models
- Nutrition databases
- Object storage
- Relational databases
- Cache providers

---

## 4. Human-in-the-loop

The architecture assumes AI predictions are imperfect.

Human correction is a normal workflow rather than an exception.

---

# System Overview

```
                   Client
                      │
                      ▼
               Presentation Layer
                      │
                      ▼
              Application Layer
                      │
                      ▼
                 Domain Layer
               ▲              ▲
               │              │
               │              │
       Infrastructure     Infrastructure
        (Vision)          (Nutrition)
```

The Domain is the center of the architecture.

Infrastructure provides implementations.

---

# Layer Responsibilities

## Presentation Layer

Responsibilities

- REST API
- DTOs
- Validation
- Authentication
- Serialization

Must NOT contain

- business rules
- AI logic
- database logic

---

## Application Layer

Responsibilities

- use cases
- workflow orchestration
- transaction coordination
- provider coordination

Examples

- Analyze Meal
- Finalize Meal
- Update Meal
- Calculate Nutrition

The Application layer coordinates Domain objects.

---

## Domain Layer

Responsibilities

- entities
- business rules
- interfaces
- value objects

The Domain defines:

- what the system is
- how it behaves

The Domain must never import:

- FastAPI
- SQLAlchemy
- OpenCV
- PyTorch
- PostgreSQL
- Redis

---

## Infrastructure Layer

Responsibilities

- AI providers
- databases
- storage
- cache
- third-party APIs

Infrastructure implements interfaces defined by the Domain.

---

# High-Level Workflow

```
Upload Image
      │
      ▼
Vision Provider (segmentation + depth)
      │
      ▼
Segments
      │
      ▼
User Labeling (human-in-the-loop)
      │
      ▼
CanonicalFood + Measurement
      │
      ▼
Nutrition Resolution
      │
      ▼
Nutrition Calculation
      │
      ▼
Meal Draft
      │
      ▼
User Review
      │
      ▼
Correction
      │
      ▼
Final Meal
```

---

# Vision Pipeline

Computer vision performs two observation tasks:

1. Segmentation — split the image into food regions (crops).
2. Depth estimation — produce a relative depth map used for portion estimation.

Label suggestions are optional and never authoritative.

```
Image

↓

Vision Provider (segmentation + depth)

↓

Segments (crops + mask statistics)

↓

User Labels (human-in-the-loop)

↓

Food Items
```

The pipeline must never calculate nutrition directly.

---

# Nutrition Pipeline

The nutrition pipeline begins **after** computer vision.

```
VisionClass

↓

CanonicalFood

↓

Nutrition Provider

↓

Nutrition Profile

↓

Nutrition Summary
```

Computer vision and nutrition are intentionally separated.

---

# Human Correction Pipeline

User interaction is part of the architecture.

Labeling segments is the primary mapping step, not an exception.

```
Segments (crops)

↓

User Review

↓

User Labels (assign CanonicalFood to segments)

↓

Food Items

↓

Optional Corrections (weight, ingredients, food change)

↓

Final Meal

↓

Nutrition Calculation
```

Corrections become part of the domain.

---

# Vision Provider Architecture

```
Application

↓

VisionProvider Interface

↓

Adapter

↓

Implementation
```

Examples

```
VisionProvider

├── MockSegmentationProvider

├── SAM3SegmentationProvider

├── YOLODepthProvider

└── Future Providers
```

Application never depends on implementations.

---

# Nutrition Provider Architecture

```
Application

↓

NutritionProvider Interface

↓

Adapter

↓

Implementation
```

Examples

```
NutritionProvider

├── PangankuProvider

├── USDAProvider

├── ManualProvider

└── Future Providers
```

The Application only depends on the interface.

---

# Canonical Mapping

Vision models may produce different labels.

The application standardizes them.

```
VisionClass

↓

CanonicalFood
```

Example

```
hamburger

↓

Burger
```

```
cheeseburger

↓

Burger
```

Business logic only understands CanonicalFood.

---

# Dependency Flow

Allowed

```
Presentation

↓

Application

↓

Domain

↑

Infrastructure
```

Infrastructure implements Domain interfaces.

---

Not Allowed

```
Domain

↓

Infrastructure
```

```
Presentation

↓

Infrastructure
```

```
Business Logic

↓

YOLO
```

```
Business Logic

↓

Panganku
```

---

# Data Flow

```
Client

↓

REST API

↓

Application Service

↓

Vision Provider

↓

Vision Result

↓

Canonical Mapping

↓

Measurement

↓

Nutrition Provider

↓

Nutrition Calculation

↓

Meal Draft

↓

User Confirmation

↓

Persistence

↓

Response
```

---

# Extension Points

The architecture intentionally supports replacement of the following components.

## Vision

- Segmentation (SAM-style)
- Depth estimation
- Optional label suggestion
- Foundation Models

---

## Nutrition

- Panganku
- USDA
- Manual Dataset
- Future Providers

---

## Persistence

- PostgreSQL
- SQLite
- MySQL
- Future Databases

---

## Storage

- Local Storage
- S3-compatible Storage
- Future Providers

---

# Error Handling Strategy

Errors are handled according to their layer.

Presentation

- Validation errors

Application

- Workflow failures

Domain

- Business rule violations

Infrastructure

- Network failures
- AI inference failures
- Database failures

Infrastructure exceptions must never leak directly into the Domain.

---

# Testing Strategy

Testing follows the architecture.

Priority

```
Domain

↓

Application

↓

Infrastructure

↓

Presentation
```

The Domain should have the highest test coverage.

AI models are tested separately.

---

# Scalability

The architecture supports future additions without redesign.

Examples

- new vision models
- new nutrition providers
- multiple AI pipelines
- asynchronous inference
- batch processing
- distributed deployment

---

# Frontend and Backend Pipeline

                  Browser

                     │

                     ▼

         Frontend (React/Vite)

                     │
              REST API (HTTP)

                     │

                     ▼

          Backend (FastAPI)

                     │

         Application Layer

                     │

             Domain Layer

                     ▲

             Infrastructure

The frontend is responsible only for user interaction and visualization. All business logic, AI inference, and nutrition calculation reside in the backend.

---

# Frontend Architecture

The frontend is intentionally separated from the backend.

Responsibilities

- image upload
- displaying AI results
- human correction UI
- nutrition visualization

The frontend must never contain:

- nutrition calculation
- business rules
- AI inference
- provider-specific logic

All business logic resides in the backend.

The frontend communicates exclusively through the REST API.

---

# Architectural Constraints

The following constraints must always hold.

## Constraint 1

Business logic must not depend on AI frameworks.

---

## Constraint 2

Business logic must not depend on database implementations.

---

## Constraint 3

Computer vision must not calculate nutrition directly.

---

## Constraint 4

Nutrition providers must never receive VisionClass.

They only receive CanonicalFood.

---

## Constraint 5

Every provider must implement an interface.

---

## Constraint 6

Every external dependency must be replaceable.

---

## Constraint 7

User corrections always override AI predictions.

---

## Constraint 8

Nutrition is calculated from the final corrected meal.

---

# Architecture Goals

The architecture should remain stable while allowing:

- new AI models
- new nutrition sources
- new APIs
- new databases
- new frontends

without requiring changes to the Domain layer.

---

# Immutable Policy

This document defines the architectural foundation of the repository.

It MUST NOT be modified automatically by AI agents.

Architectural changes require explicit approval from the repository owner because they affect every layer of the system.
