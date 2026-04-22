# Agent Development Guidelines

## 1. Purpose

Provide a clear, single reference for implementing, extending, and maintaining AI agents and related services in this repository. This project focuses on the **Cofilot AI Platform** — a multi-agent invoice approval workflow demo using Microsoft Agent Framework on Azure.

## 2. Core Principles

1. Favor simplicity and readability over premature abstraction.
2. Keep functionality self‑documenting; use docstrings, not progress/status comments.
3. Minimize surface area: small, cohesive modules > large monoliths.
4. Explicit > implicit for data contracts, configuration, and side effects.
5. Make cheap experiments disposable (prefixed `adhoc_`), not permanent.

## 3. Project‑Wide Conventions

### 3.1 Documentation

* **Specs Structure**:
    * `specs/platform/`: Cross-cutting concerns (Architecture, Data Models, Security).
    * `specs/platform/decisions/`: Project-wide Architecture Decision Records (ADRs).
    * `specs/services/<service>/`: Service-specific specs (API, Testing, Deployment).
    * `specs/services/<service>/decisions/`: Service-specific ADRs.
* Primary documentation channel inside code: **docstrings** (revise them whenever code changes behavior or signature).
* Only add code comments for non‑obvious logic or critical nuances. Never for progress logs, migration notes, or "previous implementation" commentary.
* **Implementation Details**: Update `docs/IMPLEMENTATION_LOG.md` autonomously with meaningful technical decisions (e.g., "Switched to library X for performance", "Refactored auth flow"). Do not ask for permission for these logs.
* **Architecture Decisions**: For fundamental changes (e.g., "Adding a new database", "Changing API protocol"), **propose** an ADR (Architecture Decision Record). Prepare a draft for user review, but **never** create/merge it autonomously.
* Add confirmed recurring pitfalls to `docs/COMMON_ERRORS.md` (after user confirmation—see Section 6).
* Each component/service keeps concise run & test instructions in its local `README.md`.

### 3.2 Refactoring & Improvements

Opportunistic simplifications are encouraged. When you see a refactor beyond the immediate task:
* Perform low‑risk, obviously beneficial cleanups directly (pure simplification, dead code removal).
* For broader architectural shifts, surface a brief rationale in chat before proceeding.

### 3.3 Experiments & Troubleshooting

* **Consult First**: Always check `docs/COMMON_ERRORS.md` before starting deep troubleshooting.
* **Propose Additions**: After fixing a non-trivial error, actively recommend adding it to `docs/COMMON_ERRORS.md`.
    * Draft the entry (Error, Cause, Fix).
    * Show it to the user.
    * **Wait for approval** before writing to the file.

### 3.4 Technology Stack

* **Primary Language**: Python 3.11+ with **uv** package manager
* **AI Framework**: Microsoft Agent Framework (Azure AI Agent Service, Microsoft Foundry)
* **API Framework**: FastAPI for backend services
* **Data Validation**: Pydantic models for all data contracts
* **Infrastructure as Code**: Terraform with **azapi** provider for Azure deployments
* **Frontend**: Web UI for demo portal (if applicable)

## 4. Service Guidelines (Python)

### 4.1 Structure & Modeling

Follow this project layout for Python services:

```
.
├── app/
│   ├── __init__.py
│   ├── main.py           # Application entry point
│   ├── config.py         # Configuration and environment variable handling
│   ├── models/           # Pydantic models and database schemas
│   │   ├── __init__.py
│   │   └── ...
│   ├── routes/           # API route definitions (controllers)
│   │   ├── __init__.py
│   │   └── ...
│   ├── services/         # Business logic and external service integrations
│   │   ├── __init__.py
│   │   └── ...
│   ├── agents/           # Agent definitions and orchestration logic
│   │   ├── __init__.py
│   │   └── ...
│   └── utils/            # Shared utility functions
│       ├── __init__.py
│       └── ...
├── pyproject.toml        # uv/Python project configuration
├── uv.lock               # uv lock file (committed)
├── Dockerfile            # Container definition
└── tests/                # Test files
```

* `models/`: Contains data structures, Pydantic schemas.
* `routes/`: Defines API endpoints and handles HTTP requests/responses.
* `services/`: Encapsulates business logic and interactions with databases or external APIs.
* `agents/`: Microsoft Agent Framework agent definitions, tools, and orchestration.
* `utils/`: Helper functions and common utilities used across the application.
* `config.py`: Manages environment variables and application settings.

