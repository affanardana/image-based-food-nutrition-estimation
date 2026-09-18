# AGENTS.md

# Image-based Food Nutrition Estimation (I-FNE)

This repository follows **Spec-Driven Development (SDD)**.

The primary objective of this project is to build a **modular, maintainable, and production-oriented computer vision system** for image-based food nutrition estimation.

The project prioritizes software engineering, system architecture, and extensibility over achieving state-of-the-art AI performance.

---

# Development Philosophy

This repository follows several principles:

- Specification First
- Domain Driven Design (DDD)
- Clean Architecture
- SOLID Principles
- Interface-based Programming
- Dependency Inversion
- Modular AI Components

Business logic must remain independent from AI models, databases, and external services.

---

# Documentation Structure

The documentation is divided into two groups.

## Immutable Documents

These documents define the long-term architecture and business domain.

AI agents MUST NOT modify them unless explicitly instructed by the repository owner.

```
docs/immutable/
├── PRD.md
├── DOMAIN_MODEL.md
├── ARCHITECTURE.md
├── AI_GUIDE.md
└── CODING_STANDARDS.md
```

---

## Mutable Documents

These documents evolve together with implementation.

AI agents MAY update them whenever implementation changes.

```
docs/mutable/
├── API_SPEC.md
├── IMPLEMENTATION.md
├── ROADMAP.md
├── DECISIONS.md
└── CHANGELOG.md
```

---

# Required Reading Order

Before implementing any feature, AI agents MUST read the following documents in order.

1. docs/immutable/PRD.md
2. docs/immutable/DOMAIN_MODEL.md
3. docs/immutable/ARCHITECTURE.md
4. docs/immutable/CODING_STANDARDS.md
5. docs/immutable/AI_GUIDE.md
6. docs/mutable/IMPLEMENTATION.md
7. docs/mutable/API_SPEC.md

Never skip this reading order.

---

# Repository Goals

The repository aims to demonstrate a complete production-ready AI system instead of a model demo.

The repository should demonstrate knowledge of:

- Computer Vision
- Software Engineering
- Backend Engineering
- Clean Architecture
- AI System Design
- Modular AI Pipelines

---

# Project Scope

The system should:

- Analyze food images.
- Detect food objects.
- Estimate physical properties.
- Resolve nutritional information.
- Allow user correction.
- Produce nutritional summaries.

The system should NOT:

- Diagnose diseases.
- Recommend medical treatments.
- Replace dietitians.
- Guarantee nutritional accuracy.
- Infer invisible ingredients with certainty.

---

# Execution Policy (WARNING. MUST REMEMBER)

The repository owner is responsible for executing all commands in the local development environment.

AI agents must **NOT** execute commands that modify the local environment or start local services unless explicitly instructed by the repository owner.

This includes, but is not limited to:

- `uv sync`
- `uv add`
- `pip install`
- `npm install`
- `npm run dev`
- `npm run build`
- `uv run`
- `uvicorn`
- `pytest`
- `ruff`
- `mypy`
- `docker compose up`
- `docker build`
- `alembic upgrade`
- database migrations

Instead of executing commands, AI agents must provide the exact commands for the repository owner to run manually.

Example

Instead of executing:

```bash
uv run pytest tests/
```

Respond with:

```text
Please run:

uv run pytest tests/

Then share the complete output so I can verify the results and determine the next steps.
```

The repository owner will execute commands and provide logs, error messages, screenshots, or terminal output when verification is required.

AI agents should use those outputs to:

- verify implementation
- diagnose issues
- suggest fixes
- determine the next development step

AI agents must never assume a command succeeded unless the repository owner provides its output.

The repository owner is responsible for:

- installing dependencies
- running tests
- starting development servers
- applying database migrations
- managing local services
- verifying runtime behavior

---

# Git Policy (WARNING. MUST REMEMBER)

The repository owner has exclusive control over the Git history.

AI agents must **NOT** perform Git operations that modify the repository state unless explicitly instructed.

This includes, but is not limited to:

- `git init`
- `git add`
- `git commit`
- `git commit --amend`
- `git reset`
- `git restore`
- `git rebase`
- `git merge`
- `git cherry-pick`
- `git stash`
- `git tag`
- `git push`
- `git pull`
- `git fetch`
- creating or deleting branches

Instead, AI agents should describe the recommended Git commands for the repository owner to execute manually.

Example

Instead of committing changes, respond with:

```text
Suggested commit:

git add .
git commit -m "feat: implement mock vision provider"

Please review the changes before committing.
```

The repository owner is responsible for:

- reviewing code changes
- managing branches
- creating commits
- resolving merge conflicts
- pushing changes to remote repositories

---

# Architectural Principles

## AI is a Component

Computer vision is only one component of the system.

