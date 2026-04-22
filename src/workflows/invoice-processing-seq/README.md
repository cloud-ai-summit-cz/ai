# Invoice Processing Sequential Workflow

Sequential multi-agent workflow for invoice intake, validation, and summary processing using Azure AI Foundry.

## Overview

This workflow orchestrates three agents in sequence to process invoices:

1. **Invoice Intake Agent** - Performs OCR and extracts structured invoice data
2. **Invoice Validation Agent** - Validates data, checks PO availability, flags issues
3. **Invoice Summary Agent** - Summarizes results and determines next steps

## Agents

| Agent | Role | Description |
|-------|------|-------------|
| `invoice-intake-agent` | Intake | OCR extraction, number normalization, structured payload |
| `invoice-validation-agent` | Validation | PO verification, duplicate detection, business rules |
| `invoice-process-summary-agent` | Summary | Final summary with next step recommendation |

## Local Development

```bash
# Install dependencies
uv sync

# Setup all agents (provision to Azure AI Foundry)
./setup_workflow.sh

# Run the workflow
uv run python run_workflow.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AZURE_AI_FOUNDRY_ENDPOINT` | - | Azure AI Foundry project endpoint |
| `MODEL_DEPLOYMENT_NAME` | `gpt-4o-mini` | Model deployment name |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | - | Azure Monitor telemetry |

## Workflow Structure

```
invoice-processing-seq/
├── run_workflow.py           # Main workflow execution script
├── setup_agents_template.py  # Agent provisioning with schemas
├── setup_workflow.sh         # Shell script to provision all agents
├── data/                     # Invoice images for testing
│   └── invoice1.jpg
└── .env                      # Environment configuration
```

## Agent Schemas

### Invoice Extraction (Intake Output)
- `invoice_number`, `invoice_date`, `due_date`
- `supplier` (name, address, email, phone)
- `line_items` (description, quantity, unit_price, total)
- `subtotal`, `tax`, `shipping`, `total`
- `confidence` score and `notes`

### Validation Result
- `is_ready_for_posting` - boolean approval status
- `issues` - array of validation issues with severity
- `normalized_invoice` - cleaned invoice data
- `po_validation_result` - PO verification status
- `business_rules` - array of rule check results

### Process Summary (Final Output)
- `summary` - human-readable summary
- `next_step` - `auto_post`, `manual_review`, or `vendor_follow_up`
- `approved_amount` - validated invoice amount
- `target_queue` - routing destination
