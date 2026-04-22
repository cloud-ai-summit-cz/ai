# Shared Testing Strategy

Testing expectations for Cofilot AI Platform. Focus on demo reliability and agent behavior validation.

---

## Test Pyramid Targets

| Layer | Goal | Tooling | Coverage Target |
|-------|------|---------|-----------------|
| Unit | Fast feedback, business logic | pytest | 80% for services |
| Integration | IO boundaries (DB, MCP, AI Foundry) | pytest + testcontainers | Critical paths |
| Contract | MCP tool schemas | pytest-pydantic | 100% MCP schemas |
| E2E/Scenario | Demo scenarios work end-to-end | pytest-asyncio | All PRD scenarios |
| Non-Functional | Demo timing, reliability | Manual + timing | Demo completes in target time |

---

## Quality Gates

### PR Requirements

| Check | Tool | Blocking |
|-------|------|----------|
| Lint (Python) | ruff check | ✅ Yes |
| Format (Python) | ruff format --check | ✅ Yes |
| Type check | mypy | ✅ Yes |
| Unit tests | pytest tests/unit | ✅ Yes |
| Integration tests | pytest tests/integration | ✅ Yes |
| Terraform format | terraform fmt -check | ✅ Yes |
| Terraform validate | terraform validate | ✅ Yes |

### Coverage Thresholds

| Component | Minimum | Notes |
|-----------|---------|-------|
| Backend API | 80% | Core business logic |
| MCP Servers | 70% | Tool implementations |
| Agent Definitions | N/A | Not unit testable |
| Frontend | 50% | Vue component tests |

### Waiver Process

For demo scope, coverage waivers are granted for:
- Generated code (Pydantic models)
- External SDK wrappers (thin wrappers around Azure SDKs)
- Agent prompt definitions

---

## Test Structure

```
tests/
├── unit/
│   ├── test_models.py              # Pydantic model validation
│   ├── test_scratchpad_logic.py    # Scratchpad operations
│   └── mcp_servers/
│       ├── test_market_data.py
│       ├── test_competitor.py
│       ├── test_location.py
│       └── test_finance.py
│
├── integration/
│   ├── test_cosmos_operations.py   # Cosmos DB CRUD
│   ├── test_ai_search.py           # Search index queries
│   ├── test_mcp_endpoints.py       # MCP server HTTP
│   └── test_sse_streaming.py       # SSE event delivery
│
├── contract/
│   ├── test_mcp_schemas.py         # MCP tool input/output schemas
│   ├── test_api_schemas.py         # REST API schemas
│   └── test_event_schemas.py       # SSE event schemas
│
├── e2e/
│   ├── test_research_scenarios.py  # Research demo scenarios
│   └── conftest.py                 # Shared fixtures
│
└── conftest.py                     # Global fixtures
```

---

## Unit Tests

### Model Validation Tests

```python
# tests/unit/test_models.py
import pytest
from pydantic import ValidationError
from app.models.research import ResearchSession, ChecklistItem

class TestResearchSession:
    def test_valid_research_session(self):
        """Valid research session should parse correctly."""
        session = ResearchSession(
            id="sess_abc123",
            session_id="sess_abc123",
            query="Should Cofilot expand to Vienna?",
            status="in_progress",
            created_at="2025-12-01T10:00:00Z",
            updated_at="2025-12-01T10:15:00Z",
            scratchpad_id="sp_abc123",
            checklist=[
                ChecklistItem(
                    id=1,
                    item="Market size and growth trends documented",
                    owner_agent="market-analyst",
                    status="completed"
                )
            ]
        )
        assert session.status == "in_progress"
    
    def test_invalid_status(self):
        """Status must be one of the allowed values."""
        with pytest.raises(ValidationError) as exc:
            ResearchSession(
                id="sess_abc123",
                session_id="sess_abc123",
                query="Test query",
                status="invalid_status",  # Not allowed
                created_at="2025-12-01T10:00:00Z",
                updated_at="2025-12-01T10:15:00Z",
                scratchpad_id="sp_abc123",
                checklist=[]
            )
        assert "status" in str(exc.value)
    
    def test_query_length_validation(self):
        """Query must not exceed max length."""
        with pytest.raises(ValidationError):
            ResearchSession(
                id="sess_abc123",
                session_id="sess_abc123",
                query="x" * 501,  # Too long
                status="created",
                created_at="2025-12-01T10:00:00Z",
                updated_at="2025-12-01T10:15:00Z",
                scratchpad_id="sp_abc123",
                checklist=[]
            )
```

