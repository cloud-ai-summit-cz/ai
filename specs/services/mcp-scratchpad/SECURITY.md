# Service Security: mcp-scratchpad

## Session Isolation (Security Critical)

### Threat: Cross-Session Data Access

An AI agent could potentially access another session's data if session isolation is not enforced at the infrastructure level.

| Threat | Risk | Mitigation |
|--------|------|------------|
| Agent passes wrong session_id | High | **Session ID is NOT a tool parameter** - injected via HTTP header by orchestrator |
| Agent crafts malicious request | Medium | Session ID header validated on every request |
| Session ID guessing | Low | Use UUIDs, short-lived sessions (24h TTL) |

### Session ID Enforcement

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           TRUST BOUNDARY                                      │
│                                                                               │
│  ┌─────────────────┐         ┌─────────────────────────┐                     │
│  │   AI Agent      │         │   Orchestrator          │                     │
│  │                 │         │   (Trusted Code)        │                     │
│  │ ❌ Cannot set   │         │   ✅ Controls session   │                     │
│  │    session_id   │         │      ID injection       │                     │
│  └────────┬────────┘         └───────────┬─────────────┘                     │
│           │ MCP call                     │ HTTP header                        │
│           │ (no session_id)              │ X-Session-ID: sess_xxx            │
│           └───────────────┬──────────────┘                                   │
│                           │                                                   │
└───────────────────────────┼──────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │   mcp-scratchpad    │
                  │                     │
                  │  Validates:         │
                  │  • Header present   │
                  │  • Session exists   │
                  │  • Session valid    │
                  └─────────────────────┘
```

### Validation Checklist

Every request to mcp-scratchpad MUST:

- [ ] Have `X-Session-ID` header present
- [ ] Have valid session ID format (UUID)
- [ ] Reference an existing, non-expired session
- [ ] Be logged with session ID for audit

### Error Responses

| Scenario | HTTP Status | Response |
|----------|-------------|----------|
| Missing X-Session-ID header | 400 | `{"error": "MISSING_SESSION_ID", "message": "X-Session-ID header required"}` |
| Invalid session ID format | 400 | `{"error": "INVALID_SESSION_ID", "message": "Session ID must be valid UUID"}` |
| Session not found | 404 | `{"error": "SESSION_NOT_FOUND", "message": "Session does not exist"}` |
| Session expired | 410 | `{"error": "SESSION_EXPIRED", "message": "Session has expired"}` |

## Authentication

- Internal Container Apps ingress only (no public access)
- API key authentication between services
- Managed identity for Cosmos DB access (future)

## Authorization

| Caller | Allowed Operations |
|--------|-------------------|
| Orchestrator | `create_session`, all read/write tools |
| Subagent (via scoped wrapper) | Read/write within assigned session only |
| Frontend (via API proxy) | Read-only within session |

## Data Protection

- Session data TTL enforced (24h)
- No PII stored (mock data only)
- Session data isolated by session_id key

## Audit Logging

All operations logged with:
- `session_id` - Which session
- `caller_agent` - Which agent (from X-Caller-Agent header)
- `operation` - What was done (add_note, write_draft_section, etc.)
- `timestamp` - When

```json
{
  "level": "INFO",
  "session_id": "sess_abc123",
  "caller_agent": "market-analyst",
  "operation": "add_note",
  "content_preview": "Market size is €500M...",
  "timestamp": "2025-12-01T10:05:00Z"
}
```

## Specification by Example

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Missing session header | Request without X-Session-ID | MCP tool called | 400 error returned |
| Unknown session | X-Session-ID = "unknown-id" | MCP tool called | 404 error returned |
| Expired session | Session created 25 hours ago | MCP tool called | 410 error returned |
| Valid session | Valid X-Session-ID header | MCP tool called | Operation succeeds |
| Cross-session attempt | Agent tries to read session B while in session A | - | Impossible (header controlled by wrapper) |