Business logic must never depend directly on AI implementations.

---

## Modular Providers

External technologies must be replaceable.

Examples include:

- Vision models
- Nutrition databases
- Storage providers
- External APIs

Implementation details should remain inside Infrastructure.

---

## Domain First

Business entities are the source of truth.

AI models produce observations.

Business rules interpret observations.

---

## Human-in-the-loop

Human correction is considered a first-class feature.

The system should allow users to:

- review predictions
- edit food items
- edit ingredients
- confirm nutritional estimation

---

# Layer Responsibilities

## Domain

Contains:

- entities
- value objects
- business rules
- interfaces

Must never import infrastructure.

---

## Application

Contains:

- use cases
- workflows
- orchestration

Application coordinates domain objects.

---

## Infrastructure

Contains:

- databases
- AI models
- external APIs
- storage
- providers

Infrastructure implements interfaces defined by Domain.

---

## Presentation

Contains:

- REST API
- DTOs
- validation
- serialization

No business logic.

---

# Dependency Rule

Allowed

Presentation
↓

Application
↓

Domain

Infrastructure
↓

Domain

Infrastructure
↓

Application (through interfaces only)

Not Allowed

Domain
↓

Infrastructure

Presentation
↓

Infrastructure

AI Provider
↓

Database directly

Business Logic
↓

Provider-specific classes

---

# Vision Providers

Every computer vision implementation must implement a common interface.

Examples:

- MockVisionProvider
- YOLOProvider
- FlorenceProvider
- SAMProvider

Upper layers must never know which provider is currently used.

---

# Nutrition Providers

Nutrition sources must also be replaceable.

Examples:

- PangankuProvider
- USDAProvider
- ManualProvider

The Nutrition Provider only accepts CanonicalFood.

It must never receive VisionClass.

---

# Mapping Flow

The system follows this mapping pipeline.

```
Vision Model
      │
      ▼
VisionClass
      │
      ▼
CanonicalFood
      │
      ▼
NutritionProvider
      │
      ▼
NutritionProfile
```

Do not bypass this mapping.

---

# Interface First

When integrating new technologies:

DO NOT expose third-party APIs directly.

Instead:

```
Application

↓

Interface

↓

Adapter

↓

Implementation
```

Every external dependency should be hidden behind an interface.

---

# AI Model Integration

AI models should be treated as interchangeable plugins.

Never write code that depends on:

- YOLO
- EfficientNet
- SAM
- MiDaS
- Florence
- CLIP

Instead depend on interfaces.

---

# Documentation Rules

Immutable documents

Must never be modified automatically.

Mutable documents

Should always be synchronized with implementation.

Whenever implementation changes:

Update

- IMPLEMENTATION.md

Whenever APIs change:

Update

- API_SPEC.md

Whenever roadmap changes:

Update

- ROADMAP.md

Whenever architectural decisions are made:

Append ADR into

- DECISIONS.md

Whenever user-visible functionality changes:

Update

- CHANGELOG.md

---

# Architecture Decision Records

Never edit previous ADRs.

Always append a new ADR.

Previous decisions are considered historical records.

---

# Frontend and Backend decision

Backend and frontend are independent applications.

Backend owns:

- business logic
- AI inference
- persistence

Frontend owns:

- user interaction
- visualization
- API communication

Never move business logic into the frontend.

Whenever possible, backend APIs should remain backward-compatible so that frontend changes are minimized.

---

# Coding Principles

Prefer:

- Composition over inheritance
- Small functions
- Small services
- Explicit interfaces
- Dependency injection
- Type annotations
- Immutable value objects whenever reasonable

Avoid:

- God Objects
- Circular dependencies
- Hidden side effects
- Singleton abuse
- Tight coupling
- Global mutable state

---

# Error Handling

Business errors should be represented as domain errors.

Infrastructure exceptions should never leak into the Domain layer.

---

# Logging

Prefer structured logging.

Never log:

- passwords
- secrets
- tokens
- personal information

---

# Testing Philosophy

Prioritize:

1. Domain tests
2. Application tests
3. Integration tests
4. Provider tests

Avoid testing implementation details.

Test observable behavior.

---

# Versioning

Documentation should evolve together with the implementation.

Implementation changes without documentation updates are considered incomplete.

---

# AI Agent Behavior

When implementing new features:

1. Read required documentation.
2. Reuse existing abstractions.
3. Avoid introducing duplicate concepts.
4. Prefer extending existing providers.
5. Keep architecture consistent.
6. Update mutable documentation.
7. Never modify immutable documentation unless explicitly instructed.

If architectural uncertainty exists, stop implementation and request clarification instead of inventing a new architecture.

---

# Repository Principle

The repository should always look like a production software project that happens to use AI, rather than an AI notebook wrapped inside a web application.
