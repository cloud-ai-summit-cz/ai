# Architecture Overview

Cofilot AI Platform - Multi-Agent Demo System for Azure AI Foundry

## Context

### Problem Statement
Demonstrate the capabilities of Azure AI Agent Service and AI Foundry for two contrasting patterns:
1. **Agentic Research** (Part A): Free-form, collaborative multi-agent research with shared memory
2. **Deterministic Workflow** (Part B): Sequential invoice processing with predictable agent handoffs

Additionally, demonstrate **heterogeneous agent deployment patterns**:
- **Microsoft Agent Framework (MAF)** orchestration in standalone containers
- **LangGraph** agents as Foundry Hosted Agents
- **A2A protocol** for cross-platform agent communication
- **Foundry Native** prompt-based agents with MCP tools

### Business Drivers
- Conference demos and customer presentations (target: December 8, 2025)
- POC/workshop enablement for Azure AI Agent Service adoption
- Illustrate contrast between agentic vs. workflow-based AI patterns
- Demonstrate multi-framework agent interoperability

### User Personas
| Persona | System Interaction |
|---------|-------------------|
| Business Strategist | Submits research queries, answers clarifying questions, receives reports |
| Supplier | Uploads invoices via web portal |
| PO Owner | Receives approval recommendations via Teams notification |
| Demo Audience | Observes real-time agent activity and decision visualization |

---

## Views

### System Context Diagram

```mermaid
C4Context
    title Cofilot AI Platform - System Context

    Person(strategist, "Business Strategist", "Asks research questions")
    Person(supplier, "Supplier", "Submits invoices")
    Person(po_owner, "PO Owner", "Approves invoices")
    Person(demo_audience, "Demo Audience", "Observes demo")

    System_Boundary(cofilot, "Cofilot AI Platform") {
        System(frontend_a, "Research UI", "Vue.js SPA")
        System(frontend_b, "Invoice UI", "Vue.js SPA")
        System(backend, "Backend API", "FastAPI + SSE")
        System(foundry, "AI Foundry Agents", "Managed Agents")
        System(mcp_servers, "MCP Tool Servers", "FastMCP Containers")
    }

    System_Ext(cosmos, "Azure Cosmos DB", "Scratchpad + Events")
    System_Ext(ai_search, "Azure AI Search", "Semantic Search")
    System_Ext(doc_intel, "Document Intelligence", "OCR")
    System_Ext(aoai, "Azure OpenAI", "LLM Models")
    System_Ext(teams, "Microsoft Teams", "Notifications")

    Rel(strategist, frontend_a, "Uses")
    Rel(supplier, frontend_b, "Uploads invoices")
    Rel(po_owner, teams, "Receives notifications")
    Rel(demo_audience, frontend_a, "Observes")
    Rel(demo_audience, frontend_b, "Observes")

    Rel(frontend_a, backend, "REST + SSE")
    Rel(frontend_b, backend, "REST + SSE")
    Rel(backend, foundry, "Agent orchestration")
    Rel(foundry, mcp_servers, "MCP protocol")
    Rel(mcp_servers, cosmos, "Read/Write")
    Rel(mcp_servers, ai_search, "Search")
    Rel(mcp_servers, doc_intel, "OCR")
    Rel(foundry, aoai, "LLM calls")
```

### Container / Service View

