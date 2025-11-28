# Service Testing: mcp-government-data

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Get permits | Valid city + business | get_business_permits called | Permits returned |
| Get zoning | Valid location | get_zoning_info called | Zoning returned |
| Unknown location | Invalid city | Any tool | Empty/default response |
