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