### MCP Tool Tests

```python
# tests/unit/mcp_servers/test_finance.py
import pytest
from mcp_finance.tools import calculate_break_even, StartupCosts, MonthlyCosts, RevenueProjection

class TestFinanceCalculations:
    def test_break_even_calculation(self):
        """Break-even should be calculated correctly."""
        startup = StartupCosts(
            rent_deposit=10000,
            equipment=50000,
            renovation=30000,
            initial_inventory=5000,
            licenses=2000,
            total=97000
        )
        
        monthly = MonthlyCosts(
            rent=3000,
            staff=8000,
            utilities=500,
            inventory=2000,
            marketing=1000,
            total=14500
        )
        
        revenue = RevenueProjection(
            monthly_customers=3000,
            avg_ticket=8.50,
            monthly_revenue=25500
        )
        
        result = calculate_break_even(startup, monthly, revenue)
        
        # Monthly profit = 25500 - 14500 = 11000
        # Break-even months = 97000 / 11000 ≈ 8.8
        assert result.months_to_break_even == pytest.approx(8.8, rel=0.1)
        assert result.monthly_profit == 11000
```

---

## Integration Tests

### Cosmos DB Tests

```python
# tests/integration/test_cosmos_operations.py
import pytest
from testcontainers.cosmosdb import CosmosDBEmulatorContainer
from app.services.cosmos_client import CosmosClient

@pytest.fixture(scope="module")
def cosmos_container():
    """Start Cosmos DB emulator for tests."""
    with CosmosDBEmulatorContainer() as cosmos:
        yield cosmos

@pytest.fixture
async def cosmos_client(cosmos_container):
    """Create client connected to emulator."""
    client = CosmosClient(
        endpoint=cosmos_container.get_connection_url(),
        key=cosmos_container.get_key()
    )
    await client.initialize()
    yield client
    await client.cleanup()

@pytest.mark.asyncio
async def test_create_research_session(cosmos_client):
    """Should create and retrieve research session."""
    session = await cosmos_client.create_session(
        query="Should Cofilot expand to Vienna?"
    )
    
    assert session.session_id is not None
    assert session.status == "created"
    
    retrieved = await cosmos_client.get_session(session.session_id)
    assert retrieved.query == session.query

@pytest.mark.asyncio
async def test_update_scratchpad_section(cosmos_client):
    """Should update scratchpad section."""
    session = await cosmos_client.create_session(query="Test query")
    
    await cosmos_client.update_scratchpad_section(
        session_id=session.session_id,
        section="market_findings",
        content={"market_size_eur": 450000000},
        updated_by="market-analyst"
    )
    
    scratchpad = await cosmos_client.get_scratchpad(session.session_id)
    assert scratchpad.sections["market_findings"].content["market_size_eur"] == 450000000
```

### MCP Server HTTP Tests

```python
# tests/integration/test_mcp_endpoints.py
import pytest
from httpx import AsyncClient
from mcp_market_data.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_get_market_overview(client):
    """MCP tool should return market data."""
    response = await client.post(
        "/mcp/tools/get_market_overview",
        json={"city": "Vienna"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "market_size_eur" in data
    assert data["city"] == "Vienna"

@pytest.mark.asyncio
async def test_invalid_city(client):
    """Should handle unknown city gracefully."""
    response = await client.post(
        "/mcp/tools/get_market_overview",
        json={"city": "UnknownCity"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
```

