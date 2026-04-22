# Service Testing: mcp-calculator

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Calculate startup | Valid inputs | calculate_startup_costs called | Correct total |
| Break even | Revenue > costs | calculate_break_even called | Valid months |
| Invalid input | Negative costs | Any tool | Validation error |
