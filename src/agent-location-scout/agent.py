"""LangGraph agent definition for Location Scout.

This module defines the LangGraph StateGraph for location analysis.
Currently a simple ReAct-style agent without tools - tools will be added later.

When running as a hosted agent in Azure AI Foundry, authentication is handled
via the AIProjectClient which uses the project's managed identity/agent identity.
The agent uses models deployed to the Foundry project rather than external OpenAI endpoints.
"""

import logging

from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from config import get_settings

logger = logging.getLogger(__name__)


def create_llm() -> AzureChatOpenAI:
    """Create the Azure OpenAI chat model.
    
    Uses AIProjectClient to get an authenticated OpenAI client. This uses
    the Foundry project's identity and accesses models deployed to the project
    (visible in the "Models + endpoints" tab in Foundry portal).
    
    Returns:
        Configured AzureChatOpenAI instance using project-based authentication.
    """
    settings = get_settings()
    
    logger.info(f"Creating LLM with project endpoint: {settings.azure_ai_foundry_endpoint}")
    logger.info(f"Model deployment: {settings.effective_model_deployment}")
    
    # Use AIProjectClient to get an authenticated OpenAI client
    # This leverages the Foundry project's identity when running as a hosted agent
    project_client = AIProjectClient(
        endpoint=settings.azure_ai_foundry_endpoint,
        credential=DefaultAzureCredential()
    )
    
    # Get the OpenAI client from the project
    # The project_client.get_openai_client() returns a properly authenticated client
    # that can access models deployed to the project
    openai_client = project_client.get_openai_client(api_version="2024-10-21")
    
    # The endpoint from the OpenAI client is the project's AI services endpoint
    # We need to extract this for LangChain
    base_url = str(openai_client.base_url).rstrip("/")
    logger.info(f"OpenAI client base URL: {base_url}")
    
    # LangChain's AzureChatOpenAI doesn't directly accept an OpenAI client,
    # so we need to configure it with the endpoint and authentication.
    # The project client uses managed identity, which we can replicate.
    from azure.identity import get_bearer_token_provider
    
    # Use cognitiveservices scope for AI Services/OpenAI
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )
    
    # Extract just the base endpoint (without /openai/...)
    # The base_url is typically something like:
    # https://<account>.services.ai.azure.com/api/projects/<project>/openai/deployments
    # We need just: https://<account>.services.ai.azure.com/api/projects/<project>
    endpoint = settings.azure_ai_foundry_endpoint
    
    return AzureChatOpenAI(
        azure_deployment=settings.effective_model_deployment,
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
