# Service Testing: agent-market-analyst

Testing for Foundry Native agent.

## Test Matrix

| Layer | Tools | Scope |
|-------|-------|-------|
| Prompt Testing | Manual / Playground | Prompt effectiveness |
| Integration | pytest | Agent via SDK with mock MCP |

## Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Market research | Valid city | Agent invoked | Findings written to scratchpad |
| Missing data | City not in database | Agent invoked | Graceful handling |
