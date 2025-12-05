# Shared Security Standard

Security controls for Cofilot AI Platform. This is a demo project with relaxed security for ease of demonstration.

> **⚠️ Important**: This project is designed for demos and presentations only. Do not use in production without implementing proper security controls.

---

## Security Classification

| Classification | Description | This Project |
|----------------|-------------|--------------|
| **Data** | All data is mock/synthetic | ✅ No PII, no real business data |
| **Access** | Open demo access | ✅ No authentication required |
| **Network** | Internal VNet for services | ✅ MCP servers not exposed externally |
| **Secrets** | Environment variables | ⚠️ Use Key Vault in real scenarios |

---

## Threat Modeling Expectations

### Methodology

For demo scope, a simplified threat assessment is sufficient:

| Asset | Threats | Mitigations |
|-------|---------|-------------|
| AI Foundry Agents | Prompt injection | Structured prompts, output validation |
| MCP Tool Servers | Unauthorized access | Internal VNet only |
| Mock Data | Data leakage | No sensitive data included |
| Frontend UIs | XSS, CSRF | Vue.js built-in protections |
| Backend API | Injection, DoS | Pydantic validation, rate limiting (optional) |

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET                                  │
│                                                                  │
│    ┌──────────────┐                                             │
│    │ Research UI  │                                             │
│    └──────────────┘                                             │
│            │                                                     │
└────────────┼─────────────────────────────────────────────────────┘
             │
    ─────────┼─────────────────────────────── Trust Boundary 1
             │                                (Public → Private)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CONTAINER APPS ENVIRONMENT                     │
│                                                                  │
│    ┌──────────────────────────────────────────────────────┐     │
│    │                   Backend API                         │     │
│    │               (Public ingress)                        │     │
│    └──────────────────────────────────────────────────────┘     │
│                           │                                      │
│          ─────────────────┼───────────────── Trust Boundary 2    │
│                           │                  (API → Internal)    │
│                           ▼                                      │
│    ┌──────────────────────────────────────────────────────┐     │
│    │              MCP Tool Servers                         │     │
│    │            (Internal only)                            │     │
│    └──────────────────────────────────────────────────────┘     │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
    ────────────────────────┼─────────────────── Trust Boundary 3
                            │                    (Services → Azure)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AZURE SERVICES                              │
│                                                                  │
│    ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│    │ AI Foundry │  │ Cosmos DB  │  │ AI Search  │               │
│    └────────────┘  └────────────┘  └────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Identity & Access

### Demo Configuration (Current)

| Component | Authentication | Authorization |
|-----------|---------------|---------------|
| Frontend UIs | None | Open access |
| Backend API | None | Open access |
| MCP Servers | None (internal only) | Network isolation |
| Azure Services | Managed Identity | Role-based |

### Production Recommendations

> If this project were to be productionized:

| Component | Recommendation |
|-----------|----------------|
| Frontend UIs | Azure AD B2C or Entra ID |
| Backend API | JWT tokens with Azure AD |
| MCP Servers | mTLS between services |
| Azure Services | Managed Identity (already in place) |

### Managed Identity Configuration

```hcl
# Terraform - Container Apps use system-assigned managed identity
resource "azapi_resource" "container_app_backend" {
  # ...
  identity {
    type = "SystemAssigned"
  }
}

# Role assignments for Azure services
resource "azurerm_role_assignment" "cosmos_contributor" {
  scope                = azurerm_cosmosdb_account.main.id
  role_definition_name = "Cosmos DB Data Contributor"
  principal_id         = azapi_resource.container_app_backend.identity[0].principal_id
}
```

---

## Data Protection

### Data Classification

| Data Type | Classification | Handling |
|-----------|---------------|----------|
| Mock market data | Public | No restrictions |
| Mock competitor data | Public | No restrictions |
| Agent prompts | Internal | Version controlled |
| API keys | Secret | Environment variables / Key Vault |

### Encryption

| Layer | Status | Notes |
|-------|--------|-------|
| In Transit | ✅ HTTPS/TLS 1.2+ | Container Apps enforces HTTPS |
| At Rest (Cosmos DB) | ✅ Azure managed | Default encryption |
| At Rest (AI Search) | ✅ Azure managed | Default encryption |
| At Rest (Blob Storage) | ✅ Azure managed | Default encryption |

### No PII Handling

This demo explicitly avoids PII:

```python
# Example: Mock data generation ensures no real PII
MOCK_COMPETITOR = {
    "name": "Cafe Central",           # Fictional business name
    "city": "Vienna",                 # Real city, fictional business details
}

# DO NOT: Use real names, emails, or identifiable information
```

---

## Session Isolation (Multi-Agent Workloads)

### Problem Statement

In multi-agent orchestration, multiple AI agents collaborate on shared resources (scratchpad, notes, etc.). Without proper isolation:

