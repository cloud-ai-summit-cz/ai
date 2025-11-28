# Service Testing: mcp-web-search

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Web search | Valid query | search_web called | Results returned |
| News search | Valid query + date | search_news called | Articles returned |
| Empty results | No matches | Any search | Empty list, no error |
