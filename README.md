# Cloud and AI summit 2025 Czech - AI demo

## Cofilot AI Invoice processing workflow
TBD

## Cofilot AI Research Platform

> Multi-agent research orchestration demo using Microsoft Agent Framework on Azure

See more details in [COFILOT_AI_RESEARCH.md](./COFILOT_AI_RESEARCH.md)

This project demonstrates a **collaborative AI research workflow** where multiple specialized agents work together to investigate business expansion opportunities for a specialty coffee company.

- Every agent and MCP server runs **separatly deployable and scalable microservices** in Azure Container Apps
- **A2A** is use between agents, **MCP** is used to access tools (mocked information for our demo - use questions around Brno or Vienna preferably)
- All A2A, MCP and API are **governed in Azure API Management** and visible in Foundry as registered assets
- **Agent as tool** pattern, **reasoning** model GPT 5
- Scratchpad strategy for **agentic shared memories** - plans, notes, draft, questions
- Implementation of **Human-in-the-loop** with clarifying questions of various priority

![](./images/cofilot_ai_research.png)