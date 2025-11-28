# Service Data Models: mcp-web-search

## Tool Response Schemas

```python
class WebSearchResult(BaseModel):
    """Single web search result."""
    title: str
    url: str
    snippet: str
    published_date: datetime | None = None

class WebSearchResponse(BaseModel):
    """Response from search_web tool."""
    query: str
    results: list[WebSearchResult]
    total_results: int

class NewsArticle(BaseModel):
    """News article result."""
    title: str
    source: str
    url: str
    summary: str
    published_date: datetime
    sentiment: Literal["positive", "neutral", "negative"] | None = None

class NewsSearchResponse(BaseModel):
    """Response from search_news tool."""
    query: str
    articles: list[NewsArticle]
    date_range: str

class ImageResult(BaseModel):
    """Image search result."""
    title: str
    url: str
    thumbnail_url: str
    source: str

class SocialMention(BaseModel):
    """Social media mention."""
    platform: str
    author: str
    content: str
    date: datetime
    engagement: int
    sentiment: Literal["positive", "neutral", "negative"]
```