| Component | Responsibility | Tech Stack | Deployment Target | Owners |
|-----------|---------------|------------|-------------------|--------|
| `frontend-research` | Research scenario UI with agent visualization | React, Vite, TailwindCSS | Azure Container Apps | Frontend |
| `frontend-invoice` | Invoice workflow UI with event stream | Vue.js 3, Vite, TailwindCSS | Azure Container Apps | Frontend |
| `backend-api` | REST API, SSE streaming, agent coordination | Python 3.11, FastAPI, Pydantic | Azure Container Apps | Backend |
| **Research Agents** | | | | |
| `agent-research-orchestrator` | MAF-based orchestrator with REST API for web UI | Python 3.11, MAF, FastAPI | Azure Container Apps | Platform |
| `agent-location-scout` | LangGraph agent for location/regulation analysis | Python 3.11, LangGraph, Hosted Agent Adapter | Foundry Hosted Agent | Platform |
| `agent-finance-analyst` | MAF agent exposed via A2A protocol | Python 3.11, MAF, A2A server | Azure Container Apps | Platform |
| `agent-market-analyst` | Foundry native agent for market research | Prompt-based, AI Foundry | AI Foundry Managed | Platform |
| `agent-competitor-analyst` | Foundry native agent for competitor analysis | Prompt-based, AI Foundry | AI Foundry Managed | Platform |
| `agent-synthesizer` | Foundry native agent for report synthesis | Prompt-based, AI Foundry | AI Foundry Managed | Platform |
| **MCP Tool Servers** | | | | |
| `mcp-scratchpad` | Shared memory tools for research agents | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-web-search` | Web search, news, social media tools | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-business-registry` | Company data, financials, industry players | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-government-data` | Permits, zoning, regulations, tax rates | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-demographics` | Population, income, consumer behavior | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-real-estate` | Properties, rental rates, foot traffic | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-calculator` | Financial calculations and projections | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-document` | Invoice OCR and extraction | Python 3.11, FastMCP, Doc Intelligence | Azure Container Apps | Backend |
| `mcp-po` | Purchase order data tools | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-policy` | Policy and tax rules tools | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-workflow` | Workflow state and events | Python 3.11, FastMCP | Azure Container Apps | Backend |
| `mcp-notification` | Teams notification (mock) | Python 3.11, FastMCP | Azure Container Apps | Backend |

### Component Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend Layer (Container Apps)"]
        FE_A[Research UI<br/>React]
        FE_B[Invoice UI<br/>Vue.js]
    end

    subgraph Backend["Backend Layer (Container Apps)"]
        API[Backend API<br/>FastAPI]
    end

    subgraph Orchestration["Orchestration Layer"]
        ORCH_A[research-orchestrator<br/>MAF + FastAPI<br/>Container Apps]
    end

    subgraph AIFoundry["AI Foundry"]
        subgraph HostedAgents["Hosted Agents"]
            LS[location-scout<br/>LangGraph]
        end
        subgraph NativeAgents["Native Agents"]
            MA[market-analyst]
            CA[competitor-analyst]
            SY[synthesizer]
        end
        THREADS[(Agent Threads<br/>+ Memory)]
    end

    subgraph A2ALayer["A2A Layer (Container Apps)"]
        FA[finance-analyst<br/>MAF + A2A Server]
    end

    subgraph MCPLayer["MCP Tool Servers (Container Apps)"]
        subgraph ResearchMCP["Research Tools"]
            MCP_SP[mcp-scratchpad]
            MCP_WS[mcp-web-search]
            MCP_BR[mcp-business-registry]
            MCP_GD[mcp-government-data]
            MCP_DM[mcp-demographics]
            MCP_RE[mcp-real-estate]
            MCP_CA[mcp-calculator]
        end
        subgraph InvoiceMCP["Invoice Tools"]
            MCP_DO[mcp-document]
            MCP_PO[mcp-po]
            MCP_PL[mcp-policy]
            MCP_WF[mcp-workflow]
            MCP_NO[mcp-notification]
        end
    end

    subgraph DataLayer["Data Layer"]
        COSMOS[(Cosmos DB)]
        SEARCH[(AI Search)]
        BLOB[(Blob Storage)]
    end

    subgraph ExternalServices["External Services"]
        DOCINTEL[Document Intelligence]
        AOAI[Azure OpenAI]
    end

    FE_A <-->|REST + SSE| ORCH_A
    FE_B <-->|SSE + REST| API
    API <-->|Agent SDK| AIFoundry
    
    ORCH_A <-->|Foundry SDK| NativeAgents
    ORCH_A <-->|Foundry SDK| HostedAgents
    ORCH_A <-->|A2A Protocol| FA
    
    NativeAgents <-->|MCP| ResearchMCP
    HostedAgents <-->|MCP| MCP_GD
    HostedAgents <-->|MCP| MCP_DM
    HostedAgents <-->|MCP| MCP_RE
    FA <-->|MCP| MCP_CA
    FA <-->|MCP| MCP_BR
    
    MCP_SP --> COSMOS
    MCP_WF --> COSMOS
    MCP_MD --> SEARCH
    MCP_LO --> SEARCH
    MCP_PL --> SEARCH
    MCP_DO --> DOCINTEL
    
    AIFoundry --> AOAI
    ORCH_A --> AOAI
    FA --> AOAI
```

