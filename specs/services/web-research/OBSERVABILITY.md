# Service Observability Plan: web-research

## Metrics

| Metric | Purpose | Target | Source |
| --- | --- | --- | --- |
| **Page Load Time** | UX Performance | < 1.5s (p95) | Browser Performance API / App Insights |
| **SSE Connection Stability** | Reliability | < 1 disconnect/hour | Custom Event Tracking |
| **API Latency** | Backend Health | < 500ms | App Insights (AJAX dependencies) |

## Logs
- **Development**: Console logging (Info/Error).
- **Production**: 
  - **Application Insights**: React Error Boundary captures unhandled exceptions.
  - **Nginx Access Logs**: Standard stdout/stderr logs captured by Container Apps.

## Alerts
| Alert | Condition | Severity | Channel |
| --- | --- | --- | --- |
| **High Error Rate** | > 5% JS errors in 5m | Warning | Dashboard |
| **Backend Unreachable** | API Health Check fails | Critical | PagerDuty |

## Specification by Example
- **Scenario**: Backend restart causes SSE drop.
  - **Telemetry**: `SSE_DISCONNECT` event logged. `SSE_RECONNECT_ATTEMPT` logged.
  - **Success**: `SSE_CONNECTED` logged within 5 seconds.
