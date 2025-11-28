# Data Models

Definitive schema catalog for Cofilot AI Platform. All persistent and transient data contracts.

## Authoritative Principles

- **Single source of truth**: Schemas here must match code (Pydantic models). Update together.
- **Versioning**: Use semantic versioning for breaking changes.
- **Specification by Example**: Each schema includes realistic payload examples.
- **Cosmos DB Guidelines**: Follow partition key best practices per attached instructions.

---

## Schema Inventory

| Name | Type | Partition Key | Description | Version |
|------|------|---------------|-------------|---------|
| `ResearchSession` | Cosmos Document | `/session_id` | Research scenario session state | 1.0 |
| `Scratchpad` | Cosmos Document | `/session_id` | Shared memory for research agents | 1.0 |
| `ChecklistItem` | Embedded | - | Research checklist item | 1.0 |
| `UserQuestion` | Embedded | - | Question from agent to user | 1.0 |
| `InvoiceWorkflow` | Cosmos Document | `/workflow_id` | Invoice processing workflow state | 1.0 |
| `WorkflowEvent` | Cosmos Document | `/workflow_id` | Event log for invoice processing | 1.0 |
| `InvoiceData` | Embedded | - | Extracted invoice data | 1.0 |
| `PurchaseOrder` | JSON File | - | Mock PO data | 1.0 |
| `Competitor` | JSON File | - | Mock competitor data | 1.0 |
| `MarketData` | JSON File | - | Mock market statistics | 1.0 |
| `LocationData` | JSON File | - | Mock neighborhood data | 1.0 |
| `AgentDefinition` | Python Config | - | AI Foundry agent configuration | 1.0 |
| `SSEEvent` | Transient | - | Server-Sent Event payload | 1.0 |

---

## Detailed Schemas

### `ResearchSession`

- **Owner**: Backend API
- **Storage**: Cosmos DB - `cofilot-db` / `research-sessions`
- **Consumers**: Backend API, Frontend
- **Producers**: Backend API

```json
{
  "id": "sess_abc123",
  "session_id": "sess_abc123",
  "query": "Should Cofilot expand to Vienna?",
  "status": "in_progress",
  "created_at": "2025-12-01T10:00:00Z",
  "updated_at": "2025-12-01T10:15:00Z",
  "thread_id": "thread_xyz789",
  "current_agent": "market-analyst",
  "scratchpad_id": "sp_abc123",
  "checklist": [
    {
      "id": 1,
      "item": "Market size and growth trends documented",
      "owner_agent": "market-analyst",
      "status": "completed",
      "completed_at": "2025-12-01T10:05:00Z",
      "notes": "Vienna coffee market: €450M annually"
    },
    {
      "id": 2,
      "item": "Customer segments identified",
      "owner_agent": "market-analyst",
      "status": "in_progress",
      "completed_at": null,
      "notes": null
    }
  ],
  "pending_questions": [
    {
      "id": "q_001",
      "question": "What is your target budget for initial investment?",
      "context": "Needed for financial projections",
      "priority": "high",
      "asked_at": "2025-12-01T10:10:00Z",
      "answered": false,
      "answer": null
    }
  ],
  "final_report": null
}
```

**Pydantic Model**:
```python
class ChecklistItem(BaseModel):
    id: int
    item: str
    owner_agent: str
    status: Literal["pending", "in_progress", "completed"]
    completed_at: datetime | None = None
    notes: str | None = None

class UserQuestion(BaseModel):
    id: str
    question: str
    context: str
    priority: Literal["low", "medium", "high"]
    asked_at: datetime
    answered: bool = False
    answer: str | None = None

class ResearchSession(BaseModel):
    id: str
    session_id: str  # Partition key
    query: str
    status: Literal["created", "in_progress", "awaiting_input", "completed", "failed"]
    created_at: datetime
    updated_at: datetime
    thread_id: str | None = None
    current_agent: str | None = None
    scratchpad_id: str
    checklist: list[ChecklistItem]
    pending_questions: list[UserQuestion] = []
    final_report: dict | None = None
```

---

### `Scratchpad`