### Agent Deployment Patterns

| Pattern | Agent | Framework | Hosting | Communication |
|---------|-------|-----------|---------|---------------|
| **MAF Orchestrator** | research-orchestrator | Microsoft Agent Framework | Container Apps | REST API (web UI), SDK (Foundry agents), A2A (finance-analyst) |
| **Foundry Hosted Agent** | location-scout | LangGraph | Foundry Hosted Agent | Foundry Responses API, MCP |
| **A2A External Agent** | finance-analyst | Microsoft Agent Framework | Container Apps | A2A Protocol (managed identity auth) |
| **Foundry Native** | market-analyst, competitor-analyst, synthesizer | Prompt-based | AI Foundry Managed | Foundry Agent SDK, MCP |

---

## Scenario A: Research Agents Detail

### Agent Definitions

| Agent | Framework | Hosting | System Prompt Summary | MCP Servers |
|-------|-----------|---------|----------------------|-------------|
| **research-orchestrator** | MAF | Container Apps | Coordinates research workflow via REST API. Decides which agent to invoke, manages user questions. | `mcp-scratchpad` |
| **market-analyst** | Foundry Native | AI Foundry Managed | Researches market size, growth trends, customer segments. Writes findings to scratchpad. | `mcp-scratchpad`, `mcp-web-search`, `mcp-demographics` |
| **competitor-analyst** | Foundry Native | AI Foundry Managed | Identifies and profiles competitors. Reads market context from scratchpad first. | `mcp-scratchpad`, `mcp-web-search`, `mcp-business-registry` |
| **location-scout** | LangGraph | Foundry Hosted Agent | Evaluates neighborhoods, regulations, rent. Can search regulatory database. | `mcp-scratchpad`, `mcp-government-data`, `mcp-demographics`, `mcp-real-estate` |
| **finance-analyst** | MAF | Container Apps (A2A) | Creates financial projections based on gathered data. Reads all sections from scratchpad. | `mcp-scratchpad`, `mcp-business-registry`, `mcp-government-data`, `mcp-real-estate`, `mcp-calculator` |
| **synthesizer** | Foundry Native | AI Foundry Managed | Compiles final report with recommendation. Reviews all scratchpad sections. | `mcp-scratchpad`, `mcp-calculator` |

### Research Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Research UI (React)
    participant Orch as research-orchestrator<br/>(MAF + Container Apps)
    participant SP as mcp-scratchpad
    participant MA as market-analyst<br/>(Foundry Native)
    participant CA as competitor-analyst<br/>(Foundry Native)
    participant LS as location-scout<br/>(LangGraph Hosted)
    participant FA as finance-analyst<br/>(MAF + A2A)
    participant SY as synthesizer<br/>(Foundry Native)

    User->>UI: "Should Cofilot expand to Vienna?"
    UI->>Orch: POST /research/start
    
    Orch->>SP: read_checklist()
    SP-->>Orch: checklist status
    
    loop Until checklist complete
        alt Questions pending
            Orch->>UI: SSE: questions_pending
            UI->>User: Show questions modal
            User->>UI: Answers
            UI->>Orch: POST /research/{id}/answers
            Orch->>SP: write_answers()
        end
        
        Orch->>MA: Invoke via Foundry SDK
        MA->>SP: write_section(market_findings)
        Orch->>UI: SSE: agent_activity(market-analyst)
        
        Orch->>CA: Invoke via Foundry SDK
        CA->>SP: write_section(competitor_analysis)
        Orch->>UI: SSE: agent_activity(competitor-analyst)
        
        Orch->>LS: Invoke via Foundry Responses API
        LS->>SP: write_section(location_options)
        Orch->>UI: SSE: agent_activity(location-scout)
        
        Orch->>FA: Invoke via A2A Protocol
        FA->>SP: write_section(financial_projections)
        Orch->>UI: SSE: agent_activity(finance-analyst)
    end
    
    Orch->>SY: Invoke via Foundry SDK
    SY->>SP: read_all_sections()
    SY-->>Orch: Final report
    Orch->>UI: SSE: research_complete
    UI->>User: Display report
