# agent-invoice-summary

Foundry Native agent for invoice processing summary and routing decisions.

## Overview

This agent is the final step in the invoice processing workflow. It receives validation results from the validation agent, synthesizes the information, and determines the appropriate next step for the invoice (auto-post, manual review, or vendor follow-up).

It also connects to the MCP Invoice Data server for PO/vendor context when forming the summary.

## Setup

```bash
cd src/agent-invoice-summary
uv sync

# Copy environment file and configure
cp .env.example .env
# Edit .env with your Azure AI Foundry credentials
# Set MCP_INVOICE_DATA_URL to the invoice data MCP endpoint
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
agent-invoice-summary/
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

- **Sequence**: 3 (final agent in workflow)
- **Role**: summary
- **Tools**: MCPInvoiceData (context only)

## Routing Decisions

The agent determines one of three next steps:

1. **auto_post**: Invoice approved for automatic ERP posting
   - All validations passed
   - No blocking issues

2. **manual_review**: Invoice requires human attention
   - Warning-level issues
   - Judgment calls needed

3. **vendor_follow_up**: Invoice needs vendor clarification
   - Missing information
   - Invalid PO or pricing issues

## Output

Produces a concise narrative summary with a recommended next step (auto_post, manual_review, vendor_follow_up). The response is free-form text (no enforced JSON schema).

## Authentication

Uses `DefaultAzureCredential` - run `az login` first or configure managed identity.
