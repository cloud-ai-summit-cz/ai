# Service Testing: agent-location-scout

Testing strategy for the LangGraph Hosted Agent.

## Test Matrix

| Layer | Tools | Scope | Owner |
|-------|-------|-------|-------|
| Unit | pytest | LangGraph nodes, tool bindings | Platform Team |
| Local Integration | pytest, REST client | Full agent via localhost:8088 | Platform Team |
| Foundry Integration | pytest | Agent via Responses API | Platform Team |

## Scenarios

### Unit Test Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Neighborhood analysis node | Valid neighborhood data | Node executes | Proper assessment generated |
| Regulation search | Query string | Search tool called | Results formatted correctly |
| Score calculation | Assessment data | Calculate score | Score 0-10 returned |

### Local Integration Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Agent startup | Valid config | `from_langgraph(agent).run()` | Server on 8088 |
| Basic invocation | Agent running | POST /responses | Analysis returned |
| MCP tool usage | MCP mocks available | Agent executes | Tools called correctly |

### Foundry Integration Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Hosted agent deployment | Image in ACR | Deploy to Foundry | Agent running |
| Responses API invocation | Agent deployed | Call via openai_client | Streaming response |

## Environments

### Local Development
```bash
# Start agent locally
uv run python -m agent_location_scout

# Test via REST
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": {"messages": [{"role": "user", "content": "Analyze Vienna"}]}}'
```

### CI Environment
- Mocked MCP servers
- Local agent execution

### Required Fixtures

| Fixture | Purpose | Location |
|---------|---------|----------|
| `mock_mcp_location` | Mock location MCP | conftest.py |
| `mock_mcp_scratchpad` | Mock scratchpad | conftest.py |
| `sample_neighborhoods` | Test data | fixtures/ |

## Quality Gates

### Coverage Targets
| Type | Target |
|------|--------|
| Unit tests | > 70% |
| Integration tests | Critical paths |

### Required CI Jobs
1. `lint` - ruff
2. `unit-tests` - pytest tests/unit
3. `local-integration` - pytest tests/integration
4. `container-build` - Docker build