```

### MCP Server: mcp-scratchpad

```
Tools:
├── read_section(section: str) -> dict
│   Sections: market_findings, competitor_analysis, location_options, 
│             regulations, financial_projections, user_answers
├── write_section(section: str, content: dict) -> bool
├── append_to_section(section: str, content: dict) -> bool
├── list_sections() -> list[str]
├── read_checklist() -> list[ChecklistItem]
├── update_checklist(item_id: int, status: str, notes: str) -> bool
├── add_question(question: str, context: str, priority: str) -> str
├── get_pending_questions() -> list[Question]
└── submit_answers(answers: dict) -> bool
```

### MCP Server: mcp-web-search

```
Tools:
├── search_web(query: str, max_results: int, region: str) -> WebSearchResponse
├── search_news(query: str, days_back: int, category: str) -> NewsSearchResponse
├── search_images(query: str, image_type: str) -> ImageSearchResponse
├── get_webpage_content(url: str) -> WebpageContent
└── search_social_media(query: str, platforms: list[str]) -> SocialSearchResponse
```

### MCP Server: mcp-business-registry

```
Tools:
├── search_companies(query: str, industry: str, location: str) -> list[CompanySummary]
├── get_company_profile(company_id: str) -> CompanyProfile
├── get_company_financials(company_id: str) -> CompanyFinancials
├── get_company_locations(company_id: str, city: str) -> list[CompanyLocation]
├── get_industry_players(industry: str, region: str, limit: int) -> list[IndustryPlayer]
└── get_company_news(company_id: str, days_back: int) -> list[NewsArticle]
```

### MCP Server: mcp-government-data

```
Tools:
├── get_business_permits(city: str, business_type: str) -> list[BusinessPermit]
├── get_zoning_info(city: str, district: str) -> ZoningInfo
├── get_regulations(country: str, industry: str, category: str) -> list[Regulation]
├── get_tax_rates(country: str, city: str) -> list[TaxInfo]
├── get_licensing_requirements(country: str, profession: str) -> list[LicenseRequirement]
├── get_health_safety_codes(country: str, establishment_type: str) -> list[HealthSafetyCode]
└── get_labor_laws(country: str, topics: list[str]) -> list[LaborLaw]
```

### MCP Server: mcp-demographics

```
Tools:
├── get_population_stats(city: str, district: str) -> PopulationStats
├── get_income_distribution(city: str, district: str) -> IncomeDistribution
├── get_age_distribution(city: str, district: str) -> AgeDistribution
├── get_consumer_spending(city: str, category: str) -> ConsumerSpending
├── get_lifestyle_segments(city: str, district: str) -> list[LifestyleSegment]
└── get_commuter_patterns(city: str, district: str, day_type: str) -> CommuterPattern
```

### MCP Server: mcp-real-estate

```
Tools:
├── search_commercial_properties(city: str, district: str, property_type: str) -> list[CommercialProperty]
├── get_rental_rates(city: str, district: str) -> RentalRates
├── get_foot_traffic(city: str, district: str) -> FootTraffic
├── get_nearby_amenities(city: str, address: str, radius_meters: int) -> list[NearbyAmenity]
├── get_location_score(city: str, district: str, business_type: str) -> LocationScore
├── get_vacancy_rates(city: str, district: str) -> VacancyRate
└── compare_locations(locations: list[Location], criteria: list[str]) -> LocationComparison
```

### MCP Server: mcp-calculator

```
Tools:
├── calculate_startup_costs(inputs: StartupCostInput) -> StartupCostResult
├── calculate_operating_costs(inputs: OperatingCostInput) -> OperatingCostResult
├── calculate_break_even(startup: float, monthly_fixed: float, avg_transaction: float) -> BreakEvenResult
├── calculate_roi(initial_investment: float, annual_profit: float, years: int) -> ROIResult
├── project_revenue(year1_monthly: float, growth_rate: float, years: int) -> list[RevenueProjection]
├── project_cash_flow(initial: float, monthly_revenue: float, monthly_costs: float, months: int) -> list[CashFlowProjection]
├── calculate_npv(initial: float, annual_cash_flows: list[float], discount_rate: float) -> NPVResult
└── sensitivity_analysis(base_profit: float, variable: str, base_value: float, impact_per_unit: float) -> SensitivityResult
```

---

## Scenario B: Invoice Agents Detail

### Agent Definitions (AI Foundry Managed)

| Agent | System Prompt Summary | Connected MCP Servers |
|-------|----------------------|----------------------|
| **invoice-orchestrator** | Sequential workflow coordinator. Invokes agents in order, handles errors. | `mcp-workflow` |
| **intake-agent** | Extracts invoice data using Document Intelligence + LLM for field mapping. | `mcp-document`, `mcp-workflow` |
| **validation-agent** | Validates PO exists, checks against policies and tax rules. | `mcp-po`, `mcp-policy`, `mcp-workflow` |
| **reconciliation-agent** | Compares invoice line items to PO details, flags discrepancies. | `mcp-po`, `mcp-workflow` |
| **routing-agent** | Identifies PO owner and determines approval chain. | `mcp-po`, `mcp-workflow` |
| **recommendation-agent** | Generates approval/rejection recommendation with reasoning. | `mcp-workflow` |
| **notification-agent** | Sends Teams notification to approver (mocked). | `mcp-notification`, `mcp-workflow` |

### Invoice Flow

```mermaid
sequenceDiagram
    participant User as Supplier
    participant UI as Invoice UI
    participant API as Backend API
    participant Orch as Orchestrator
    participant WF as mcp-workflow
    participant Agents as Sequential Agents
    participant Tools as MCP Tools

    User->>UI: Upload invoice PDF
    UI->>API: POST /invoice/upload
    API->>WF: emit_event(invoice_received)
    API->>UI: SSE: invoice_received
    
    API->>Orch: Create thread + invoke
    
    Orch->>Agents: Invoke Intake Agent
    Agents->>Tools: extract_invoice_data()
    Tools-->>Agents: Extracted fields
    Agents->>WF: emit_event(data_extracted)
    API->>UI: SSE: data_extracted
    
    Orch->>Agents: Invoke Validation Agent
    Agents->>Tools: validate_po_exists(), check_policies()
    Agents->>WF: emit_event(validation_complete)
    API->>UI: SSE: validation_complete
    
    Orch->>Agents: Invoke Reconciliation Agent
    Agents->>Tools: compare_to_po()
    Agents->>WF: emit_event(reconciliation_complete)
    API->>UI: SSE: reconciliation_complete
    
    Orch->>Agents: Invoke Routing Agent
    Agents->>Tools: get_po_owner()
    Agents->>WF: emit_event(routing_complete)
    
    Orch->>Agents: Invoke Recommendation Agent
    Agents->>WF: emit_event(recommendation_generated)
    API->>UI: SSE: recommendation_generated
    
    Orch->>Agents: Invoke Notification Agent
    Agents->>Tools: send_teams_message()
    Agents->>WF: emit_event(notification_sent)
    API->>UI: SSE: workflow_complete
