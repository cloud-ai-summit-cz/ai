# Cofilot AI Platform

> Multi-agent research orchestration demo using Microsoft Agent Framework on Azure

This project demonstrates a **collaborative AI research workflow** where multiple specialized agents work together to investigate business expansion opportunities for a specialty coffee company.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    WEB RESEARCH UI                                      │
│                              (React + Server-Sent Events)                               │
└─────────────────────────────────────┬───────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                             RESEARCH ORCHESTRATOR                                       │
│                        (Microsoft Agent Framework + A2A)                                │
│                                                                                         │
│  • Receives research queries           • Delegates to specialist agents                 │
│  • Manages research plan               • Tracks progress via Scratchpad                 │
│  • Coordinates agent collaboration     • Streams real-time SSE updates                  │
└───────┬───────────────┬───────────────┬───────────────┬───────────────┬─────────────────┘
        │               │               │               │               │
        ▼               ▼               ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│    MARKET     │ │  COMPETITOR   │ │   LOCATION    │ │   FINANCE     │ │  SYNTHESIZER  │
│   ANALYST     │ │   ANALYST     │ │    SCOUT      │ │   ANALYST     │ │    (Exit)     │
│               │ │               │ │               │ │               │ │               │
│ Demographics  │ │ Business      │ │ Government    │ │ Calculator    │ │ Scratchpad    │
│ Web Search    │ │ Registry      │ │ Demographics  │ │ Real Estate   │ │ Calculator    │
│ Scratchpad    │ │ Web Search    │ │ Real Estate   │ │ Government    │ │               │
│               │ │ Scratchpad    │ │ Web Search    │ │ Business Reg  │ │ Reads all     │
│               │ │               │ │ Scratchpad    │ │ Web Search    │ │ agent outputs │
│               │ │               │ │               │ │ Scratchpad    │ │ → Final Report│
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
        │               │               │               │               │
        └───────────────┴───────────────┴───────────────┴───────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              MCP SCRATCHPAD (Shared Memory)                            │
│                                                                                        │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│   │    PLAN     │    │   NOTES     │    │   DRAFTS    │    │  QUESTIONS  │             │
│   │             │    │             │    │             │    │    (HITL)   │             │
│   │ • add_tasks │    │ • add_note  │    │ • write_    │    │ • add_      │             │
│   │ • update_   │    │ • read_     │    │   draft_    │    │   question  │             │
│   │   task      │    │   notes     │    │   section   │    │ • get_      │             │
│   │ • read_plan │    │             │    │ • read_     │    │   pending_  │             │
│   │             │    │             │    │   draft     │    │   questions │             │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                                        │
│   Session-isolated via X-Session-ID header (agents cannot access other sessions)       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Specifications

### Research Orchestrator
**Role**: Project manager that coordinates the entire research workflow

| Capability | Description |
|------------|-------------|
| **Query Analysis** | Breaks down research requests into actionable tasks |
| **Agent Delegation** | Calls specialist agents via A2A protocol |
| **Progress Tracking** | Monitors task completion via Scratchpad |
| **Quality Control** | Ensures research depth before synthesis |

**MCP Tools**: `mcp-scratchpad` (full access to plan, notes, drafts)

---

### Market Analyst
**Role**: Analyzes market conditions, demographics, and consumer behavior

| MCP Server | Tools |
|------------|-------|
| **mcp-demographics** | `get_population_stats`, `get_income_distribution`, `get_age_distribution`, `get_consumer_spending`, `get_lifestyle_segments`, `get_commuter_patterns` |
| **mcp-scratchpad** | `add_note`, `read_notes`, `write_draft_section`, `read_draft` |
| **Web Search** | Grounded Bing search for real-time market trends |

---

### Competitor Analyst
**Role**: Profiles competitors and analyzes the competitive landscape

| MCP Server | Tools |
|------------|-------|
| **mcp-business-registry** | `search_companies`, `get_company_profile`, `get_company_financials`, `get_company_locations`, `get_industry_players`, `get_company_news` |
| **mcp-scratchpad** | `add_note`, `read_notes`, `write_draft_section`, `read_draft` |
| **Web Search** | Grounded Bing search for competitor news and reviews |

