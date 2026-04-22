# Service Security: agent-location-scout

Security controls for the LangGraph Hosted Agent.

## Threat Model Snapshot

| Asset | Threat | Mitigation |
|-------|--------|------------|
| Container image | Supply chain attack | Image scanning, signed images |
| Agent credentials | Credential theft | Managed Identity, no secrets in image |
| LLM prompts | Prompt injection | Input validation, prompt templates |
| MCP communication | Data interception | Internal VNet, no public exposure |

## Controls Checklist

### Authentication/Authorization
- [ ] Agent Identity: Foundry-managed agent identity
- [ ] MCP access: Internal network only
- [ ] LLM access: Managed Identity to Azure OpenAI

### Secrets Handling
| Secret | Storage | Rotation |
|--------|---------|----------|
| Azure OpenAI credentials | Agent Identity | N/A (automatic) |
| MCP server URLs | Environment variables | N/A (not secrets) |

### Data Classification
| Data Type | Classification | Handling |
|-----------|----------------|----------|
| Location data | Demo/Synthetic | No retention |
| Regulation data | Demo/Synthetic | No retention |
| Agent responses | Transient | Foundry-managed |

### Encryption
- **In transit**: TLS 1.2+ for all connections
- **At rest**: Foundry-managed

### Identity

```yaml
# Agent Identity (Foundry-managed)
identity:
  type: AgentIdentity
  permissions:
    - Azure OpenAI: Cognitive Services OpenAI User
    - MCP servers: Internal network access
```

## Testing & Monitoring

### Security Scans
| Scan | Tool | Frequency |
|------|------|-----------|
| Container vulnerabilities | Trivy | Every build |
| Dependency vulnerabilities | pip-audit | Every build |
| Secret detection | gitleaks | Every commit |

### Security Alerts
| Alert | Condition | Severity |
|-------|-----------|----------|
| Agent failure rate | >20% errors | Medium |
| Unusual invocation pattern | >5x baseline | Low |

## Exceptions

| Exception | Owner | Expiration | Follow-up |
|-----------|-------|------------|-----------|
| Preview region (North Central US) | Platform Team | GA release | Move to West Europe |
