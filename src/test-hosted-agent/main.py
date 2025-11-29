# Copyright (c) Microsoft. All rights reserved.
"""
Minimal test agent for Azure AI Foundry Hosted Agents.
Based on official SDK calculator-agent sample.

This uses the official pattern with init_chat_model and token provider.
"""

import os
import logging

from dotenv import load_dotenv
from importlib.metadata import version
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from azure.ai.agentserver.langgraph import from_langgraph
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

logger = logging.getLogger(__name__)
load_dotenv()

memory = MemorySaver()
deployment_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")

try:
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    model = init_chat_model(
        f"azure_openai:{deployment_name}",
        azure_ad_token_provider=token_provider,
    )
except Exception:
    logger.exception("Failed to initialize chat model")
    raise


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
