# agent-invoice-validation

Foundry Native agent for invoice validation and business rule enforcement.

## Overview

This agent is the second step in the invoice processing workflow. It receives extracted invoice data from the intake agent, validates it against business rules, verifies PO numbers using MCP tools, and prepares the invoice for posting or flags issues for manual review.

## Setup

```bash
cd src/agent-invoice-validation
uv sync

# Copy environment file and configure
cp .env.example .env
# Edit .env with your Azure AI Foundry credentials
```

## Usage

### Provision Agent

Create the agent in AI Foundry (idempotent - recreates if exists):

```bash
uv run python provision.py create
```

List agents:

```bash
uv run python provision.py list
```

Destroy agent:

```bash
uv run python provision.py destroy
```

## Project Structure

```
agent-invoice-validation/
├── __init__.py
├── config.py                 # Configuration from environment
├── provision.py              # CLI for agent provisioning
├── prompts/
│   └── system_prompt.jinja2
├── pyproject.toml
├── .env.example
└── README.md
```

## Workflow Role

- **Sequence**: 2 (second agent in workflow)
- **Role**: validation
- **Handoff**: invoice-process-summary-agent
- **Output Schema**: InvoiceValidation

## MCP Tools

The validation agent uses the following MCP tools:
- **MCPInvoiceData**: Provides PO validation, vendor lookup, and duplicate checking

## Output Schema

The agent produces structured JSON conforming to the InvoiceValidation schema:
- `is_ready_for_posting`: Boolean indicating if invoice can proceed
- `issues`: Array of validation issues with code, severity, message
- `normalized_invoice`: The corrected/normalized invoice data
- `po_validation_result`: PO verification results
- `business_rules`: Array of business rule check results

## Authentication

Uses `DefaultAzureCredential` - run `az login` first or configure managed identity.