```

### MCP Server: mcp-document

```
Tools:
└── extract_invoice_data(document_url: str) -> InvoiceData
    Uses: Azure Document Intelligence (prebuilt-invoice model)
    + LLM for field mapping and normalization
    Returns: vendor, po_number, invoice_number, date, amount, 
             tax, line_items[], currency
```

### MCP Server: mcp-po

```
Tools:
├── validate_po_exists(po_number: str) -> bool
├── get_po(po_number: str) -> PurchaseOrder
│   Returns: po_number, vendor, items[], total_amount, owner, status
├── get_po_owner(po_number: str) -> POOwner
│   Returns: name, email, teams_id, approval_limit
└── compare_invoice_to_po(invoice: InvoiceData, po_number: str) -> ComparisonResult
    Returns: matches, discrepancies[], recommendation
```

### MCP Server: mcp-policy

```
Tools:
├── check_approval_threshold(amount: float, owner_limit: float) -> PolicyResult
├── check_vendor_policy(vendor_id: str) -> PolicyResult
├── search_tax_rules(query: str, jurisdiction: str) -> list[TaxRule]
│   Uses: Azure AI Search
└── validate_tax_compliance(invoice: InvoiceData, jurisdiction: str) -> TaxComplianceResult
```

### MCP Server: mcp-workflow

```
Tools:
├── emit_event(event_type: str, payload: dict) -> str
│   Event types: invoice_received, data_extracted, validation_complete,
│                reconciliation_complete, routing_complete, 
│                recommendation_generated, notification_sent
├── get_workflow_status(workflow_id: str) -> WorkflowStatus
├── update_workflow_data(workflow_id: str, data: dict) -> bool
└── get_workflow_events(workflow_id: str) -> list[Event]
```

### MCP Server: mcp-notification

```
Tools:
└── send_teams_message(
        recipient_id: str,
        subject: str,
        body: str,
        invoice_summary: InvoiceSummary,
        recommendation: Recommendation
    ) -> NotificationResult
    Note: Mock implementation - logs to console and stores in Cosmos DB