---

### Location Scout
**Role**: Evaluates commercial real estate and site suitability

| MCP Server | Tools |
|------------|-------|
| **mcp-government-data** | `get_business_permits`, `get_zoning_info`, `get_regulations`, `get_tax_rates`, `get_licensing_requirements`, `get_health_safety_codes`, `get_labor_laws` |
| **mcp-demographics** | `get_population_stats`, `get_income_distribution`, `get_commuter_patterns` |
| **mcp-real-estate** | `search_properties`, `get_rental_rates`, `get_foot_traffic`, `get_nearby_amenities`, `get_location_score`, `get_vacancy_rates`, `compare_locations` |
| **mcp-scratchpad** | `add_note`, `read_notes`, `write_draft_section`, `read_draft` |
| **Web Search** | Grounded Bing search for location intelligence |

---

### Finance Analyst
**Role**: Creates financial projections and investment analysis

| MCP Server | Tools |
|------------|-------|
| **mcp-calculator** | `startup_costs`, `operating_costs`, `project_revenue`, `break_even`, `roi`, `cash_flow`, `sensitivity_analysis` |
| **mcp-real-estate** | `get_rental_rates`, `search_properties` |
| **mcp-government-data** | `get_tax_rates`, `get_regulations` |
| **mcp-business-registry** | `get_company_financials` (for benchmarks) |
| **mcp-scratchpad** | `add_note`, `read_notes`, `write_draft_section`, `read_draft` |
| **Web Search** | Grounded Bing search for financial benchmarks |

---

### Synthesizer (Exit Agent)
**Role**: Compiles all research into final strategic recommendation

| MCP Server | Tools |
|------------|-------|
| **mcp-scratchpad** | `read_notes`, `read_draft`, `read_plan`, `write_draft_section` |
| **mcp-calculator** | ROI/NPV calculations for final recommendations |

**Output Sections**: `executive_summary`, `recommendation`, `risk_assessment`

---

## 🔄 Collaboration via Scratchpad

The MCP Scratchpad enables asynchronous collaboration between agents through four pillars:

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                           SCRATCHPAD COLLABORATION FLOW                              │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 📋 PLAN - Task Coordination                                                    │  │
│  ├────────────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                                │  │
│  │  Orchestrator                                                                  │  │
│  │      │                                                                         │  │
│  │      ├──► add_tasks([                                                          │  │
│  │      │      {description: "Analyze Brno market demographics"},                 │  │
│  │      │      {description: "Profile specialty coffee competitors"},             │  │
│  │      │      {description: "Evaluate Veveří district viability"},               │  │
│  │      │      {description: "Project 3-year financials"},                        │  │
│  │      │      {description: "Synthesize findings → recommendation"}              │  │
│  │      │    ])                                                                   │  │
│  │      │                                                                         │  │
│  │      └──► update_task(task_id, status="completed") ◄─ after agent reports      │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 📝 NOTES - Raw Findings (The Corkboard)                                        │  │
│  ├────────────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                                │  │
│  │  Market Analyst ──► add_note("Brno population: 382,000", tags=["demographics"])│  │
│  │                                                                                │  │
│  │  Competitor ──────► add_note("Coffee Koruna: 12 locations in Brno",            │  │
│  │                              tags=["competitor", "brno"])                      │  │
│  │                                                                                │  │
│  │  Location Scout ──► add_note("Veveří avg rent: €18/sqm/month",                 │  │
│  │                              tags=["real-estate", "brno"])                     │  │
│  │                                                                                │  │
│  │  Finance ─────────► add_note("Break-even at 120 customers/day",                │  │
│  │                              tags=["financial", "projection"])                 │  │
│  │                                                                                │  │
│  │  Any Agent ───────► read_notes(tag="competitor") ◄─ Cross-reference findings   │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 📄 DRAFTS - Structured Report Sections (The Manuscript)                        │  │
│  ├────────────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                                │  │
│  │  Market Analyst ──► write_draft_section(                                       │  │
│  │                        section_id="market_analysis",                           │  │
│  │                        title="Market Analysis: Brno",                          │  │
│  │                        content="## Overview\nBrno represents a growing..."     │  │
│  │                     )                                                          │  │
│  │                                                                                │  │
│  │  Competitor ──────► write_draft_section(                                       │  │
│  │                        section_id="competitor_landscape",                      │  │
│  │                        title="Competitive Landscape",                          │  │
│  │                        content="## Key Players\n1. Coffee Koruna..."           │  │
│  │                     )                                                          │  │
│  │                                                                                │  │
│  │  Synthesizer ─────► read_draft() ◄─ Reads ALL sections                         │  │
│  │                 └─► write_draft_section(section_id="executive_summary", ...)   │  │
│  │                 └─► write_draft_section(section_id="recommendation", ...)      │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │ ❓ QUESTIONS - Human-in-the-Loop (HITL)                                        │  │
│  ├────────────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                                │  │
│  │  Any Agent ───────► add_question(                                              │  │
│  │                        question="Should we prioritize Brno or Vienna?",        │  │
│  │                        priority="high",                                        │  │
│  │                        context="Market data suggests similar opportunity..."   │  │
│  │                     )                                                          │  │
│  │                                                                                │  │
│  │  Web UI ──────────► get_pending_questions() ◄─ Shows to human user             │  │
│  │                                                                                │  │
│  │  Human User ──────► submit_answers([{question_id, answer}])                    │  │
│  │                                                                                │  │
│  │  Orchestrator ────► get_answered_questions() ◄─ Incorporates human guidance    │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 MCP Server Reference