- Session A's agent could accidentally access Session B's data
- Malicious prompts could trick agents into cross-session data access
- Debugging becomes difficult without clear session boundaries

### Security Principle

**Session IDs are infrastructure-controlled, not AI-controlled.**

AI agents CANNOT set or modify session IDs. The orchestrator (trusted application code) injects session context via HTTP headers that agents cannot manipulate.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TRUST BOUNDARY                                     │
│                                                                              │
│  ┌─────────────────┐              ┌─────────────────────────────────────┐   │
│  │   AI Agent      │              │   Orchestrator (Trusted Code)       │   │
│  │                 │              │                                      │   │
│  │ • Receives MCP  │  MCP Call    │ • Creates session-scoped tool       │   │
│  │   tool wrapper  │──────────────▶   wrappers                          │   │
│  │ • Cannot access │  (no         │ • Injects X-Session-ID header       │   │
│  │   session_id    │   session_id)│ • Controls session lifecycle        │   │
│  │                 │              │                                      │   │
│  └─────────────────┘              └──────────────────┬──────────────────┘   │
│                                                      │                       │
└──────────────────────────────────────────────────────┼───────────────────────┘
                                                       │ X-Session-ID: sess_xxx
                                                       ▼
                                        ┌───────────────────────────┐
                                        │   MCP Server              │
                                        │   (e.g., scratchpad)      │
                                        │                           │
                                        │   • Validates header      │
                                        │   • Rejects if missing    │
                                        │   • Isolates data storage │
                                        └───────────────────────────┘
```

### Implementation Requirements

| Component | Responsibility |
|-----------|----------------|
| **Orchestrator** | Create session-scoped MCP tool wrappers that inject `X-Session-ID` header |
| **MCP Servers** | Validate `X-Session-ID` header on every request; reject if missing/invalid |
| **Agent Prompts** | Do NOT include session_id as a tool parameter; agents are unaware of session mechanics |
| **Audit Logging** | Log session_id with every operation for traceability |

### Session ID Requirements

| Requirement | Specification |
|-------------|---------------|
| Format | UUID v4 (e.g., `sess_a1b2c3d4-5678-90ab-cdef-1234567890ab`) |
| Lifetime | Created at session start, valid for 24 hours |
| Uniqueness | Globally unique across all sessions |
| Exposure | Never exposed to end users or AI agents as a settable parameter |

### Validation Matrix

| Scenario | Expected Behavior |
|----------|-------------------|
| Request without X-Session-ID | 400 Bad Request |
| Request with invalid format | 400 Bad Request |
| Request with unknown session | 404 Not Found |
| Request with expired session | 410 Gone |
| Request with valid session | Process normally |

### Audit Requirements

All session-scoped operations must log:

```python
logger.info(
    "session_operation",
    session_id="sess_abc123",           # Which session
    caller_agent="market-analyst",      # Which agent (from X-Caller-Agent header)
    operation="add_note",               # What was done
    resource="scratchpad",              # Which resource
    timestamp="2025-12-01T10:05:00Z"    # When
)
```

---

## Secure Coding & Dependencies

### SAST/DAST Tools

| Tool | Purpose | Frequency |
|------|---------|-----------|
| Ruff | Python linting + security rules | Every PR |
| pip-audit | Dependency vulnerabilities | Every PR |
| npm audit | Node.js dependencies | Every PR |
| Trivy | Container image scanning | On build |

### CI Security Checks

```yaml
# .github/workflows/ci.yml (security section)
security-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Python dependency audit
      run: |
        pip install pip-audit
        pip-audit --requirement requirements.txt
    
    - name: Node.js audit
      run: |
        cd services/frontend-research
        npm audit --audit-level=high
    
    - name: Container scan
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'backend-api:latest'
        severity: 'HIGH,CRITICAL'
```

### Dependency Version Pinning

```toml
# pyproject.toml - Pin all dependencies
[project]
dependencies = [
    "fastapi==0.109.2",
    "pydantic==2.5.3",
    "azure-cosmos==4.7.0",
    "azure-ai-projects==1.0.0b1",
    # ... all versions pinned
]
```

### Severity Thresholds

| Severity | PR Blocking | Action Required |
|----------|-------------|-----------------|
| Critical | ✅ Yes | Immediate fix |
| High | ✅ Yes | Fix before merge |
| Medium | ⚠️ Warning | Fix within sprint |
| Low | ℹ️ Info | Track in backlog |

---

## Secrets Management

### Current Approach (Demo)

Environment variables loaded from `.env` files or Azure Container Apps secrets.

```powershell
# Local development
cp deploy/local/.env.example deploy/local/.env
# Edit .env with your values

# DO NOT commit .env files
# .gitignore includes: .env, .env.local, .env.*.local
```

### Production Recommendation

Use Azure Key Vault with managed identity:

```hcl
# Terraform - Key Vault reference (recommended for production)
resource "azurerm_key_vault" "main" {
  name                = "kv-cofilot-${var.environment}"
  # ...
}

