# agent-invoice-intake

Foundry Native agent for invoice intake and OCR extraction.

## Overview

This agent is the first step in the invoice processing workflow. It analyzes invoice images or scanned documents, performs OCR, extracts structured data, and validates basic consistency (e.g., line item totals matching invoice total).

## Setup

```bash
cd src/agent-invoice-intake
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
agent-invoice-intake/
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

- **Sequence**: 1 (first agent in workflow)
- **Role**: intake
- **Output Schema**: InvoiceExtraction

## Output Schema

The agent produces structured JSON conforming to the InvoiceExtraction schema:
- Invoice identification (number, dates, PO reference)
- Supplier information
- Bill-to information
- Line items with quantities, prices, and totals
- Summary totals (subtotal, tax, shipping, total)
- Confidence score
- Notes for any discrepancies

## Authentication

Uses `DefaultAzureCredential` - run `az login` first or configure managed identity.
