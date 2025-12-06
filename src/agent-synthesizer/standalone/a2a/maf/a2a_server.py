"""A2A Server implementation for the Synthesizer Agent.

This module implements the A2A (Agent-to-Agent) protocol server that wraps
the Microsoft Agent Framework Synthesizer agent, making it accessible
to other A2A-compliant agents.

The A2A protocol is defined at: https://a2a-protocol.org/latest/specification/

Note: This server enables streaming mode to support keepalive heartbeats during
long-running agent tasks. This prevents Azure Load Balancer from dropping idle
connections (4-minute timeout) by sending periodic TaskStatusUpdateEvent messages.
"""

import asyncio
import logging
import secrets

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.apps.jsonrpc.jsonrpc_app import CallContextBuilder
from a2a.server.context import ServerCallContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    APIKeySecurityScheme,
    Part,
    SecurityScheme,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from agent import SynthesizerAgent
from config import get_settings

logger = logging.getLogger(__name__)

# Header name for session ID (matches MCP Scratchpad server expectation)
SESSION_ID_HEADER = "X-Session-ID"


class SessionContextBuilder(CallContextBuilder):
    """Custom CallContextBuilder that extracts session context from HTTP headers.
    
    Extracts X-Session-ID from incoming A2A requests and stores it in
    ServerCallContext.state for access by the executor. This enables
    session-scoped MCP tool calls where the session ID flows from:
    orchestrator -> A2A agent -> MCP server.
    """

    def build(self, request: Request) -> ServerCallContext:
        """Build ServerCallContext from Starlette Request.
        
        Extracts X-Session-ID header if present and stores in context state.
        
        Args:
            request: The incoming Starlette HTTP request.
            
        Returns:
            ServerCallContext with session_id in state if header was present.
        """
        state = {}
        
        # Extract session ID from header
        session_id = request.headers.get(SESSION_ID_HEADER)
        if session_id:
            state["session_id"] = session_id
            logger.debug(f"Extracted session_id from header: {session_id}")
        else:
            logger.debug(f"No {SESSION_ID_HEADER} header found in request")
        
        return ServerCallContext(state=state)


