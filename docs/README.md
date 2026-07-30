# Documentation

This directory contains the project documentation for **Image-based Food Nutrition Estimation (I-FNE)**.

The project follows **Spec-Driven Development (SDD)**, where documentation acts as the single source of truth before implementation.

---

# Documentation Philosophy

Documentation is divided into two categories:

- **Immutable Documents**
- **Mutable Documents**

This separation ensures the project's long-term vision remains stable while allowing implementation details to evolve over time.

---

# Immutable Documents

Immutable documents define the project's foundation.

They should remain stable throughout the project's lifecycle and must only be modified when the repository owner explicitly changes the product vision, business domain, or architecture.

AI agents **must not** modify these documents automatically.

| Document | Purpose |
|----------|---------|
| `immutable/PRD.md` | Product vision, goals, requirements, and project scope |
| `immutable/DOMAIN_MODEL.md` | Core business entities and relationships |
| `immutable/ARCHITECTURE.md` | High-level system architecture and design principles |
| `immutable/AI_GUIDE.md` | Development rules and AI implementation guidelines |
| `immutable/CODING_STANDARDS.md` | Coding conventions and architectural rules |

---

# Mutable Documents

Mutable documents evolve together with implementation.

Whenever implementation changes, these documents should also be updated.

AI agents are encouraged to keep these documents synchronized with the codebase.

| Document | Purpose |
|----------|---------|
| `mutable/API_SPEC.md` | REST API specification |
| `mutable/IMPLEMENTATION.md` | Current implementation details |
| `mutable/ROADMAP.md` | Development roadmap |
| `mutable/DECISIONS.md` | Architecture Decision Records (ADR) |
| `mutable/CHANGELOG.md` | User-visible project changes |

---

# Reading Order

Before implementing any feature, read the documentation in the following order.

1. `immutable/PRD.md`
2. `immutable/DOMAIN_MODEL.md`
3. `immutable/ARCHITECTURE.md`
4. `immutable/CODING_STANDARDS.md`
5. `immutable/AI_GUIDE.md`
6. `mutable/IMPLEMENTATION.md`
7. `mutable/API_SPEC.md`

This order ensures that implementation decisions follow the product vision, domain model, and architecture before considering implementation details.

---

# Updating Documentation

## When Product Vision Changes

Update:

- `immutable/PRD.md`

---

## When Business Domain Changes

Update:

- `immutable/DOMAIN_MODEL.md`

---

## When Architecture Changes

Update:

- `immutable/ARCHITECTURE.md`

Append a new Architecture Decision Record to:

- `mutable/DECISIONS.md`

---

## When APIs Change

Update:

- `mutable/API_SPEC.md`

---

## When Implementation Changes

Update:

- `mutable/IMPLEMENTATION.md`

---

## When Milestones Change

Update:

- `mutable/ROADMAP.md`

---

## When User-visible Features Change

Update:

- `mutable/CHANGELOG.md`

---

# Architecture Principles

The project follows several architectural principles.

- Clean Architecture
- Domain-Driven Design (DDD)
- SOLID Principles
- Dependency Inversion
- Interface-based Programming
- Adapter Pattern
- Spec-Driven Development

---

# Design Goals

The system should be:

- Modular
- Testable
- Maintainable
- Extensible
- Provider-independent
- Model-independent

Business logic should remain independent from:

- Computer vision models
- Nutrition databases
- Storage providers
- External APIs
- Frontend technologies

---

# AI Provider Philosophy

Computer vision models are treated as interchangeable plugins.

The application should never depend directly on:

- YOLO
- SAM
- Florence
- EfficientNet
- CLIP
- MiDaS

Instead, all providers must implement common interfaces defined by the Domain layer.

---

# Nutrition Provider Philosophy

Nutrition data sources are also interchangeable.

Possible providers include:

- Panganku
- USDA FoodData Central
- Manual datasets
- Future custom datasets

Business logic must only interact with a Nutrition Provider abstraction.

---

# Architecture Decision Records

Architectural decisions are documented using ADR (Architecture Decision Records).

Rules:

- Never edit previous ADRs.
- Never delete previous ADRs.
- Always append new ADRs.
- Reference previous ADRs when necessary.

---

# Contributing

Before implementing a new feature:

1. Read the required documentation.
2. Verify the feature aligns with the PRD.
3. Reuse existing abstractions whenever possible.
4. Avoid introducing duplicate concepts.
5. Keep documentation synchronized with implementation.

---

# Repository Goal

This repository is intended to demonstrate how a production-quality computer vision system can be designed and implemented using modern software engineering practices.

The project emphasizes architecture, modularity, and maintainability as much as computer vision itself.
