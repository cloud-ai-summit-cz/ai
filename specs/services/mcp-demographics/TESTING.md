# Service Testing: mcp-demographics

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Get population | Valid city | get_population_stats called | Stats returned |
| Get income | Valid location | get_income_distribution called | Distribution returned |