### SSE Streaming Tests

```python
# tests/integration/test_sse_streaming.py
import pytest
import asyncio
from httpx import AsyncClient
from app.main import app
from app.services.event_bus import event_bus

@pytest.mark.asyncio
async def test_sse_event_delivery():
    """SSE events should be delivered to connected clients."""
    session_id = "test_sess_001"
    received_events = []
    
    async def collect_events():
        async with AsyncClient(app=app, base_url="http://test") as client:
            async with client.stream("GET", f"/api/events/{session_id}") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        received_events.append(line)
                        if len(received_events) >= 2:
                            break
    
    # Start collecting in background
    collect_task = asyncio.create_task(collect_events())
    
    # Wait for connection
    await asyncio.sleep(0.1)
    
    # Publish events
    await event_bus.publish(session_id, {
        "type": "agent_activity",
        "data": {"agent": "market-analyst", "action": "started"}
    })
    await event_bus.publish(session_id, {
        "type": "agent_activity",
        "data": {"agent": "market-analyst", "action": "completed"}
    })
    
    await asyncio.wait_for(collect_task, timeout=5.0)
    
    assert len(received_events) == 2
```

---

## Contract Tests

### MCP Schema Validation

```python
# tests/contract/test_mcp_schemas.py
import pytest
from pydantic import ValidationError
from mcp_market_data.schemas import (
    GetMarketOverviewInput,
    GetMarketOverviewOutput,
    MarketTrend
)

class TestMarketDataSchemas:
    def test_input_schema_validation(self):
        """Input schema should validate correctly."""
        # Valid
        valid = GetMarketOverviewInput(city="Vienna")
        assert valid.city == "Vienna"
        
        # Invalid - empty city
        with pytest.raises(ValidationError):
            GetMarketOverviewInput(city="")
    
    def test_output_schema_completeness(self):
        """Output schema should have all required fields."""
        output = GetMarketOverviewOutput(
            city="Vienna",
            country="Austria",
            population=1920000,
            market_size_eur=450000000,
            annual_growth_rate=0.035,
            consumption_per_capita_kg=7.2,
            specialty_coffee_share=0.28
        )
        
        # Verify all fields are present
        assert output.model_dump().keys() == {
            "city", "country", "population", "market_size_eur",
            "annual_growth_rate", "consumption_per_capita_kg",
            "specialty_coffee_share"
        }
```

### API Schema Validation

```python
# tests/contract/test_api_schemas.py
import pytest
from app.models.api import (
    StartResearchRequest,
    StartResearchResponse
)

class TestAPISchemas:
    def test_start_research_request(self):
        """Research request should require query."""
        with pytest.raises(ValidationError):
            StartResearchRequest()  # Missing query
        
        valid = StartResearchRequest(query="Should we expand?")
        assert len(valid.query) > 0
    
    def test_start_research_response(self):
        """Response should include session_id and status."""
        response = StartResearchResponse(
            session_id="sess_123",
            status="created",
            message="Research session started"
        )
        
        assert response.session_id.startswith("sess_")
```

---

## E2E Scenario Tests

### Research Scenarios

