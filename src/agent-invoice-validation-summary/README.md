# agent-invoice-validation-summary

Foundry Native agent for summarizing invoice validation outcomes.

## Overview

This agent consumes the JSON output from the invoice validation step and produces a concise summary. When validation succeeds it echoes a one-sentence summary with supplier and total; when validation fails it highlights the key findings.

## Setup

```bash
cd src/agent-invoice-validation-summary
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
agent-invoice-validation-summary/
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

- **Sequence**: 2.5 (after validation, before final processing summary)
- **Role**: validation-summary
- **Output Schema**: InvoiceValidationSummary

## Output Schema

The agent produces structured JSON conforming to the InvoiceValidationSummary schema:
- `invoice_validation_status`: `<INV_OK>` or `<INV_FAIL>`
- `summary`: One-sentence summary of the invoice or issues
- `supplier`: Supplier name when available
- `total`: Invoice total when available
- `issues`: Array of issue descriptions when validation failed

## Authentication

Uses `DefaultAzureCredential` - run `az login` first or configure managed identity.
