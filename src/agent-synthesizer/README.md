# agent-synthesizer

Foundry Native agent for research synthesis and recommendations.

## Overview

This agent synthesizes findings from all research agents into a cohesive expansion recommendation. It reads all gathered research, identifies patterns, assesses overall viability, and generates a final report with actionable recommendations.

## Setup

```powershell
cd src/agent-synthesizer
uv sync

# Copy environment file and configure
cp .env.example .env
# Edit .env with your Azure AI Foundry credentials
```

## Usage

### Provision Agent

Create the agent in AI Foundry (idempotent - recreates if exists):

```powershell
uv run python -m synthesizer.provision create
```

List agents:

```powershell
uv run python -m synthesizer.provision list
```

Destroy agent:

```powershell
uv run python -m synthesizer.provision destroy
```

## Project Structure

```
agent-synthesizer/
├── synthesizer/
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