### 4.2 Language & Style

* Target **Python 3.11+**; do not introduce code that requires deprecated versions.
* Follow **PEP 8** with these clarifications:
    * Max line length 100 characters.
    * Prefer `snake_case` for functions/variables, `PascalCase` for classes.
    * Use **type hints everywhere**; enforce via `mypy` or `pyright` CI checks.
* Every public class/function must have a docstring specifying purpose, parameters, return value(s), and exceptions.
* Avoid redundant comments explaining obvious code or restating names.

### 4.3 Dependencies & Packaging

* Use **uv** as the package manager for all Python projects.
* Manage dependencies in `pyproject.toml` with pinned versions.
* Use `uv.lock` for reproducible builds (commit this file).
* Use `uv sync` to install dependencies.
* Use `uv run` to execute scripts within the virtual environment.
* Use `pip-audit` or equivalent to scan dependencies for known vulnerabilities.

### 4.4 Logging

* Use the standard `logging` library configured in `main.py`.
* **No `print` statements** in production code; use `logger.info()`, `logger.error()`, etc.
* Log levels:
    * DEBUG: diagnostics
    * INFO: lifecycle events
    * WARNING: recoverable anomalies
    * ERROR: failures
    * CRITICAL: systemic outages

### 4.5 Error Handling & Resilience

* Use FastAPI's `HTTPException` for API errors with appropriate status codes.
* Bubble validation errors with meaningful messages.
* Wrap external IO (DB, HTTP, queues) with retry-capable clients. Include exponential backoff and jitter for transient failures.
* For Azure Cosmos DB usage, reuse a singleton `CosmosClient`, honor `Retry-After` headers, and log diagnostics when latency or status codes deviate from expectations.

### 4.6 Testing

* Use **pytest** with descriptive test names (`test_<function>_<behavior>`).
    * Use `pytest-asyncio` for async tests.
    * Use `pytest-cov` to measure coverage.
* Keep unit tests fast and free of live IO; mock repositories/interfaces.
* Provide integration tests for persistence layers and API contracts.
* Ensure Specification by Example scenarios from PRD exist as automated tests before implementing major behavior.

### 4.7 Security

* Load secrets from environment variables using `.env` files (local) or managed identity (cloud).
* Use `.env.example` to document required environment variables without committing secrets.
* Enforce dependency scanning and formatting in CI: `ruff`, `mypy`, `pytest`, `pip-audit` must pass before merge.
* Validate all untrusted inputs via Pydantic models before use.

## 5. Infrastructure as Code (Terraform with azapi)

### 5.1 Tooling & Providers

* **Terraform Version**: Use the latest stable version of Terraform. Pin versions in `terraform` block.
* **Providers**:
    * Use **azapi** as the primary provider for Azure resources (bleeding-edge features, full ARM API coverage).
    * Use `azurerm` only when azapi is insufficient or for specific legacy resources.
    * Pin provider versions to ensure reproducible builds.

### 5.2 Project Structure

```
infra/
├── main.tf               # Provider configuration and backend setup
├── versions.tf           # Provider and terraform version constraints
├── variables.tf          # Input variables with rich descriptions
├── outputs.tf            # Output values
├── locals.tf             # Local values and common tags
├── networking.tf         # Network resources
├── ai_services.tf        # Azure AI services (Foundry, OpenAI, Document Intelligence)
├── storage.tf            # Storage accounts, Cosmos DB
├── compute.tf            # Container Apps, App Services
└── rbac.tf               # Role assignments and managed identities
```

* Segment resource types into separate files.
* If a type bloats, split further by function (e.g., `container_app.frontend.tf`, `container_app.backend.tf`).

### 5.3 Coding Conventions

* **Variables**:
    * Always include rich multi-line descriptions: purpose, type, constraints, examples.
    * Provide sensible defaults where safe.
    * Use specific types (e.g., `list(string)`, `object({...})`) instead of `any`.
* **Comments**:
    * Only for non-obvious attributes or critical justification.
    * No change logs, no progress notes.
* **Tags**:
    * Tags are optional unless explicitly requested.
    * If used, prefer a `locals` block to define common tags applied to all resources.
* **Naming**:
    * Use `snake_case` for resource names and variables.
    * Resource names should be descriptive and unique within the module.

