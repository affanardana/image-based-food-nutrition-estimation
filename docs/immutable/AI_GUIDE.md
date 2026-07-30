# AI Development Guide

# Image-based Food Nutrition Estimation (I-FNE)

**Version:** 1.0  
**Status:** Immutable  
**Audience:** AI Coding Agents (Claude Code, Gemini CLI, Cursor, GitHub Copilot, etc.)

---

# Purpose

This document defines how AI coding agents should understand, navigate, and contribute to this repository.

Unlike the PRD or Architecture documents, this guide focuses on **how implementation should be performed**, not **what the product should do**.

Before modifying any code, AI agents MUST read this document.

---

# Repository Identity

This repository is a **production-oriented software engineering project**.

It is **NOT**:

- a research repository
- a collection of notebooks
- a benchmark implementation
- a model zoo

The repository demonstrates how to build an AI-powered software system using modern software engineering principles.

---

# Project Priorities

Always prioritize, in order:

1. Correct architecture
2. Maintainability
3. Readability
4. Extensibility
5. Testability
6. Performance
7. AI accuracy

Improving model accuracy should never significantly degrade software architecture.

---

# Required Reading Order

Before implementing any feature, read the following documents.

1.

```
docs/immutable/PRD.md
```

2.

```
docs/immutable/DOMAIN_MODEL.md
```

3.

```
docs/immutable/ARCHITECTURE.md
```

4.

```
docs/immutable/CODING_STANDARDS.md
```

5.

```
docs/mutable/IMPLEMENTATION.md
```

6.

```
docs/mutable/API_SPEC.md
```

Never skip this order.

---

# Documentation Rules

The repository contains two documentation categories.

## Immutable

Must NOT be modified automatically.

```
docs/immutable/
```

Examples

- PRD
- Architecture
- Domain Model

---

## Mutable

Should evolve together with implementation.

```
docs/mutable/
```

Examples

- API
- Roadmap
- Implementation
- Changelog

---

# Architecture Mindset

The application is composed of four layers.

```
Presentation

↓

Application

↓

Domain

↑

Infrastructure
```

Always respect this dependency direction.

---

# Domain is Sacred

The Domain layer defines:

- business entities
- business rules
- interfaces
- value objects

The Domain must never know about:

- AI models
- databases
- REST frameworks
- machine learning libraries
- storage providers

---

# AI Models are Plugins

Never write business logic around a specific model.

Wrong

```
YOLO

↓

Business Logic
```

Correct

```
VisionProvider Interface

↓

YOLOProvider
```

↓

Business Logic

The interface is stable.

The implementation is replaceable.

---

# Provider Philosophy

Every external dependency should be hidden behind an abstraction.

Examples

Vision

```
VisionProvider
```

Nutrition

```
NutritionProvider
```

Storage

```
StorageProvider
```

Future implementations should require no changes to business logic.

---

# Canonical Food

Business logic should never depend on VisionClass.

Always convert

```
VisionClass

↓

CanonicalFood
```

before continuing the workflow.

---

# Human-in-the-loop

Never assume AI predictions are perfect.

User correction is part of the normal workflow.

Whenever uncertainty exists, prefer allowing user review rather than making hidden assumptions.

---

# Coding Philosophy

Prefer

- composition
- interfaces
- dependency injection
- explicit code
- small functions
- immutable value objects

Avoid

- inheritance-heavy hierarchies
- global state
- hidden side effects
- implicit dependencies
- magic numbers

---

# Introducing New Features

Before creating a new service, ask:

Can this responsibility belong to an existing service?

Avoid duplicate concepts.

Avoid duplicate workflows.

Avoid duplicate providers.

---

# Introducing New Models

When integrating a new AI model:

DO NOT

- expose provider-specific outputs
- expose provider-specific DTOs

Instead

Convert everything into domain objects.

---

# Introducing New Providers

Every provider should satisfy an existing interface.

Never modify upper layers to support one provider.

Instead extend the provider implementation.

---

# Error Handling

Errors should be translated between layers.

Infrastructure

↓

Application

↓

Presentation

Do not leak infrastructure exceptions directly to users.

---

# Logging

Prefer structured logging.

Never log

- secrets
- passwords
- API keys
- authentication tokens
- personal information

---

# Testing Philosophy

Prioritize testing in this order.

1. Domain
2. Application
3. Infrastructure
4. Presentation

Business rules are more important than framework integration.

---

# Documentation Synchronization

Whenever implementation changes:

Update

```
IMPLEMENTATION.md
```

Whenever APIs change:

Update

```
API_SPEC.md
```

Whenever milestones change:

Update

```
ROADMAP.md
```

Whenever architecture decisions occur:

Append a new ADR into

```
DECISIONS.md
```

Whenever functionality changes:

Update

```
CHANGELOG.md
```

Implementation and documentation should never diverge.

---

# AI Agent Behavior

When implementing code:

✔ Read existing code first.

✔ Reuse abstractions.

✔ Prefer extension over duplication.

✔ Keep architecture consistent.

✔ Keep interfaces stable.

✔ Respect dependency direction.

✔ Keep documentation synchronized.

---

# AI Agent Must NOT

Never

- rewrite architecture
- invent new domain concepts
- duplicate existing services
- bypass interfaces
- tightly couple providers
- modify immutable documentation

unless explicitly instructed by the repository owner.

---

# Repository Goal

When someone opens this repository, they should immediately recognize it as a well-engineered software system rather than an experimental AI project.

The AI models are interchangeable.

The architecture is the product.
