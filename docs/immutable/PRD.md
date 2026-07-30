# Product Requirements Document (PRD)

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 1.0  
**Status:** Immutable  
**Last Updated:** 2026-07-30

---

# 1. Vision

Image-based Food Nutrition Estimation (I-FNE) is a modular computer vision system that estimates nutritional information from a single food image.

Rather than treating artificial intelligence as an all-knowing decision maker, I-FNE treats computer vision as an assistant that generates an initial understanding of a meal. Users may review and refine the prediction before nutritional information is calculated.

The project aims to demonstrate how modern computer vision can be integrated into a production-oriented software system using clean architecture and modular engineering principles.

---

# 2. Problem Statement

Food nutrition tracking is traditionally performed manually.

Users typically need to:

- search every food item,
- estimate portion size,
- manually calculate calories,
- manually compute macronutrients,
- repeat the process for every meal.

This process is time-consuming and discourages long-term dietary tracking.

Recent computer vision models can recognize food from images, but most existing systems stop immediately after inference.

Typical workflow:

```
Image

↓

Food Classification

↓

Nutrition Result
```

Real-world usage is significantly more complicated.

Challenges include:

- multiple food items
- uncertain predictions
- ambiguous food categories
- invisible ingredients
- different nutrition databases
- changing AI models
- changing datasets

I-FNE addresses these challenges through a modular architecture where AI is only one component of a larger workflow.

---

# 3. Project Objectives

The primary objectives are:

- build a production-oriented computer vision system
- demonstrate modular software architecture
- separate AI implementation from business logic
- support interchangeable computer vision models
- support interchangeable nutrition databases
- support future experimentation without redesigning the application

---

# 4. Target Users

## Primary User

People who want a quick estimation of meal nutrition from images.

Typical workflow:

- upload meal image
- review AI prediction
- optionally edit detected foods
- obtain nutrition estimation
- save meal history

---

## Secondary User

Developers and researchers exploring modular computer vision system design.

---

# 5. Project Scope

The system SHALL support:

- image upload
- multiple food detection
- food segmentation
- food recognition
- physical property estimation
- nutrition estimation
- user correction
- nutrition recalculation
- meal persistence
- modular AI providers
- modular nutrition providers

---

# 6. Out of Scope

The following features are intentionally excluded.

## Medical

- disease diagnosis
- medical advice
- treatment recommendation

---

## Nutrition

- personalized diet plans
- allergy recommendation
- personalized calorie goals
- meal planning

---

## Computer Vision

- real-time video processing
- multi-camera reconstruction
- automatic invisible ingredient inference
- perfect portion estimation
- state-of-the-art benchmark competition

---

# 7. Product Principles

## AI Assists Humans

AI provides suggestions.

Users remain the final decision maker.

---

## Human-in-the-loop

Users can refine predictions before nutrition calculation.

Human correction is considered part of the normal workflow.

---

## Modular Design

Every AI component should be replaceable without redesigning the system.

---

## Provider Independence

External services must remain interchangeable.

Examples:

- computer vision models
- nutrition databases
- storage providers

---

## Domain-driven Design

Business entities are independent from implementation details.

---

# 8. Functional Requirements

## FR-01 Image Upload

The system shall allow users to upload a meal image.

Supported formats:

- JPEG
- PNG

---

## FR-02 Food Detection

The system shall detect one or more food objects within the uploaded image.

---

## FR-03 Food Segmentation

The system shall generate segmentation masks for detected food objects whenever supported by the selected vision provider.

---

## FR-04 Food Recognition

The system shall classify each detected food object into a VisionClass.

---

## FR-05 Physical Measurement

The system shall estimate available physical properties required for nutrition estimation.

Examples include:

- relative size
- relative area
- estimated volume
- estimated weight

The estimation method is implementation-dependent.

---

## FR-06 Canonical Food Resolution

The system shall convert VisionClass into CanonicalFood before nutrition lookup.

This mapping is independent from AI implementation.

---

## FR-07 Nutrition Resolution

The system shall retrieve nutritional information from the configured Nutrition Provider.

---

## FR-08 Nutrition Calculation

The system shall calculate:

- calories
- macronutrients
- micronutrients

for every detected food item.

---

## FR-09 User Correction

The system shall allow users to modify AI predictions before final nutrition calculation.

Possible edits include:

- changing food category
- deleting incorrect items
- adding missing items
- editing ingredient information
- adjusting measurements

---

## FR-10 Nutrition Recalculation

The system shall recalculate nutritional information after user corrections.

---

## FR-11 Meal Persistence

The system shall persist completed meal records for future retrieval.

---

# 9. Non-functional Requirements

## NFR-01 Maintainability

The system shall use modular architecture with clear separation between:

- domain
- application
- infrastructure
- presentation

---

## NFR-02 Extensibility

Computer vision providers shall be replaceable without changing business logic.

Nutrition providers shall be replaceable without changing business logic.

---

## NFR-03 Scalability

The architecture shall support additional:

- AI providers
- nutrition databases
- storage implementations

without major redesign.

---

## NFR-04 Testability

Business logic shall be independently testable without requiring AI models.

---

## NFR-05 Portability

The application shall support containerized deployment.

---

## NFR-06 API-first Design

All application functionality shall be exposed through REST APIs.

---

# 10. User Workflow

The expected user workflow is:

```
Upload Meal Image
        │
        ▼
Vision Analysis
        │
        ▼
Meal Draft Generation
        │
        ▼
User Review
        │
        ▼
Optional Corrections
        │
        ▼
Nutrition Calculation
        │
        ▼
Meal Saved
```

---

# 11. Success Criteria

The project is considered successful if it demonstrates:

- modular architecture
- clean software engineering practices
- interchangeable AI providers
- interchangeable nutrition providers
- maintainable domain model
- complete end-to-end workflow
- human-in-the-loop interaction

Model accuracy alone is **not** considered the primary success metric.

---

# 12. Future Vision

Future versions of I-FNE may include:

- ingredient-level reasoning
- confidence-aware interaction
- personalized nutrition profiles
- continual learning
- meal recommendation
- active learning pipeline
- multiple nutrition providers
- foundation vision-language models

These features are intentionally excluded from the current project scope but should be supported by the existing architecture.

---

# 13. Immutable Policy

This document defines the long-term product vision.

It MUST NOT be modified automatically by AI agents.

Changes are only allowed when explicitly requested by the repository owner because they may affect the entire architecture, domain model, and implementation.
