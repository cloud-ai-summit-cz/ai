# Service Testing: agent-competitor-analyst

## Test Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Competitor analysis | Valid city, market context | Agent invoked | Analysis written to scratchpad |
| No competitors | Empty competitor data | Agent invoked | Graceful handling |
