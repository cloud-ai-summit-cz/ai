"""OpenTelemetry configuration for Research Orchestrator.

Configures Azure Monitor tracing for:
- FastAPI auto-instrumentation (requests, responses)
- HTTPX auto-instrumentation (outgoing HTTP calls)
- Agent Framework instrumentation (agent invocations, tool calls)
- Custom spans for research session correlation

See ADR-005: Real-time Agent Observability via OpenTelemetry and Application Insights
"""

import logging
import os

from opentelemetry import trace

logger = logging.getLogger(__name__)

# Flag to track if telemetry has been configured
_telemetry_configured = False


def configure_telemetry(service_name: str = "agent-research-orchestrator") -> None:
    """Configure OpenTelemetry with Azure Monitor export.

    This should be called ONCE at application startup, before any other
    modules are imported that might create spans.

    Args:
        service_name: The service name to use in traces.
    """
    global _telemetry_configured

    if _telemetry_configured:
        logger.debug("Telemetry already configured, skipping")
        return

    # Suppress noisy OpenTelemetry context warnings that occur when spans cross
    # async boundaries. These are harmless but create log noise.
    # See: https://github.com/open-telemetry/opentelemetry-python/issues/2606
    logging.getLogger("opentelemetry.context").setLevel(logging.CRITICAL)
    logging.getLogger("opentelemetry.sdk.trace").setLevel(logging.ERROR)

    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if not connection_string:
        logger.warning(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not set - tracing disabled. "
            "Set this environment variable to enable Application Insights tracing."
        )
        _telemetry_configured = True
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        # Configure Azure Monitor as the exporter
        configure_azure_monitor(
            connection_string=connection_string,
            service_name=service_name,
            enable_live_metrics=True,
        )

        # Auto-instrument FastAPI (requests/responses)
        FastAPIInstrumentor.instrument()

        # Auto-instrument HTTPX (outgoing HTTP calls to MCP servers, etc.)
        HTTPXClientInstrumentor().instrument()

        # Try to instrument Agent Framework if available
        try:
            from azure.ai.agents.telemetry import AIAgentsInstrumentor
            AIAgentsInstrumentor().instrument()
            logger.info("AIAgentsInstrumentor enabled for agent tracing")
        except ImportError:
            logger.debug("AIAgentsInstrumentor not available, skipping agent instrumentation")

        logger.info(f"Telemetry configured for {service_name} with Azure Monitor")
        _telemetry_configured = True

    except ImportError as e:
        logger.warning(f"Failed to configure telemetry - missing dependency: {e}")
        _telemetry_configured = True
    except Exception as e:
        logger.error(f"Failed to configure telemetry: {e}")
        _telemetry_configured = True


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get a tracer instance for manual span creation.

    Args:
        name: The tracer name (typically __name__ of the module).

    Returns:
        A tracer instance for creating custom spans.
    """
    return trace.get_tracer(name)


# Standard attributes for research orchestrator spans
SPAN_ATTRIBUTES = {
    "service.name": "agent-research-orchestrator",
    "service.version": "0.1.0",
}


def set_session_context(span: trace.Span, session_id: str, query: str | None = None) -> None:
    """Set session context attributes on a span.

    Args:
        span: The span to add attributes to.
        session_id: The research session ID.
        query: Optional research query.
    """
    span.set_attribute("session.id", session_id)
    if query:
        # Truncate query to avoid huge attribute values
        span.set_attribute("research.query", query[:500])


def set_agent_context(
    span: trace.Span,
    agent_name: str,
    agent_type: str = "foundry_native",
) -> None:
    """Set agent context attributes on a span.

    Args:
        span: The span to add attributes to.
        agent_name: The name of the agent being invoked.
        agent_type: The type of agent (foundry_native, foundry_hosted, a2a).
    """
    span.set_attribute("gen_ai.agent.name", agent_name)
    span.set_attribute("agent.type", agent_type)


def set_tool_context(
    span: trace.Span,
    tool_name: str,
    mcp_server: str | None = None,
) -> None:
    """Set tool context attributes on a span.

    Args:
        span: The span to add attributes to.
        tool_name: The name of the tool being called.
        mcp_server: Optional MCP server name.
    """
    span.set_attribute("tool.name", tool_name)
    if mcp_server:
        span.set_attribute("mcp.server", mcp_server)