```

---

## Cross-Cutting Concerns

### Security Posture
- **Authentication**: None for demo (open access)
- **Data Classification**: All data is mock/synthetic - no PII
- **Network**: Container Apps with internal VNet for MCP servers
- See `SECURITY.md` for details

### Performance Characteristics
| Metric | Target | Strategy |
|--------|--------|----------|
| Research scenario E2E | < 3 minutes | Parallel agent calls where possible |
| Invoice scenario E2E | < 10 seconds | Sequential but optimized |
| UI update latency | < 500ms | SSE streaming |
| Agent response time | < 5 seconds per turn | Model selection (GPT-4o for speed) |

### Resilience
- **Retry Strategy**: Exponential backoff for AI Foundry API calls
- **Fallback**: Pre-recorded demo responses for critical failures
- **Circuit Breaker**: Not implemented (demo scope)

---

## Dependencies

### Azure Services
| Service | Purpose | SKU/Tier |
|---------|---------|----------|
| Azure AI Foundry | Managed agents, threads | Standard |
| Azure OpenAI | GPT-4o, GPT-4o-mini | Standard |
| Azure Cosmos DB | Scratchpad, events | Serverless |
| Azure AI Search | Semantic search | Basic |
| Azure Document Intelligence | Invoice OCR | S0 |
| Azure Container Apps | All containers | Consumption |
| Azure Container Registry | Container images | Basic |

### Third-Party Libraries
| Library | Purpose | Version |
|---------|---------|---------|
| FastAPI | Backend API framework | ^0.109.0 |
| FastMCP | MCP server framework | ^0.1.0 |
| azure-ai-projects | AI Foundry SDK | ^1.0.0 |
| azure-cosmos | Cosmos DB client | ^4.7.0 |
| azure-ai-formrecognizer | Document Intelligence | ^3.3.0 |
| pydantic | Data validation | ^2.5.0 |
| Vue.js | Frontend framework | ^3.4.0 |

---

## Specification by Example

| Scenario | Given | When | Then |
|----------|-------|------|------|
| SSE event delivery | User starts research | Agent completes a step | UI receives SSE event within 500ms |
| Scratchpad persistence | Market analyst writes findings | Competitor analyst runs | Competitor agent can read market findings |
| Agent thread isolation | Two concurrent research sessions | Both complete | Each session has isolated thread/memory |
| MCP tool timeout | MCP server is slow (>30s) | Agent calls tool | Agent receives timeout error, can retry |
| Document extraction | Valid invoice PDF uploaded | Intake agent runs | All fields extracted with >90% accuracy |

---

## Decision References

- ADR-001: Use AI Foundry Managed Agents (pending)
- ADR-002: MCP over direct function calling (pending)
- ADR-003: SSE over WebSocket for real-time updates (pending)
- ADR-004: Separate frontends per scenario (pending)
