# Agent Test - A2A Client

A simple test client that connects to the Market Analyst agent via the **A2A (Agent-to-Agent) protocol** using Microsoft Agent Framework.

## Purpose

This test client verifies that:
1. The Market Analyst A2A server is running and discoverable
2. The AgentCard endpoint returns valid agent metadata
3. The agent can process messages and return responses via A2A protocol

## Prerequisites

- Python 3.11+
- Market Analyst A2A server running (see `src/agent-market-analyst/standalone/a2a/maf`)

## Installation

```bash
cd src/agent-test
uv sync
```

## Running the Test

### Step 1: Start the Market Analyst A2A Server

In a separate terminal:

```bash
cd src/agent-market-analyst/standalone/a2a/maf
uv run python main.py
```

You should see:
```
Starting Market Analyst A2A Agent
  Name: Market Analyst Agent
  Host: 0.0.0.0
  Port: 8020
  Agent Card: http://0.0.0.0:8020/.well-known/agent-card.json
```

### Step 2: Run the Test Client

```bash
cd src/agent-test
uv run python test_a2a_client.py
```

Or with a custom agent URL:

```bash
A2A_AGENT_HOST=http://localhost:8020 uv run python test_a2a_client.py
```

## Expected Output

```
======================================================================
Market Analyst A2A Agent Test Client
======================================================================

Connecting to A2A agent at: http://localhost:8020

[1] Discovering agent...
    ✓ Found agent: Market Analyst Agent
    ✓ Description: Market analysis specialist for Cofilot's coffee business expansion...
    ✓ Version: 1.0.0
    ✓ Skills: 3
      - Market Size Analysis: Analyze total addressable market (TAM)...
      - Consumer Behavior Analysis: Analyze coffee consumption patterns...
      - Market Trends & Dynamics: Identify market trends, growth drivers...

[2] Creating A2A agent instance...
    ✓ A2A agent created

[3.1] Testing query...
    Query: What is the estimated market size for specialty coffee in Brno...

    Sending to agent...

    ✓ Response received!

----------------------------------------------------------------------
AGENT RESPONSE:
----------------------------------------------------------------------
[Market analysis response from the agent...]
----------------------------------------------------------------------

======================================================================
Test completed!
======================================================================
```

## How It Works

1. **Agent Discovery**: Uses `A2ACardResolver` to fetch the AgentCard from `/.well-known/agent-card.json`
2. **A2A Client Creation**: Creates an `A2AAgent` instance using the discovered card
3. **Message Exchange**: Sends queries via the A2A protocol (JSON-RPC over HTTP)
4. **Response Handling**: Receives and displays the agent's response

## A2A Protocol

The A2A (Agent-to-Agent) protocol is an open standard for agent communication:
- **Specification**: https://a2a-protocol.org/latest/specification/
- **Microsoft Implementation**: `agent-framework-a2a` package

Key A2A concepts:
- **AgentCard**: JSON metadata describing agent capabilities
- **Tasks**: Units of work with state transitions
- **Messages**: Communication turns between client and agent
