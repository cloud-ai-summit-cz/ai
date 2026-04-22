# Service Testing: mcp-scratchpad

## Test Scenarios

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Write section | Valid session | write_section called | Content stored |
| Read section | Existing section | read_section called | Content returned |
| Session isolation | Two sessions | Same section name | Independent data |
