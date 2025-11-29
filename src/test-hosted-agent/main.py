# Copyright (c) Microsoft. All rights reserved.
"""
Minimal test agent for Azure AI Foundry Hosted Agents.
Based on official SDK samples.

This uses AzureChatOpenAI with explicit token provider for managed identity auth.
"""

import os
import logging

from dotenv import load_dotenv
from importlib.metadata import version
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from azure.ai.agentserver.langgraph import from_langgraph
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

logger = logging.getLogger(__name__)
load_dotenv()

memory = MemorySaver()
deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4o")

# Use managed identity for authentication
credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    credential, "https://cognitiveservices.azure.com/.default"
)

model = AzureChatOpenAI(
    model=deployment_name,
    azure_ad_token_provider=token_provider,
)


@tool
def get_word_length(word: str) -> int:
    """Returns the length of a word."""
    return len(word)


@tool
def calculator(expression: str) -> str:
    """Evaluates mathematical expression"""
    try:
        maths_result = eval(expression)
        return str(maths_result)
    except Exception as e:
        return f"Error: {str(e)}"


def create_agent(model, tools, checkpointer):
    # for different langgraph versions
    langgraph_version = version("langgraph")
    if langgraph_version < "1.0.0":
        from langgraph.prebuilt import create_react_agent

        return create_react_agent(model, tools, checkpointer=checkpointer)
    else:
        from langchain.agents import create_agent

        return create_agent(model, tools, checkpointer=checkpointer)


tools = [get_word_length, calculator]

agent_executor = create_agent(model, tools, memory)

if __name__ == "__main__":
    # host the langgraph agent
    from_langgraph(agent_executor).run()