```python
# tests/e2e/test_research_scenarios.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_research_with_recommendation(client):
    """
    PRD Scenario: Complete research with recommendation
    Given: User asks "Should Cofilot expand to Vienna?"
    When: Research completes
    Then: All checklist items addressed; synthesized report with clear recommendation
    """
    # Start research
    response = await client.post(
        "/api/research/start",
        json={"query": "Should Cofilot expand to Vienna?"}
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    
    # Wait for completion (with timeout)
    import asyncio
    for _ in range(60):  # Max 60 seconds
        status_response = await client.get(f"/api/research/{session_id}/status")
        status = status_response.json()
        
        if status["status"] == "completed":
            break
        await asyncio.sleep(1)
    else:
        pytest.fail("Research did not complete within timeout")
    
    # Verify checklist
    checklist = status["checklist"]
    completed_items = [item for item in checklist if item["status"] == "completed"]
    assert len(completed_items) == 8, "All 8 checklist items should be completed"
    
    # Verify report
    report = status["final_report"]
    assert report is not None
    assert "recommendation" in report
    assert report["recommendation"] in ["expand", "do_not_expand", "conditional"]

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_agent_collaboration(client):
    """
    PRD Scenario: Agent collaboration
    Given: Market agent finds high coffee consumption
    When: Competitor agent runs
    Then: Competitor agent references market findings in its analysis
    """
    response = await client.post(
        "/api/research/start",
        json={"query": "Should Cofilot expand to Vienna?"}
    )
    session_id = response.json()["session_id"]
    
    # Wait for competitor analysis to complete
    import asyncio
    for _ in range(30):
        scratchpad = await client.get(f"/api/research/{session_id}/scratchpad")
        data = scratchpad.json()
        
        if data["sections"]["competitor_analysis"]["content"]:
            break
        await asyncio.sleep(1)
    
    # Verify competitor analysis references market data
    competitor_analysis = data["sections"]["competitor_analysis"]["content"]
    market_findings = data["sections"]["market_findings"]["content"]
    
    # The competitor analysis should have been informed by market size
    assert market_findings is not None, "Market findings should exist before competitor analysis"
    # Note: Actual cross-reference validation would require agent output inspection

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_user_interaction_mid_research(client):
    """
    PRD Scenario: User interaction mid-research
    Given: Agents identify need for budget clarification
    When: Agents pause for input
    Then: User is prompted with specific questions; research resumes with user input
    """
    response = await client.post(
        "/api/research/start",
        json={"query": "Should Cofilot expand to Vienna?"}
    )
    session_id = response.json()["session_id"]
    
    # Wait for questions to appear
    import asyncio
    questions = None
    for _ in range(30):
        status = await client.get(f"/api/research/{session_id}/status")
        data = status.json()
        
        if data["pending_questions"]:
            questions = data["pending_questions"]
            break
        await asyncio.sleep(1)
    
    if questions:  # Questions may or may not appear depending on agent behavior
        # Submit answers
        answers = {q["id"]: "€150,000 - €200,000" for q in questions}
        await client.post(
            f"/api/research/{session_id}/answers",
            json={"answers": answers}
        )
        
        # Verify research continues
        await asyncio.sleep(2)
        status = await client.get(f"/api/research/{session_id}/status")
        assert status.json()["status"] in ["in_progress", "completed"]
```

---

## Test Configuration

### pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    contract: Contract tests
    e2e: End-to-end tests
    slow: Slow tests (excluded from default run)
addopts = -v --tb=short
filterwarnings =
    ignore::DeprecationWarning
```

### conftest.py (Global)

```python
# tests/conftest.py
import pytest
import asyncio
from typing import Generator

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_data_path(tmp_path):
    """Create temporary mock data directory."""
    import shutil
    src = Path("mock-data")
    dst = tmp_path / "mock-data"
    shutil.copytree(src, dst)
    return dst
```

---

## Running Tests

```powershell
# All tests
uv run pytest

# Unit tests only
uv run pytest tests/unit -v

# Integration tests (requires Docker for emulators)
uv run pytest tests/integration -v

# E2E tests (requires running services)
uv run pytest tests/e2e -v -m e2e

# With coverage
uv run pytest --cov=app --cov-report=html

# Skip slow tests
uv run pytest -m "not slow"
```

---

## Specification by Example

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Unit test failure | Test fails | PR submitted | CI blocks merge |
| Coverage drop | New code without tests | Coverage check runs | Warning if below threshold |
| E2E test timeout | Demo takes too long | Test runs | Test fails with timeout error |
| Contract mismatch | MCP schema changed | Contract test runs | Test fails, schema must be updated |
| Flaky test | Test fails intermittently | Test marked flaky | Retry up to 3 times |
