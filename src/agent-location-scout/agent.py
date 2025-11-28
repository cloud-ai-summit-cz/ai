"""LangGraph agent definition for Location Scout.

This module defines the LangGraph StateGraph for location analysis.
Currently a simple ReAct-style agent without tools - tools will be added later.
"""

import os
import logging

from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from config import get_settings

logger = logging.getLogger(__name__)


def create_llm() -> AzureChatOpenAI:
    """Create the Azure OpenAI chat model.
    
    Returns:
        Configured AzureChatOpenAI instance.
    """
    settings = get_settings()
    
    # Use Azure AD token provider for authentication
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    
    # Determine endpoint - prefer explicit setting, fall back to Foundry endpoint
    endpoint = settings.azure_openai_endpoint or settings.azure_ai_foundry_endpoint
    
    return AzureChatOpenAI(
        azure_deployment=settings.azure_ai_model_deployment_name,
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2024-10-21",
        temperature=0.7,
    )


def get_system_prompt() -> str:
    """Load the system prompt from template.
    
    Returns:
        The system prompt string.
    """
    settings = get_settings()
    return settings.get_prompt("system_prompt")


def build_agent() -> StateGraph:
    """Build the LangGraph agent.
    
    Creates a simple conversational agent that responds to location
    analysis queries. Tools will be added in future iterations.
    
    Returns:
        Compiled LangGraph StateGraph.
    """
    llm = create_llm()
    system_prompt = get_system_prompt()
    
    def call_model(state: MessagesState) -> dict:
        """Invoke the LLM with the current message state."""
        messages = state["messages"]
        
        # Prepend system message if not already present
        if not messages or messages[0].type != "system":
            from langchain_core.messages import SystemMessage
            messages = [SystemMessage(content=system_prompt)] + list(messages)
        
        response = llm.invoke(messages)
        return {"messages": [response]}
    
    # Build the graph
    builder = StateGraph(MessagesState)
    
    # Add the single node (no tools yet)
    builder.add_node("agent", call_model)
    
    # Connect edges
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)
    
    return builder.compile()
