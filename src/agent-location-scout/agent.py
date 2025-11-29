"""LangGraph agent definition for Location Scout.

This module defines the LangGraph StateGraph for location analysis.
Currently a simple ReAct-style agent without tools - tools will be added later.

When running as a hosted agent in Azure AI Foundry, authentication is handled
via Azure Managed Identity with explicit token provider for cognitive services.
"""

import logging
import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, MessagesState, StateGraph

logger = logging.getLogger(__name__)


def create_llm():
    """Create the Azure OpenAI chat model with managed identity authentication.
    
    Uses init_chat_model with explicit azure_ad_token_provider for proper
    managed identity authentication. This pattern matches the official 
    azure-ai-agentserver-langgraph samples.
    
    Environment variables required:
    - AZURE_OPENAI_ENDPOINT: The Azure OpenAI service endpoint 
      (format: https://<name>.cognitiveservices.azure.com/)
    - AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: The model deployment name
    
    Returns:
        Configured LangChain chat model instance.
    """
    # Get configuration from environment
    deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4o")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    
    logger.info(f"Creating LLM with deployment: {deployment_name}")
    logger.info(f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT', 'not set')}")
    logger.info(f"Using API key: {'yes' if api_key else 'no (managed identity)'}")
    
    # Pattern from official SDK samples:
    # sdk/agentserver/azure-ai-agentserver-langgraph/samples/agent_calculator/
    if api_key:
        # API key authentication (local development)
        return init_chat_model(
            f"azure_openai:{deployment_name}",
            temperature=0.7,
        )
    else:
        # Managed identity authentication (hosted agent)
        # The scope "https://cognitiveservices.azure.com/.default" is required
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        return init_chat_model(
            f"azure_openai:{deployment_name}",
            azure_ad_token_provider=token_provider,
            temperature=0.7,
        )


def get_system_prompt() -> str:
    """Load the system prompt from template.
    
    Returns:
        The system prompt string.
    """
    from pathlib import Path
    prompt_path = Path(__file__).parent / "prompts" / "system_prompt.jinja2"
    if not prompt_path.exists():
        return "You are a helpful location scout assistant."
    return prompt_path.read_text(encoding="utf-8")


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