- **Owner**: mcp-scratchpad
- **Storage**: Cosmos DB - `cofilot-db` / `scratchpads`
- **Consumers**: All research agents
- **Producers**: All research agents

```json
{
  "id": "sp_abc123",
  "session_id": "sess_abc123",
  "created_at": "2025-12-01T10:00:00Z",
  "updated_at": "2025-12-01T10:15:00Z",
  "sections": {
    "market_findings": {
      "last_updated": "2025-12-01T10:05:00Z",
      "updated_by": "market-analyst",
      "content": {
        "market_size_eur": 450000000,
        "annual_growth_rate": 0.035,
        "coffee_consumption_per_capita_kg": 7.2,
        "specialty_coffee_share": 0.28,
        "key_trends": [
          "Growing demand for specialty coffee",
          "Sustainability focus increasing",
          "Third-wave coffee shops expanding"
        ]
      }
    },
    "competitor_analysis": {
      "last_updated": "2025-12-01T10:10:00Z",
      "updated_by": "competitor-analyst",
      "content": {
        "total_competitors_analyzed": 5,
        "competitors": [
          {
            "name": "Cafe Central",
            "type": "traditional",
            "locations": 3,
            "price_range": "high",
            "strengths": ["Historic brand", "Tourist attraction"],
            "weaknesses": ["Not specialty focused"]
          }
        ],
        "market_gaps": [
          "Limited third-wave specialty options in 1st district",
          "No major player with sustainable sourcing focus"
        ]
      }
    },
    "location_options": {
      "last_updated": null,
      "updated_by": null,
      "content": null
    },
    "regulations": {
      "last_updated": null,
      "updated_by": null,
      "content": null
    },
    "financial_projections": {
      "last_updated": null,
      "updated_by": null,
      "content": null
    },
    "user_answers": {
      "last_updated": "2025-12-01T10:12:00Z",
      "updated_by": "user",
      "content": {
        "target_budget": "€150,000 - €200,000",
        "preferred_neighborhoods": ["1st District", "7th District"],
        "timeline": "Q2 2026"
      }
    }
  }
}
```

**Pydantic Model**:
```python
class ScratchpadSection(BaseModel):
    last_updated: datetime | None = None
    updated_by: str | None = None
    content: dict | None = None

class Scratchpad(BaseModel):
    id: str
    session_id: str  # Partition key
    created_at: datetime
    updated_at: datetime
    sections: dict[str, ScratchpadSection]
```

---

### `InvoiceWorkflow`

- **Owner**: Backend API
- **Storage**: Cosmos DB - `cofilot-db` / `invoice-workflows`
- **Consumers**: Backend API, Frontend
- **Producers**: Backend API, mcp-workflow

```json
{
  "id": "wf_inv123",
  "workflow_id": "wf_inv123",
  "status": "recommendation_generated",
  "created_at": "2025-12-01T14:00:00Z",
  "updated_at": "2025-12-01T14:00:08Z",
  "thread_id": "thread_inv456",
  "document_url": "https://storage.blob.core.windows.net/invoices/inv_001.pdf",
  "invoice_data": {
    "vendor_name": "Coffee Beans Co.",
    "vendor_id": "VND001",
    "invoice_number": "INV-2025-0042",
    "invoice_date": "2025-11-25",
    "po_number": "PO-12345",
    "subtotal": 850.00,
    "tax_amount": 170.00,
    "tax_rate": 0.20,
    "total_amount": 1020.00,
    "currency": "EUR",
    "line_items": [
      {
        "description": "Premium Arabica Beans - 10kg",
        "quantity": 5,
        "unit_price": 150.00,
        "total": 750.00
      },
      {
        "description": "Shipping",
        "quantity": 1,
        "unit_price": 100.00,
        "total": 100.00
      }
    ]
  },
  "validation_result": {
    "po_exists": true,
    "po_status": "active",
    "policy_checks": [
      {"policy": "approval_threshold", "passed": true, "details": "Amount within owner limit"},
      {"policy": "vendor_approved", "passed": true, "details": "Vendor in approved list"}
    ],
    "tax_compliance": {
      "valid": true,
      "details": "VAT correctly applied at 20%"
    }
  },
  "reconciliation_result": {
    "matches": true,
    "discrepancies": [],
    "po_total": 1020.00,
    "invoice_total": 1020.00,
    "variance": 0.00
  },
  "routing_result": {
    "po_owner": {
      "name": "Jan Novak",
      "email": "jan.novak@cofilot.cz",
      "teams_id": "jan.novak@cofilot.cz",
      "approval_limit": 5000.00
    },
    "requires_escalation": false
  },
  "recommendation": {
    "decision": "approve",
    "confidence": 0.95,
    "reasoning": "Invoice matches PO exactly. All policy checks passed. Tax compliance verified.",
    "summary": "Invoice INV-2025-0042 from Coffee Beans Co. for €1,020.00 matches PO-12345. Recommended for approval."
  },
  "notification_sent": true,
  "notification_sent_at": "2025-12-01T14:00:08Z"
}
```

