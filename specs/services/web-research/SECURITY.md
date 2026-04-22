# Service Security Notes: web-research

## Threat Model Snapshot

| Asset | Threat | Mitigation |
| --- | --- | --- |
| **User Input** | XSS (Cross-Site Scripting) via research query or answers | React automatically escapes content. Markdown renderer (e.g., `react-markdown`) must use a sanitizer plugin (e.g., `rehype-sanitize`). |
| **Draft Content** | Malicious Markdown injection from LLM (indirect XSS) | Same as above; sanitize all Markdown rendering. |
| **API Access** | CSRF / Unauthorized access | For demo: Open access or basic shared token. Prod: OAuth2/OIDC via MSAL. |

## Controls Checklist

- [ ] **Content Security Policy (CSP)**: Configured in Nginx to allow connections only to known API endpoints.
- [ ] **Input Sanitization**: All user inputs trimmed and validated.
- **HTTPS**: Enforced by Azure Container Apps Ingress.

## Testing & Monitoring
- **Dependency Scan**: `npm audit` in CI pipeline.
- **Static Analysis**: ESLint security plugins.