### 5.4 State Management

* **Remote State**: Always use a remote backend (Azure Storage Account) for state files. Never commit `terraform.tfstate` to version control.
* **State Locking**: Ensure the backend supports state locking (Azure Storage supports this via leases).
* **State Isolation**: Use separate state files for different environments (dev, staging, prod).

### 5.5 Security

* **Secrets**: Never hardcode secrets in `.tf` files. Use Azure Key Vault or environment variables.
* **Sensitive Data**: Mark sensitive output values with `sensitive = true`.

### 5.6 CI/CD Expectations

* **PR**: Run `terraform fmt -check`, `terraform validate`, and `terraform plan`.
* **Merge**: Run `terraform apply` (auto-approve) on the main branch or via manual approval gate.
* **Formatting**: Enforce `terraform fmt` in CI.
* **Linting**: Use `tflint` to catch common errors and enforce best practices.

## 6. Reinforced Documentation & Logging Rules

These constraints exist to prevent uncontrolled documentation sprawl and progress leakage into code:

1. **Implementation Log Boundaries**: Implementation progress and technical details belong in `docs/IMPLEMENTATION_LOG.md`. Update this file autonomously as you work.
2. **Architecture Decision Boundaries**: Fundamental changes require an ADR. **Never** write an ADR autonomously. Always propose the content and wait for user review.
3. **Common Errors Workflow**:
    * Consult `docs/COMMON_ERRORS.md` when stuck.
    * After fixing, **propose** the addition to the user.
    * Only write to the file after explicit user approval.
4. **Controlled Design Changes**: Architectural or behavioral design alterations should be reflected (after approval) in `specs/` documentation. Treat specs as guiding artifacts; do not mutate them unilaterally.
5. **New Doc File Exception**: If a truly new doc artifact is justified, create it in `docs/` with prefix `ADHOC_` and notify user. Expect eventual consolidation or deletion.
6. **No Progress/History Comments**: Ban inline comments like "// updated previous logic" or "# temporary hack (will remove)" — instead record durable decisions in `docs/IMPLEMENTATION_LOG.md`.

## 7. Ad‑Hoc / Disposable Artifacts

| Type | Naming Pattern | Purpose | Lifecycle |
|------|----------------|---------|-----------|
| Scratch test script | `adhoc_test_*` or `adhoc_*` | Quick reproduction / isolate behavior | Delete after converting insight into real tests/code |
| Documentation draft | `docs/ADHOC_*.md` | Rare: staging ground for large doc refactor | Merge content into canonical doc then delete |

Rules:
* Must not be imported by production code.
* Must not hold secrets or credentials.
* Track none of them in long‑term design history; only distilled results.

## 8. Change Control & Communication

1. Before major architectural changes: summarize intent, risk, and alternatives in chat. If agreed, **propose an ADR draft** for review.
2. After implementing a feature: update relevant docstrings + (if needed) `docs/IMPLEMENTATION_LOG.md`.
3. If you discover systemic flaw: propose remediation path; avoid broad speculative refactors without confirmation.

## 9. Quick Reference Checklist

### Before Starting Work
- [ ] Read `PRD.md` for requirements and acceptance criteria
- [ ] Check `docs/COMMON_ERRORS.md` for known pitfalls
- [ ] Review relevant `specs/` documentation

### During Development
- [ ] Write type hints for all functions and classes
- [ ] Add docstrings to all public interfaces
- [ ] Use `uv run pytest` to validate changes
- [ ] Run `ruff check` and `ruff format` for Python code
- [ ] Run `terraform fmt` and `terraform validate` for IaC

### Before Committing
- [ ] Update `docs/IMPLEMENTATION_LOG.md` with decisions made
- [ ] Ensure all tests pass
- [ ] Verify no secrets in code or config files
- [ ] Update service-level `README.md` if run/test instructions changed

### For New Features
- [ ] Implement Specification by Example tests from PRD first
- [ ] Propose ADR if architectural change is needed
- [ ] Update relevant specs after user approval

## 10. Scope & Precedence

This `AGENTS.md` centralizes operational & stylistic guidance. If conflicts arise:

1. Explicit user instruction (chat) overrides this file case‑by‑case.
2. `specs/` documentation governs architecture (pending approved changes).
3. This file governs daily engineering discipline & hygiene.
