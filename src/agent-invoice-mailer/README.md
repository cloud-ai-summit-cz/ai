# agent-invoice-mailer

Foundry Native agent for drafting emails about invoice validation issues.

## Overview

This agent is the fourth step in the invoice processing workflow. It receives validation results (especially failed validations) and creates professional email drafts summarizing issues and providing clear resolution steps. The email subject includes the Invoice ID and revocation status.

## Setup

```bash
cd src/agent-invoice-mailer
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
agent-invoice-mailer/
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

- **Sequence**: 4 (fourth agent in workflow)
- **Role**: notification
- **Handoff**: end
- **Output Schema**: EmailDraft

## Output Schema

The agent produces structured JSON conforming to the EmailDraft schema:
- `email_subject`: Subject line including Invoice ID and revocation status
- `email_to`: Supplier email address
- `email_cc`: Optional CC recipients
- `email_body`: Full email content with issue summary and resolution steps
- `invoice_id`: The invoice number being referenced
- `po_number`: PO number if available
- `validation_status`: "failed" or "passed"
- `issues_summary`: Array of issues with code, description, and suggested action
- `next_steps`: Recommended actions for resolution
- `urgency`: Priority level (low, medium, high, critical)

## Email Format

### For Failed Validations
Subject: `[ACTION REQUIRED] Invoice {invoice_number} - Validation Issues (Revocation Pending)`

The email body includes:
- Professional greeting
- Clear explanation of validation issues
- Impact on invoice processing
- Step-by-step resolution guidance
- Contact information for questions

### For Passed Validations
Subject: `Invoice {invoice_number} - Validation Successful`

A brief confirmation that the invoice has passed validation.

## Authentication

Uses `DefaultAzureCredential` - run `az login` first or configure managed identity.