resource "azurerm_key_vault_secret" "cosmos_key" {
  name         = "cosmos-key"
  value        = azurerm_cosmosdb_account.main.primary_key
  key_vault_id = azurerm_key_vault.main.id
}
```

### Secrets Inventory

| Secret | Current Storage | Recommended |
|--------|-----------------|-------------|
| `COSMOS_KEY` | Env var | Key Vault |
| `AI_SEARCH_KEY` | Env var | Key Vault |
| `DOC_INTELLIGENCE_KEY` | Env var | Key Vault |
| `AZURE_OPENAI_KEY` | Env var | Managed Identity |

---

## Logging & Security Events

### Required Log Fields

Every log entry should include:

```python
import logging
import structlog

logger = structlog.get_logger()

# Standard log fields
logger.info(
    "event",
    request_id="req_abc123",      # Correlation ID
    session_id="sess_xyz789",     # Research session
    agent="market-analyst",        # Which agent/service
    action="tool_call",            # What happened
    # Never log secrets or PII
)
```

### Security Events to Log

| Event Code | Description | Severity |
|------------|-------------|----------|
| SEC-001 | Rate limit exceeded | Warning |
| SEC-002 | Invalid input detected | Warning |
| SEC-003 | Tool call timeout | Info |
| SEC-004 | Agent error/retry | Info |
| SEC-005 | Unexpected exception | Error |

### What NOT to Log

```python
# NEVER log these:
# - API keys or tokens
# - Full request/response bodies with sensitive data
# - User credentials
# - PII (even if mock, establish good habits)

# BAD
logger.info("API call", api_key=config.COSMOS_KEY)  # NO!

# GOOD
logger.info("API call", endpoint="cosmos", status=200)
```

---

## Input Validation

### Pydantic Models

All API inputs validated via Pydantic:

```python
from pydantic import BaseModel, Field, validator

class ResearchQueryInput(BaseModel):
    query: str = Field(..., min_length=10, max_length=500)
    
    @validator('query')
    def sanitize_query(cls, v):
        # Basic sanitization
        if '<script>' in v.lower():
            raise ValueError('Invalid characters in query')
        return v.strip()
```

### Agent Prompt Safety

```python
# Agent prompts include safety instructions
MARKET_ANALYST_PROMPT = """
You are a market research analyst.

## Safety Guidelines:
- Only use data from the provided MCP tools
- Do not make up statistics or sources
- If data is unavailable, state "Data not available"
- Do not attempt to access external URLs or systems
- Do not include personal information in responses
"""
```

---

## Network Security

### Container Apps Configuration

```hcl
# Internal-only ingress for MCP servers
resource "azapi_resource" "mcp_scratchpad" {
  # ...
  body = jsonencode({
    properties = {
      configuration = {
        ingress = {
          external = false  # Internal only
          targetPort = 8000
        }
      }
    }
  })
}

# External ingress for Backend API
resource "azapi_resource" "backend_api" {
  # ...
  body = jsonencode({
    properties = {
      configuration = {
        ingress = {
          external = true
          targetPort = 8000
          transport = "http"  # TLS terminated at ingress
        }
      }
    }
  })
}
```

### Service Communication

| From | To | Protocol | Network |
|------|-----|----------|---------|
| Frontend | Backend API | HTTPS | Public |
| Backend API | AI Foundry | HTTPS | Azure backbone |
| AI Foundry | MCP Servers | HTTP | Internal VNet |
| MCP Servers | Cosmos DB | HTTPS | Azure backbone |

---

## Incident Response & Compliance

### Demo Scope

For a demo project, formal incident response is not required. However:

1. **If Azure services become unavailable**: Use pre-recorded demo video as backup
2. **If agents misbehave**: Restart the demo, re-provision agents
3. **If data corruption occurs**: Reset Cosmos DB containers (mock data)

### Evidence Requirements

None for demo scope. For production, would require:
- Log retention: 90 days minimum
- Audit trail: All agent interactions
- Access logs: Who accessed what, when

---

## Specification by Example

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Invalid query input | User submits query with `<script>` tag | API processes request | Request rejected with 422 error |
| Internal service access | External request to MCP server | Request reaches Container Apps | Request blocked (internal only) |
| Dependency vulnerability | pip-audit finds critical CVE | CI runs | Build fails, PR blocked |
| Secret in code | Developer commits API key | Pre-commit hook runs | Commit rejected |

---

## Exceptions

### Current Demo Exceptions

| Exception | Justification | Expiry |
|-----------|---------------|--------|
| No authentication | Demo ease of use | Permanent for demo |
| Env var secrets | Local development simplicity | Move to Key Vault for any production use |
| No WAF | Cost/complexity for demo | Required for production |

### Requesting Exceptions

For production use, document:
1. What control is being bypassed
2. Risk assessment
3. Compensating controls
4. Planned remediation date
5. Approval from security review
