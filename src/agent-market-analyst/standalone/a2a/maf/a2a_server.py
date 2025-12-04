"""A2A Server implementation for the Market Analyst Agent.

This module implements the A2A (Agent-to-Agent) protocol server that wraps
the Microsoft Agent Framework Market Analyst agent, making it accessible
to other A2A-compliant agents.

The A2A protocol is defined at: https://a2a-protocol.org/latest/specification/
"""

import logging
import secrets

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
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

from agent import MarketAnalystAgent
from config import get_settings

logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware:
    """Pure ASGI middleware for API key authentication.
    
    Validates requests using Bearer token or X-API-Key header.
    The agent card endpoint (/.well-known/agent-card.json) is always public.
    
    Uses pure ASGI interface to avoid request body consumption issues
    that can occur with BaseHTTPMiddleware.
    """

    # Endpoints that don't require authentication
    # Agent Card endpoints MUST be public per A2A spec - clients need to read
    # the card to discover authentication requirements (securitySchemes)
    PUBLIC_PATHS = {
        "/.well-known/agent.json",      # A2A SDK default path
        "/.well-known/agent-card.json",  # A2A spec standard path
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


class MarketAnalystExecutor(AgentExecutor):
    """A2A AgentExecutor implementation for the Market Analyst.

    This class bridges the A2A protocol with the underlying Microsoft Agent
    Framework agent, handling message processing, task management, and
    response generation.
    """

    def __init__(self) -> None:
        """Initialize the executor."""
        self._settings = get_settings()
        self._agent: MarketAnalystAgent | None = None

    async def _ensure_agent(self) -> MarketAnalystAgent:
        """Ensure the agent is initialized.

        Returns:
            The initialized agent instance.
        """
        if self._agent is None:
            self._agent = MarketAnalystAgent(self._settings)
            await self._agent.initialize()
        return self._agent

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent for an incoming A2A message.

        This method processes incoming messages, runs them through the
        Market Analyst agent, and produces the appropriate A2A response.

        Args:
            context: The request context containing the message and task info.
            event_queue: Queue for sending events back to the client.
        """
        try:
            agent = await self._ensure_agent()

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

            # Run the agent
            response_text = await agent.run(user_message)

            # Add response as artifact and complete
            await updater.add_artifact(
                parts=[Part(root=TextPart(text=response_text))],
                name="Market Analysis Response",
            )
            await updater.complete()

        except ServerError:
            raise
        except Exception as e:
            logger.exception(f"Error executing agent: {e}")
            raise ServerError(error=UnsupportedOperationError(message=str(e)))

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
    """Create the A2A AgentCard for the Market Analyst.

    The AgentCard is a JSON metadata document that describes the agent's
    identity, capabilities, skills, and how to interact with it.

    Per A2A spec, the AgentCard declares authentication requirements via
    `securitySchemes` and `security` fields. This allows clients to discover
    how to authenticate before making operational requests.

    Args:
        port: The server port.

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
        url=f"http://{settings.a2a_public_host}:{port}/",
        capabilities=AgentCapabilities(
            streaming=False,
            pushNotifications=False,
            stateTransitionHistory=False,
        ),
        default_input_modes=["text"],
        default_output_modes=["text"],
        security_schemes=security_schemes,
        security=security,
        skills=[
            AgentSkill(
                id="market-sizing",
                name="Market Size Analysis",
                description=(
                    "Analyze total addressable market (TAM), serviceable market (SAM), "
                    "and obtainable market (SOM) for specialty coffee in target cities."
                ),
                tags=["market", "sizing", "tam", "sam", "som", "analysis"],
                examples=[
                    "What is the market size for specialty coffee in Brno?",
                    "Calculate TAM/SAM/SOM for Vienna coffee market",
                    "How big is the third-wave coffee market in Czech Republic?",
                ],
            ),
            AgentSkill(
                id="consumer-analysis",
                name="Consumer Behavior Analysis",
                description=(
                    "Analyze coffee consumption patterns, customer segments, "
                    "demographics, and spending behavior in target markets."
                ),
                tags=["consumer", "behavior", "demographics", "segments", "coffee"],
                examples=[
                    "What are the key customer segments for specialty coffee in Vienna?",
                    "Analyze coffee consumption patterns in Brno",
                    "Who are the target customers for a third-wave coffee shop?",
                ],
            ),
            AgentSkill(
                id="market-trends",
                name="Market Trends & Dynamics",
                description=(
                    "Identify market trends, growth drivers, industry dynamics, "
                    "and opportunities in the specialty coffee sector."
                ),
                tags=["trends", "growth", "dynamics", "opportunities", "coffee"],
                examples=[
                    "What are the growth trends in specialty coffee?",
                    "Identify opportunities in the Vienna coffee market",
                    "What drives demand for third-wave coffee?",
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
    executor = MarketAnalystExecutor()

    # Create the request handler with task store
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )


def build_app(port: int = 8020):
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
