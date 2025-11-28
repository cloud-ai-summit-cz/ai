# agent-competitor-analyst

Foundry Native agent for competitive landscape analysis.

## Overview

This agent identifies and profiles competitors, analyzes competitive positioning, and identifies market gaps for expansion analysis. It is deployed as an AI Foundry managed agent.

## Setup

```powershell
cd src/agent-competitor-analyst
uv sync

# Copy environment file and configure
cp .env.example .env
# Edit .env with your Azure AI Foundry credentials
```

## Usage

### Provision Agent

Create the agent in AI Foundry (idempotent - recreates if exists):

```powershell
uv run python -m competitor_analyst.provision create
```

List agents:

```powershell
uv run python -m competitor_analyst.provision list
```

Destroy agent:

```powershell
uv run python -m competitor_analyst.provision destroy
```

## Project Structure

```
agent-competitor-analyst/
├── competitor_analyst/
│   ├── __init__.py
│   ├── config.py             # Configuration from environment
│   ├── provision.py          # CLI for agent provisioning
│   └── prompts/
│       └── system_prompt.jinja2
├── pyproject.toml
├── .env.example
└── README.md
```

## Authentication

Uses `DefaultAzureCredential` - run `az login` first or configure managed identity.