**Pydantic Model**:
```python
class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float

class InvoiceData(BaseModel):
    vendor_name: str
    vendor_id: str | None = None
    invoice_number: str
    invoice_date: str
    po_number: str | None = None
    subtotal: float
    tax_amount: float
    tax_rate: float
    total_amount: float
    currency: str
    line_items: list[LineItem]

class PolicyCheck(BaseModel):
    policy: str
    passed: bool
    details: str

class ValidationResult(BaseModel):
    po_exists: bool
    po_status: str | None = None
    policy_checks: list[PolicyCheck]
    tax_compliance: dict

class ReconciliationResult(BaseModel):
    matches: bool
    discrepancies: list[str]
    po_total: float
    invoice_total: float
    variance: float

class POOwner(BaseModel):
    name: str
    email: str
    teams_id: str
    approval_limit: float

class RoutingResult(BaseModel):
    po_owner: POOwner
    requires_escalation: bool

class Recommendation(BaseModel):
    decision: Literal["approve", "reject", "escalate"]
    confidence: float
    reasoning: str
    summary: str

class InvoiceWorkflow(BaseModel):
    id: str
    workflow_id: str  # Partition key
    status: Literal[
        "created", "extracting", "validating", "reconciling", 
        "routing", "recommendation_generated", "notification_sent", "failed"
    ]
    created_at: datetime
    updated_at: datetime
    thread_id: str | None = None
    document_url: str
    invoice_data: InvoiceData | None = None
    validation_result: ValidationResult | None = None
    reconciliation_result: ReconciliationResult | None = None
    routing_result: RoutingResult | None = None
    recommendation: Recommendation | None = None
    notification_sent: bool = False
    notification_sent_at: datetime | None = None
```

---

### `WorkflowEvent`

- **Owner**: mcp-workflow
- **Storage**: Cosmos DB - `cofilot-db` / `workflow-events`
- **Consumers**: Backend API (SSE streaming)
- **Producers**: mcp-workflow

```json
{
  "id": "evt_001",
  "workflow_id": "wf_inv123",
  "event_type": "data_extracted",
  "timestamp": "2025-12-01T14:00:02Z",
  "agent": "intake-agent",
  "payload": {
    "fields_extracted": 12,
    "confidence": 0.94,
    "vendor": "Coffee Beans Co.",
    "amount": 1020.00
  },
  "message": "Invoice data extracted successfully. 12 fields identified with 94% confidence."
}
```

**Pydantic Model**:
```python
class WorkflowEvent(BaseModel):
    id: str
    workflow_id: str  # Partition key
    event_type: Literal[
        "invoice_received", "data_extracted", "validation_complete",
        "reconciliation_complete", "routing_complete", 
        "recommendation_generated", "notification_sent", "error"
    ]
    timestamp: datetime
    agent: str
    payload: dict
    message: str
```

---

### `SSEEvent`

- **Owner**: Backend API
- **Type**: Transient (not persisted)
- **Consumers**: Frontend
- **Producers**: Backend API

```json
{
  "event": "agent_activity",
  "data": {
    "session_id": "sess_abc123",
    "timestamp": "2025-12-01T10:05:00Z",
    "agent": "market-analyst",
    "action": "tool_call",
    "tool": "get_market_overview",
    "status": "completed",
    "message": "Retrieved Vienna market data: €450M market size",
    "details": {
      "market_size_eur": 450000000,
      "source": "mcp-market-data"
    }
  }
}
```