class APIKeyAuthMiddleware:
    """Pure ASGI middleware for API key authentication.
    
    Validates requests using Bearer token or X-API-Key header.
    The agent card endpoint (/.well-known/agent-card.json) is always public.
    
    Uses pure ASGI interface to avoid request body consumption issues
    that can occur with BaseHTTPMiddleware.
    """

    # Endpoints that don't require authentication
    # Agent Card endpoint MUST be public per A2A spec Section 8.2 - clients
    # need to read the card to discover authentication requirements (securitySchemes)
    PUBLIC_PATHS = {
        "/.well-known/agent-card.json",  # A2A spec standard path (Section 14.3)
        "/health",
        "/ready",
    }

    def __init__(self, app: ASGIApp, api_key: str) -> None:
        """Initialize the middleware.
        
        Args:
            app: The ASGI application.
            api_key: The required API key for authentication.
        """
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the ASGI request.
        
        Args:
            scope: The ASGI scope.
            receive: The receive callable.
            send: The send callable.
        """
        if scope["type"] != "http":
            # Pass through non-HTTP requests (websocket, lifespan, etc.)
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        
        # Allow public endpoints without auth
        if path in self.PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        # Extract headers from scope
        headers = dict(scope.get("headers", []))
        
        # Check for API key in headers
        api_key = None
        
        # Check Authorization header (Bearer token)
        auth_header = headers.get(b"authorization", b"").decode()
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # Remove "Bearer " prefix
        
        # Check X-API-Key header as alternative
        if not api_key:
            api_key = headers.get(b"x-api-key", b"").decode()

        # Validate API key using constant-time comparison
        if not api_key or not secrets.compare_digest(api_key, self.api_key):
            client_host = scope.get("client", ("unknown", 0))[0]
            logger.warning(f"Unauthorized request to {path} from {client_host}")
            
            # Return 401 response
            response = JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "unauthorized",
                        "message": "Invalid or missing API key. Provide via 'Authorization: Bearer <key>' or 'X-API-Key: <key>' header.",
                    }
                },
            )
            await response(scope, receive, send)
            return

        # Auth passed, continue to app
        await self.app(scope, receive, send)


class SynthesizerExecutor(AgentExecutor):
    """A2A AgentExecutor implementation for the Synthesizer.

    This class bridges the A2A protocol with the underlying Microsoft Agent
    Framework agent, handling message processing, task management, and
    response generation.
    
    The executor creates per-request agent instances when a session_id is
    provided in the request context (via X-Session-ID header). This enables
    session-scoped MCP tool access for cross-agent collaboration.
    """

    def __init__(self) -> None:
        """Initialize the executor."""
        self._settings = get_settings()
        # Shared agent for requests without session context
        self._shared_agent: SynthesizerAgent | None = None

    async def _get_agent(self, session_id: str | None = None) -> SynthesizerAgent:
        """Get or create an agent instance.
        
        When session_id is provided, creates a new agent instance with
        session-scoped MCP Scratchpad access. Otherwise, returns the
        shared agent instance.

        Args:
            session_id: Optional session ID for session-scoped tools.

        Returns:
            The appropriate agent instance.
        """
        if session_id:
            # Create per-request agent with session context
            logger.info(f"Creating session-scoped agent for session: {session_id}")
            agent = SynthesizerAgent(self._settings, session_id=session_id)
            await agent.initialize()
            return agent
        else:
            # Use shared agent for non-session requests
            if self._shared_agent is None:
                self._shared_agent = SynthesizerAgent(self._settings)
                await self._shared_agent.initialize()
            return self._shared_agent

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent for an incoming A2A message.

        This method processes incoming messages, runs them through the
        Synthesizer agent, and produces the appropriate A2A response.
        
        If X-Session-ID header was provided in the request, the agent
        will have access to session-scoped MCP Scratchpad for collaboration.

        Args:
            context: The request context containing the message and task info.
            event_queue: Queue for sending events back to the client.
        """
        session_scoped_agent: SynthesizerAgent | None = None
        try:
            # Extract session_id from context state (set by SessionContextBuilder)
            session_id = context.call_context.state.get("session_id") if context.call_context else None
            if session_id:
                logger.info(f"Request has session context: {session_id}")
            
            agent = await self._get_agent(session_id)
            # Track if we created a session-scoped agent that needs cleanup
            if session_id:
                session_scoped_agent = agent

            # Extract the text content from the message
            user_message = context.get_user_input()
            
            if not user_message:
                raise ServerError(
                    error=UnsupportedOperationError(
                        message="No text content found in message"
                    )
                )

            logger.info(f"Processing message: {user_message[:100]}...")

            # Get or create task
            task = context.current_task
            if not task:
                task = new_task(context.message)
                await event_queue.enqueue_event(task)

            # Create task updater for managing task state
            updater = TaskUpdater(event_queue, task.id, task.context_id)

            # Mark task as working
            await updater.start_work()

            # Start keepalive task to prevent Azure LB from dropping idle connections
            # Azure Load Balancer has a 4-minute idle timeout that cannot be changed
            async def send_keepalive():
                keepalive_count = 0
                while True:
                    await asyncio.sleep(60)  # Send every 60 seconds (well under 4-min limit)
                    keepalive_count += 1
                    await updater.update_status(
                        state=TaskState.working,
                        message=new_agent_text_message(
                            f"Analysis in progress... ({keepalive_count} min elapsed)"
                        ),
                    )

            keepalive_task = asyncio.create_task(send_keepalive())

            try:
                # Run the agent
                response_text = await agent.run(user_message)
            finally:
                # Cancel keepalive task when agent completes
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except asyncio.CancelledError:
                    pass

            # Add response as artifact and complete
            await updater.add_artifact(
                parts=[Part(root=TextPart(text=response_text))],
                name="Synthesis Report",
            )
            await updater.complete()

        except ServerError:
            raise
        except Exception as e:
            logger.exception(f"Error executing agent: {e}")
            raise ServerError(error=UnsupportedOperationError(message=str(e)))
        finally:
            # Clean up session-scoped agent resources
            if session_scoped_agent is not None:
                await session_scoped_agent.close()
                logger.debug("Session-scoped agent resources released")

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle task cancellation.

        Args:
            context: The request context.
            event_queue: Queue for sending events.
        """
        logger.info(f"Cancellation requested for task: {context.task_id}")
        raise ServerError(
            error=UnsupportedOperationError(message="cancel not supported")
        )


def create_agent_card(port: int) -> AgentCard:
    """Create the A2A AgentCard for the Synthesizer.

    The AgentCard is a JSON metadata document that describes the agent's
    identity, capabilities, skills, and how to interact with it.

    Per A2A spec, the AgentCard declares authentication requirements via
    `securitySchemes` and `security` fields. This allows clients to discover
    how to authenticate before making operational requests.

    Args:
        port: The server port (used for local development URL).

    Returns:
        The configured AgentCard.
    """
    settings = get_settings()

    # Build security configuration if API key is enabled
    security_schemes: dict[str, SecurityScheme] | None = None
    security: list[dict[str, list[str]]] | None = None
    
    if settings.a2a_api_key:
        # Declare API key authentication requirement per A2A spec Section 4.5
        security_schemes = {
            "apiKey": SecurityScheme(
                root=APIKeySecurityScheme(
                    type="apiKey",
                    name="X-API-Key",
                    in_="header",
                    description="API key for authenticating requests. Can also be provided via 'Authorization: Bearer <key>' header.",
                )
            )
        }
        # Require apiKey for all operations
        security = [{"apiKey": []}]

    return AgentCard(
        name=settings.a2a_agent_name,
        description=settings.a2a_agent_description,
        version=settings.a2a_agent_version,
        url=settings.a2a_public_url,
        capabilities=AgentCapabilities(
            streaming=True,
            pushNotifications=False,
            stateTransitionHistory=False,
        ),
        default_input_modes=["text"],
        default_output_modes=["text"],
        security_schemes=security_schemes,
        security=security,
        skills=[
            AgentSkill(
                id="read-research-findings",
                name="Read Research Findings",
                description=(
                    "Read research findings from the shared scratchpad including "
                    "market analysis, competitor landscape, location strategy, and financial outlook."
                ),
                tags=["scratchpad", "research", "findings", "read"],
                examples=[
                    "Read the market analysis findings",
                    "Get all research notes from the scratchpad",
                    "Review the draft sections from other analysts",
                ],
            ),
            AgentSkill(
                id="executive-summary",
                name="Executive Summary Generation",
                description=(
                    "Generate an executive summary with clear recommendation "
                    "(EXPAND/DO NOT EXPAND/CONDITIONAL), confidence level, and key findings."
                ),
                tags=["executive-summary", "recommendation", "synthesis"],
                examples=[
                    "Create an executive summary for the Brno expansion",
                    "What's your recommendation based on the research?",
                    "Summarize the key findings and give a decision",
                ],
            ),
            AgentSkill(
                id="risk-assessment",
                name="Risk Assessment",
                description=(
                    "Comprehensive risk analysis across market, competitive, "
                    "operational, financial, and regulatory categories."
                ),
                tags=["risk", "assessment", "mitigation", "analysis"],
                examples=[
                    "What are the key risks for this expansion?",
                    "Provide a risk assessment with mitigation strategies",
                    "Analyze operational and financial risks",
                ],
            ),
            AgentSkill(
                id="financial-synthesis",
                name="Financial Synthesis",
                description=(
                    "Synthesize financial data from analysts into investment requirements, "
                    "ROI projections, and break-even analysis."
                ),
                tags=["financial", "roi", "investment", "break-even"],
                examples=[
                    "What's the total investment required?",
                    "Calculate the expected ROI",
                    "When will the expansion break even?",
                ],
            ),
            AgentSkill(
                id="full-report",
                name="Full Expansion Report",
                description=(
                    "Generate a comprehensive expansion report with all sections: "
                    "executive summary, market opportunity, competitive landscape, "
                    "location strategy, financial outlook, risk assessment, and recommendation."
                ),
                tags=["report", "comprehensive", "expansion", "full"],
                examples=[
                    "Generate the full expansion report",
                    "Synthesize all findings into a comprehensive report",
                    "Create the final Cofilot expansion research report",
                ],
            ),
        ],
    )


def create_app(port: int) -> A2AStarletteApplication:
    """Create the A2A Starlette application.

    Args:
        port: The server port.

    Returns:
        The configured A2A application.
    """
    agent_card = create_agent_card(port)
    executor = SynthesizerExecutor()

    # Create the request handler with task store
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    # Use custom context builder to extract session ID from headers
    context_builder = SessionContextBuilder()

    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
        context_builder=context_builder,
    )


def build_app(port: int = 8024):
    """Build and return the ASGI app.

    Args:
        port: The server port.

    Returns:
        The Starlette ASGI application.
    """
    settings = get_settings()
    a2a_app = create_app(port)
    app = a2a_app.build()

    # Wrap with API key authentication middleware if configured
    if settings.a2a_api_key:
        app = APIKeyAuthMiddleware(app, api_key=settings.a2a_api_key)
        logger.info("API key authentication enabled")
    else:
        logger.warning("API key authentication is DISABLED - server is open to all requests")

    return app