| Server | Purpose | Tools |
|--------|---------|-------|
| **mcp-scratchpad** | Inter-agent collaboration | `add_note`, `read_notes`, `write_draft_section`, `read_draft`, `add_tasks`, `update_task`, `read_plan`, `add_question`, `get_pending_questions`, `submit_answers` |
| **mcp-demographics** | Population & consumer data | `get_population_stats`, `get_income_distribution`, `get_age_distribution`, `get_consumer_spending`, `get_lifestyle_segments`, `get_commuter_patterns` |
| **mcp-business-registry** | Company profiles & industry data | `search_companies`, `get_company_profile`, `get_company_financials`, `get_company_locations`, `get_industry_players`, `get_company_news` |
| **mcp-government-data** | Permits, zoning, regulations | `get_business_permits`, `get_zoning_info`, `get_regulations`, `get_tax_rates`, `get_licensing_requirements`, `get_health_safety_codes`, `get_labor_laws` |
| **mcp-real-estate** | Commercial property analysis | `search_properties`, `get_rental_rates`, `get_foot_traffic`, `get_nearby_amenities`, `get_location_score`, `get_vacancy_rates`, `compare_locations` |
| **mcp-calculator** | Financial projections | `startup_costs`, `operating_costs`, `project_revenue`, `break_even`, `roi`, `cash_flow`, `sensitivity_analysis` |

---

## 📁 Project Structure

```
src/
├── agent-research-orchestrator/    # Main orchestrator (FastAPI + SSE)
├── agent-market-analyst/           # Market analysis specialist
├── agent-competitor-analyst/       # Competitive intelligence
├── agent-location-scout/           # Site selection specialist
├── agent-finance-analyst/          # Financial modeling
├── agent-synthesizer/              # Final report compilation
│
├── mcp-scratchpad/                 # Shared memory for agents
├── mcp-demographics/               # Population & consumer data
├── mcp-business-registry/          # Company database
├── mcp-government-data/            # Permits & regulations
├── mcp-real-estate/                # Property listings
├── mcp-calculator/                 # Financial calculations
│
└── web-research/                   # React frontend
```

---

## 🚀 Quick Start

See individual service READMEs for setup instructions:
- [Research Orchestrator](src/agent-research-orchestrator/README.md)
- [MCP Scratchpad](src/mcp-scratchpad/README.md)

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.
