# MCP Invoice Data

MCP server providing invoice and purchase order data tools.

## Overview

This MCP server provides mock data for invoice processing and purchase order validation. It's designed for demo purposes with realistic invoice approval workflow data.

## Tools

| Tool | Description |
|------|-------------|
| `check_po` | Check if a purchase order number exists and is valid for invoicing |
| `get_invoice` | Get invoice details by ID or invoice number |
| `get_po` | Get purchase order details by PO number |

## Mock Data Strategy

The server includes curated sample data:

**Purchase Orders:**
- `PO-2024-001` - Coffee supplies (approved)
- `PO-2024-002` - Office furniture (approved)
- `PO-2024-003` - IT equipment (fulfilled)
- `PO-2024-004` - Marketing materials (submitted - not yet approved)
- `PO-2024-005` - Catering services (cancelled)

**Invoices:**
- `INV-2024-0001` - Coffee supplies invoice (paid)
- `INV-2024-0002` - Furniture invoice (approved)
- `INV-2024-0003` - IT equipment invoice (pending)
- `INV-2024-0004` - Consulting services (no PO - requires special approval)
- `INV-2024-0005` - Cloud services (rejected - invalid PO)

## Local Development

```bash
# Install dependencies
uv sync

# Run the server
uv run python main.py

# Or with uvicorn directly
uv run uvicorn main:mcp --host 0.0.0.0 --port 8014
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8014` | Server port |
| `API_KEY` | `dev-invoice-data-key` | Authentication key |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | - | Azure Monitor telemetry |

## Docker

```bash
# Build
docker build -t mcp-invoice-data .

# Run
docker run -p 8014:8014 -e API_KEY=your-key mcp-invoice-data
```

## Example Usage

### Check PO Validity

```python
# Valid PO
check_po("PO-2024-001")
# Returns: {"po_number": "PO-2024-001", "exists": true, "is_valid": true, "message": "..."}

# Cancelled PO
check_po("PO-2024-005")
# Returns: {"po_number": "PO-2024-005", "exists": true, "is_valid": false, "message": "...cancelled"}

# Non-existent PO
check_po("PO-9999-999")
# Returns: {"po_number": "PO-9999-999", "exists": false, "is_valid": false, "message": "..."}
```

### Get Invoice Details

```python
get_invoice("INV-2024-0001")
# Returns full invoice details with line items, vendor info, amounts, etc.
```

### Get PO Details

```python
get_po("PO-2024-003")
# Returns full purchase order details with line items, department, requester, etc.
```