**Event Types**:
| Event | Description | Payload |
|-------|-------------|---------|
| `session_created` | Research session started | `{session_id, query}` |
| `agent_activity` | Agent performed action | `{agent, action, tool, status, message}` |
| `scratchpad_updated` | Scratchpad section changed | `{section, agent, summary}` |
| `checklist_updated` | Checklist item status changed | `{item_id, status, notes}` |
| `questions_pending` | Agent needs user input | `{questions: [...]}` |
| `research_complete` | Research finished | `{session_id, report}` |
| `invoice_received` | Invoice upload received | `{workflow_id, filename}` |
| `workflow_event` | Invoice workflow step | `{event_type, agent, message}` |
| `workflow_complete` | Invoice processing done | `{workflow_id, recommendation}` |
| `error` | Error occurred | `{error_type, message}` |

---

### `PurchaseOrder` (Mock Data)

- **Owner**: Engineering
- **Storage**: JSON file - `mock-data/purchase_orders.json`
- **Consumers**: mcp-po

```json
{
  "po_number": "PO-12345",
  "vendor_id": "VND001",
  "vendor_name": "Coffee Beans Co.",
  "status": "active",
  "created_date": "2025-10-15",
  "owner": {
    "id": "USR001",
    "name": "Jan Novak",
    "email": "jan.novak@cofilot.cz",
    "teams_id": "jan.novak@cofilot.cz",
    "approval_limit": 5000.00
  },
  "items": [
    {
      "line_number": 1,
      "description": "Premium Arabica Beans - 10kg",
      "quantity": 5,
      "unit_price": 150.00,
      "total": 750.00
    },
    {
      "line_number": 2,
      "description": "Shipping",
      "quantity": 1,
      "unit_price": 100.00,
      "total": 100.00
    }
  ],
  "subtotal": 850.00,
  "tax_rate": 0.20,
  "tax_amount": 170.00,
  "total": 1020.00,
  "currency": "EUR"
}
```

---

### `Competitor` (Mock Data)

- **Owner**: Engineering
- **Storage**: JSON file - `mock-data/competitors_vienna.json`
- **Consumers**: mcp-competitor

```json
{
  "id": "COMP001",
  "name": "Cafe Central",
  "city": "Vienna",
  "type": "traditional_coffeehouse",
  "founded": 1876,
  "locations": [
    {
      "address": "Herrengasse 14, 1010 Wien",
      "district": "1st District",
      "size_sqm": 450
    }
  ],
  "price_range": "high",
  "average_coffee_price_eur": 5.50,
  "specialties": ["Melange", "Einspänner", "Traditional pastries"],
  "positioning": "Historic Viennese coffeehouse experience",
  "target_audience": ["Tourists", "Business professionals", "Traditionalists"],
  "strengths": [
    "Historic brand recognition",
    "Prime location",
    "UNESCO intangible heritage"
  ],
  "weaknesses": [
    "Not specialty coffee focused",
    "High prices",
    "Tourist-heavy atmosphere"
  ],
  "website": "https://www.cafecentral.wien"
}
```

---

### `MarketData` (Mock Data)

- **Owner**: Engineering
- **Storage**: JSON file - `mock-data/market_vienna.json`
- **Consumers**: mcp-market-data

```json
{
  "city": "Vienna",
  "country": "Austria",
  "population": 1920000,
  "gdp_per_capita_eur": 52000,
  "coffee_market": {
    "total_market_size_eur": 450000000,
    "annual_growth_rate": 0.035,
    "consumption_per_capita_kg": 7.2,
    "specialty_coffee_share": 0.28,
    "third_wave_growth_rate": 0.12
  },
  "trends": [
    {
      "trend": "Specialty coffee growth",
      "description": "Third-wave coffee shops growing 12% annually",
      "impact": "high"
    },
    {
      "trend": "Sustainability focus",
      "description": "60% of consumers prefer sustainable sourcing",
      "impact": "medium"
    }
  ],
  "customer_segments": [
    {
      "segment": "Young Professionals",
      "size_percent": 0.25,
      "avg_spend_per_visit_eur": 8.50,
      "visits_per_month": 12,
      "preferences": ["Specialty coffee", "Laptop-friendly", "Modern aesthetic"]
    },
    {
      "segment": "Students",
      "size_percent": 0.20,
      "avg_spend_per_visit_eur": 5.00,
      "visits_per_month": 15,
      "preferences": ["Affordable", "WiFi", "Study-friendly"]
    }
  ]
}
```

