# MCP Scratchpad Server

A Model Context Protocol (MCP) server for managing shared scratchpad state in multi-agent workflows. Enables agents to:

- Store and share findings across sections (market analysis, competitor insights, etc.)
- Track task progress via checklists
- Queue questions for human-in-the-loop (HITL) approval

## Features

- **FastMCP Framework**: Built on FastMCP 2.0+ for MCP protocol compliance
- **HTTP Transport**: RESTful API with HTTP transport
- **Token Authentication**: StaticTokenVerifier for API key authentication
- **In-Memory Storage**: Fast, session-based storage (ready for swap to Cosmos DB/Redis)
- **Health Checks**: Built-in `/health` endpoint for container orchestration

## Quick Start

### Local Development

```bash
# Install dependencies
cd src/mcp-scratchpad
uv sync

# Set authentication token
export MCP_AUTH_TOKEN="your-secure-token"

# Run the server
uv run python -m mcp_scratchpad.main
```

The server starts on `http://localhost:8080`.

### Docker

```bash
# Build the image
docker build -t mcp-scratchpad .

# Run the container
docker run -p 8080:8080 \
  -e MCP_AUTH_TOKEN="your-secure-token" \
  mcp-scratchpad
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `0.0.0.0` | Server bind address |
| `MCP_PORT` | `8080` | Server port |
| `MCP_AUTH_TOKEN` | (required) | Authentication token |
| `MCP_LOG_LEVEL` | `INFO` | Logging level |
| `MCP_DEBUG` | `false` | Enable debug mode |

## MCP Tools

### Section Management

| Tool | Description |
|------|-------------|
| `read_section` | Read content from a named section |
| `write_section` | Write/replace content in a section |
| `append_to_section` | Append content to existing section |
| `list_sections` | List all sections in a session |

### Checklist Management

| Tool | Description |
|------|-------------|
| `update_checklist` | Update or add checklist items |
| `get_checklist` | Get all checklist items |

### Question Queue (HITL)

| Tool | Description |
|------|-------------|
| `add_question` | Add a question for human review |
| `get_pending_questions` | Get unanswered questions |
| `get_answered_questions` | Get answered questions |
| `submit_answers` | Submit answers to questions |

### Session Management

| Tool | Description |
|------|-------------|
| `delete_session` | Delete a session and all its data |

## Project Structure

```
mcp_scratchpad/
├── __init__.py      # Package exports
├── main.py          # Entry point
├── server.py        # FastMCP server and tools
├── models.py        # Pydantic data models
├── config.py        # Configuration settings
└── storage.py       # Storage abstraction layer
```

## Deployment

### GitHub Actions

The repository includes a GitHub Actions workflow (`.github/workflows/mcp-scratchpad.yml`) that:

1. Runs linting and tests on PRs
2. Builds and pushes Docker image to GitHub Container Registry on merge to main
3. Tags images with `latest` and commit SHA

### Azure Container Apps

See `deploy/azure/terraform/` for Terraform configuration to deploy to Azure Container Apps.

```bash
cd deploy/azure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars
terraform init
terraform apply
```

## Development

### Running Tests

```bash
uv run pytest tests/ -v
```

### Code Formatting

```bash
uv run ruff format mcp_scratchpad/
uv run ruff check mcp_scratchpad/
```

## Storage Abstraction

The storage layer uses a protocol-based design for easy swapping:

```python
class ScratchpadStorage(Protocol):
    async def get_session(self, session_id: str) -> ScratchpadSession | None: ...
    async def create_session(self, session_id: str) -> ScratchpadSession: ...
    async def update_session(self, session: ScratchpadSession) -> None: ...
    async def delete_session(self, session_id: str) -> bool: ...
    async def list_sessions(self) -> list[str]: ...
```

To swap storage backend, implement this protocol (e.g., `CosmosDBStorage`, `RedisStorage`) and inject it into the server.

## License

See repository LICENSE file.
