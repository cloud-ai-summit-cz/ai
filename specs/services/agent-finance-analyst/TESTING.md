# Service Testing: agent-finance-analyst

Testing strategy for the A2A agent.

## Test Matrix

| Layer | Tools | Scope | Owner |
|-------|-------|-------|-------|
| Unit | pytest | MAF agent, calculations | Platform Team |
| Integration | pytest, httpx | Full agent + A2A server | Platform Team |
| Contract | pact-python | A2A protocol compliance | Platform Team |
| E2E | pytest | Full flow with orchestrator | Platform Team |

## Scenarios

### Unit Test Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Cost calculation | Valid inputs | Calculate costs | Correct totals |
| Break-even analysis | Costs + revenue | Calculate | Valid months |

### A2A Contract Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Agent card endpoint | Server running | GET /.well-known/agent.json | Valid agent card |
| Task creation | Valid A2A request | POST /a2a/tasks | Task accepted |
| Task completion | Task running | Poll status | Completed with result |

### Integration Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Full financial analysis | MCP mocks available | A2A task submitted | Projection returned |
| Auth validation | Invalid token | A2A request | 401 returned |

## Quality Gates

### Coverage Targets
| Type | Target |
|------|--------|
| Unit tests | > 80% |
| A2A contract tests | 100% |

### Required CI Jobs
1. `lint` - ruff
2. `unit-tests` - pytest tests/unit
3. `a2a-contract` - pytest tests/contract
4. `integration-tests` - pytest tests/integration
