# Service Testing: mcp-business-registry

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Search companies | Valid query | search_companies called | Results returned |
| Get profile | Valid company ID | get_company_profile called | Profile returned |
| Unknown company | Invalid ID | get_company_profile called | Graceful error |
