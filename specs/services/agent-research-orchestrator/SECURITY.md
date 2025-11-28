# Service Security: agent-research-orchestrator

Security controls and threat model for the research orchestrator.

## Threat Model Snapshot

| Asset | Threat | Mitigation |
|-------|--------|------------|
| REST API | Unauthorized access | Demo: Open access (no auth for demo). Production: Azure AD B2C |
| Agent credentials | Credential theft | Managed Identity, no secrets in code |
| LLM prompts | Prompt injection | Input validation, prompt templates |
| SSE stream | Information disclosure | Session-scoped events only |
| A2A communication | Man-in-the-middle | HTTPS, managed identity tokens |

## Controls Checklist

### Authentication/Authorization
- [ ] **Demo mode**: No authentication (open access for conference demo)
- [ ] **Production mode**: Azure AD B2C integration (future)
- [ ] API rate limiting: 100 requests/minute per IP
- [ ] Session isolation: Each research session is independent

### Secrets Handling
| Secret | Storage | Rotation |
|--------|---------|----------|
| Azure OpenAI API Key | Key Vault | 90 days |
| Foundry connection string | Key Vault | 90 days |
| A2A client credentials | Managed Identity | N/A (automatic) |

### Data Classification
| Data Type | Classification | Handling |
|-----------|----------------|----------|
| Research queries | Demo/Synthetic | No retention |
| Agent responses | Demo/Synthetic | 7-day log retention |
| Session state | Transient | In-memory only |

### Encryption
- **In transit**: TLS 1.2+ for all connections
- **At rest**: N/A (no persistent storage in this service)

### Identity
```yaml
# Managed Identity permissions
identity:
  type: SystemAssigned
  permissions:
    - Azure AI Foundry: Cognitive Services User
    - Azure OpenAI: Cognitive Services OpenAI User
    - Key Vault: Key Vault Secrets User
    - Container Registry: AcrPull
```

## Testing & Monitoring

### Security Scans
| Scan | Tool | Frequency |
|------|------|-----------|
| Dependency vulnerabilities | pip-audit | Every build |
| Container vulnerabilities | Trivy | Every build |
| Secret detection | gitleaks | Every commit |
| SAST | Bandit | Every build |

### Security Alerts
| Alert | Condition | Severity |
|-------|-----------|----------|
| High error rate | >10% 4xx/5xx | Medium |
| Unusual traffic pattern | >3x baseline | Low |
| Failed auth attempts | >50/hour | Medium |

### Security Logs
- All API requests logged with timestamp, IP, path
- Agent invocations logged with session context
- No PII in logs (demo data only)

## Exceptions

| Exception | Owner | Expiration | Follow-up |
|-----------|-------|------------|-----------|
| No authentication (demo) | Platform Team | 2025-12-31 | Implement Azure AD B2C for production |
| Open CORS policy | Platform Team | 2025-12-31 | Restrict to specific origins |

## Compliance Notes

- **GDPR**: Not applicable (no real PII, demo data only)
- **SOC2**: Not in scope for demo
- **Data residency**: All processing in West Europe