---

### `LocationData` (Mock Data)

- **Owner**: Engineering
- **Storage**: JSON file - `mock-data/locations_vienna.json`
- **Consumers**: mcp-location

```json
{
  "city": "Vienna",
  "neighborhoods": [
    {
      "id": "LOC001",
      "name": "Innere Stadt",
      "district": "1st District",
      "description": "Historic city center, tourist hub",
      "rent_per_sqm_eur": 45.00,
      "foot_traffic": "very_high",
      "foot_traffic_daily_avg": 50000,
      "demographics": {
        "residents": 16000,
        "avg_income_eur": 65000,
        "age_distribution": {
          "18-30": 0.22,
          "31-50": 0.35,
          "51+": 0.43
        }
      },
      "existing_coffee_shops": 45,
      "competition_density": "very_high",
      "pros": ["High visibility", "Tourist traffic", "Prestige location"],
      "cons": ["Very high rent", "Saturated market", "Tourist-focused"]
    }
  ]
}
```

---

### `AgentDefinition`

- **Owner**: Platform team
- **Storage**: Python configuration files
- **Consumers**: agent-provisioner

```python
# agents/research/market_analyst.py
AGENT_DEFINITION = {
    "name": "market-analyst",
    "display_name": "Market Analyst",
    "model": "gpt-4o",
    "instructions": """You are a market research analyst specializing in the coffee industry.
Your role is to analyze market conditions for potential business expansion.

## Your Responsibilities:
1. Research market size and growth trends
2. Identify customer segments and their preferences
3. Analyze market opportunities and challenges

## Tools Available:
- get_market_overview: Get market statistics for a city
- get_market_trends: Get historical and projected trends
- get_customer_segments: Get customer segment analysis
- search_cultural_data: Search for cultural insights
- read_section: Read from shared scratchpad
- write_section: Write findings to scratchpad
- update_checklist: Mark checklist items complete

## Output Guidelines:
- Always write findings to the scratchpad
- Reference data sources in your analysis
- Update checklist when completing assigned items
- Flag any gaps or uncertainties for follow-up
""",
    "tools": [
        {"type": "mcp", "server": "mcp-market-data"},
        {"type": "mcp", "server": "mcp-scratchpad"}
    ],
    "temperature": 0.3
}
```

---

## Data Lineage & Transformations

### Research Flow

```
User Query
    ↓
ResearchSession (created)
    ↓
Scratchpad (created, empty sections)
    ↓
[Agent Loop]
    ├── MCP Tool → Mock Data (JSON)
    ├── Agent → Scratchpad.sections
    ├── Agent → ResearchSession.checklist
    └── Agent → SSEEvent → Frontend
    ↓
Synthesizer → ResearchSession.final_report
```

### Invoice Flow

```
PDF Upload
    ↓
Blob Storage
    ↓
InvoiceWorkflow (created)
    ↓
[Agent Sequence]
    ├── Document Intelligence → InvoiceData
    ├── mcp-po → ValidationResult
    ├── mcp-po → ReconciliationResult
    ├── mcp-po → RoutingResult
    ├── Agent → Recommendation
    └── Each step → WorkflowEvent → SSEEvent → Frontend
    ↓
mcp-notification → Notification Sent
```

---

## Validation Rules

### Invoice Data
- `po_number`: Optional, but if present must match regex `^PO-\d{5}$`
- `total_amount`: Must equal `subtotal + tax_amount` (within 0.01 tolerance)
- `tax_rate`: Must be between 0 and 1
- `line_items`: At least one required

### Research Session
- `query`: Non-empty string, max 500 characters
- `checklist`: Must contain exactly 8 items matching predefined template
- `status`: State machine transitions enforced

### Scratchpad
- Section names must be from predefined set
- `updated_by` must be valid agent name or "user"
