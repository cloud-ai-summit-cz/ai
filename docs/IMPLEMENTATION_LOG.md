# Implementation Log

## 2025-12-12

- Added workflow deployment scaffolding under `deploy_workflow/azure/` (Terraform + ACR Tasks build script).
- Added workflow agent provisioning runner under `deploy_workflow/agent_provisioning/` to provision the invoice workflow agents via their `provision.py` scripts.

## 2026-04-22

- Moved `mcp-invoice-data` Logic App callback URLs out of source code into environment-backed settings and Terraform secret wiring.
- Redacted raw header logging in `mcp-invoice-data` and `mcp-scratchpad` so Authorization-bearing request metadata is no longer written to logs verbatim.
