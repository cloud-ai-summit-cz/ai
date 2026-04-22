# Service Testing: agent-research-orchestrator

Testing strategy for the research orchestrator service.

## Test Matrix

| Layer | Tools | Scope | Owner |
|-------|-------|-------|-------|
| Unit | pytest, pytest-asyncio | Business logic, workflows | Platform Team |
| Integration | pytest, testcontainers | API endpoints, agent mocks | Platform Team |
| Contract | pact-python | A2A protocol compliance | Platform Team |
| E2E | pytest, httpx | Full workflow with real agents | Platform Team |

## Scenarios

### Unit Test Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Session creation | Valid request | POST /research/sessions | Session created with UUID |
| Invalid query | Query < 10 chars | POST /research/sessions | 422 validation error |
| Workflow state machine | Session in "running" | Agent completes | State transitions correctly |
| Retry logic | Agent fails once | Retry triggered | Second attempt succeeds |

### Integration Test Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| API health check | Service running | GET /health | 200 OK |
| Session lifecycle | Valid session | Start → Run → Complete | All states visited |
| SSE streaming | Active session | Agent completes | SSE event delivered |
| Agent mock invocation | Mocked Foundry SDK | Invoke market-analyst | Mock response returned |

### Contract Test Scenarios

| Scenario | Provider | Consumer | Contract |
|----------|----------|----------|----------|
| A2A protocol | finance-analyst | orchestrator | A2A v1 schema |
| MCP tools | mcp-scratchpad | orchestrator | MCP protocol |

### E2E Test Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Full research workflow | All agents deployed | Submit "Expand to Vienna?" | Report generated < 3min |
| Agent failure recovery | One agent times out | Workflow continues | Report with partial data |
| User questions | Questions pending | User submits answers | Workflow resumes |

## Environments

### Local Development
```bash
# Start with mocked agents
uv run pytest tests/unit
uv run pytest tests/integration --mock-agents

# Start dependencies
docker compose up -d mcp-scratchpad
```

### CI Environment
- GitHub Actions runner
- Mocked Azure services (azurite, emulators)
- Real Foundry SDK with test project

### Staging Environment
- Real Azure Container Apps
- Real AI Foundry agents (test instances)
- Real MCP servers

### Required Fixtures

| Fixture | Purpose | Location |
|---------|---------|----------|
| `mock_foundry_client` | Mock AIProjectClient | conftest.py |
| `mock_a2a_server` | Mock finance-analyst | conftest.py |
| `mock_mcp_scratchpad` | Mock scratchpad server | conftest.py |
| `sample_research_session` | Pre-populated session | fixtures/ |

## Quality Gates

### Coverage Targets
| Type | Target |
|------|--------|
| Unit tests | > 80% |
| Integration tests | > 60% |
| E2E tests | Critical paths covered |

### Required CI Jobs
1. `lint` - ruff check + format
2. `typecheck` - pyright
3. `unit-tests` - pytest tests/unit
4. `integration-tests` - pytest tests/integration
5. `security-scan` - pip-audit, bandit

### Waiver Process
- Create issue with justification
- Platform team approval required
- Maximum 7-day waiver period

## Test Commands

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=agents --cov-report=html

# Run specific test type
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e

# Run with markers
uv run pytest -m "not slow"
uv run pytest -m "e2e"
```
