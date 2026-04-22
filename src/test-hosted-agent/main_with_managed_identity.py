# Copyright (c) Microsoft. All rights reserved.
"""
Test agent for Azure AI Foundry with managed identity authentication.
Based on official SDK agent_calculator sample.

This sample shows explicit DefaultAzureCredential + token provider pattern.
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import (
    END,
    START,
    MessagesState,
    StateGraph,
)
from typing_extensions import Literal
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from azure.ai.agentserver.langgraph import from_langgraph

load_dotenv()

deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4o")
api_key = os.getenv("AZURE_OPENAI_API_KEY", "")

if api_key:
    # API key-based auth
    llm = init_chat_model(f"azure_openai:{deployment_name}")
else:
    # Managed identity auth (used in hosted agent)
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    llm = init_chat_model(
        f"azure_openai:{deployment_name}",
        azure_ad_token_provider=token_provider,
    )


# ---- Tools ----
@tool
def add(a: int, b: int) -> int:
    """Adds a and b."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiplies a and b."""
    return a * b


@tool
def divide(a: int, b: int) -> float:
    """Divide a and b."""
    return a / b


tools = [add, multiply, divide]
llm_with_tools = llm.bind_tools(tools)
tools_by_name = {tool.name: tool for tool in tools}


def llm_call(state: MessagesState):
    """LLM decides whether to call a tool or not"""
    return {
        "messages": [
            llm_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                    )
                ]
                + state["messages"]
            )
        ]
    }


def tool_node(state: dict):
    """Performs the tool call"""
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
    return {"messages": result}


def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Determine if we should continue to tool_node or end."""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tool_node"
    return END


# ---- Build the graph ----
workflow = StateGraph(MessagesState)
workflow.add_node("llm_call", llm_call)
workflow.add_node("tool_node", tool_node)

workflow.add_edge(START, "llm_call")
workflow.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
workflow.add_edge("tool_node", "llm_call")

agent = workflow.compile()

if __name__ == "__main__":
    from_langgraph(agent).run()
