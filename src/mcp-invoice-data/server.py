"""FastMCP Server for Invoice Data - Invoices and purchase orders.

Provides mock data for invoice processing and purchase order validation
for demo purposes.

No session isolation needed - this is read-only reference data.

Extensive logging is enabled to trace MCP creation, HTTP headers,
and all tool invocations for debugging and observability.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from fastmcp import FastMCP, Context
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import settings
from mock_data import (
    check_po as _check_po,
    get_invoice as _get_invoice,
    get_po as _get_po,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Logging Utility Functions
# =============================================================================

def _log_separator(title: str, char: str = "=", width: int = 80) -> None:
    """Log a visual separator for readability."""
    logger.info(char * width)
    logger.info(f"  {title}")
    logger.info(char * width)


def _log_dict(data: dict, prefix: str = "") -> None:
    """Log a dictionary with nice formatting."""
    for key, value in data.items():
        logger.info(f"{prefix}  {key}: {value}")


def _sanitize_for_logging(value: Any, max_length: int = 500) -> str:
    """Sanitize a value for safe logging (truncate long strings, mask secrets)."""
    if value is None:
        return "None"
    str_value = str(value)
    # Mask potential secrets in headers
    if "authorization" in str_value.lower() or "bearer" in str_value.lower():
        return "[REDACTED]"
    if len(str_value) > max_length:
        return str_value[:max_length] + "... [truncated]"
    return str_value


# =============================================================================
# Request/Response Logging Middleware
# =============================================================================

class MCPLoggingMiddleware(Middleware):
    """Comprehensive logging middleware for MCP server.
    
    Logs:
    - All incoming tool calls with full HTTP headers
    - Tool execution timing and results
    - Error details if tool execution fails
    - MCP protocol messages (list_tools, call_tool, etc.)
    """
    
    def __init__(self):
        self.request_counter = 0
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Log before and after every tool call with comprehensive details."""
        self.request_counter += 1
        request_id = f"REQ-{self.request_counter:05d}"
        start_time = time.time()
        tool_name = context.message.name if context.message else "unknown"
        
        # Log incoming request
        _log_separator(f"TOOL CALL START: {tool_name} [{request_id}]", "=")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info(f"Request ID: {request_id}")
        logger.info(f"Tool Name: {tool_name}")
        
        # Extract and log HTTP headers
        try:
            headers = get_http_headers(include_all=True)
            headers_dict = dict(headers)
            logger.info("")
            logger.info("--- HTTP Headers ---")
            for header_name, header_value in sorted(headers_dict.items()):
                sanitized_value = _sanitize_for_logging(header_value)
                logger.info(f"  {header_name}: {sanitized_value}")
            
            # Log specific MCP-related headers
            logger.info("")
            logger.info("--- MCP-Specific Headers ---")
            mcp_headers = [
                "x-session-id", "x-caller-agent", "x-request-id",
                "content-type", "accept", "authorization",
                "x-mcp-version", "x-mcp-client"
            ]
            for h in mcp_headers:
                val = headers_dict.get(h) or headers_dict.get(h.title()) or headers_dict.get(h.upper())
                if val:
                    logger.info(f"  {h}: {_sanitize_for_logging(val)}")
                else:
                    logger.info(f"  {h}: [not present]")
        except Exception as e:
            logger.warning(f"Could not extract HTTP headers: {e}")
            headers_dict = {}
        
        # Log tool arguments
        logger.info("")
        logger.info("--- Tool Arguments ---")
        if context.message and hasattr(context.message, 'arguments'):
            args = context.message.arguments or {}
            for arg_name, arg_value in args.items():
                logger.info(f"  {arg_name}: {_sanitize_for_logging(arg_value)}")
        else:
            logger.info("  [no arguments]")
        
        # Log context state if available
        if context.fastmcp_context:
            logger.info("")
            logger.info("--- FastMCP Context State ---")
            try:
                # Store headers in context for potential use by tools
                context.fastmcp_context.set_state("request_id", request_id)
                context.fastmcp_context.set_state("request_headers", headers_dict)
                logger.info(f"  request_id: {request_id}")
                logger.info(f"  headers_count: {len(headers_dict)}")
            except Exception as e:
                logger.warning(f"  Could not set context state: {e}")
        
        # Execute the tool
        logger.info("")
        logger.info("--- Executing Tool ---")
        error_occurred = None
        result = None
        
        try:
            result = await call_next(context)
        except Exception as e:
            error_occurred = e
            logger.error(f"Tool execution failed: {type(e).__name__}: {e}")
            raise
        finally:
            # Log completion details
            elapsed_ms = (time.time() - start_time) * 1000
            
            logger.info("")
            _log_separator(f"TOOL CALL END: {tool_name} [{request_id}]", "-")
            logger.info(f"Elapsed Time: {elapsed_ms:.2f} ms")
            logger.info(f"Status: {'ERROR' if error_occurred else 'SUCCESS'}")
            
            if result is not None:
                logger.info("")
                logger.info("--- Tool Result (truncated) ---")
                try:
                    if hasattr(result, 'model_dump'):
                        result_str = json.dumps(result.model_dump(), indent=2, default=str)
                    else:
                        result_str = json.dumps(result, indent=2, default=str)
                    logger.info(_sanitize_for_logging(result_str, max_length=1000))
                except Exception:
                    logger.info(f"  {_sanitize_for_logging(str(result))}")
            
            logger.info("="*80)
            logger.info("")
        
        return result
    
    async def on_list_tools(self, context: MiddlewareContext, call_next):
        """Log when client requests the list of available tools."""
        _log_separator("MCP LIST_TOOLS REQUEST", "*")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        
        # Extract and log HTTP headers
        try:
            headers = get_http_headers(include_all=True)
            logger.info("")
            logger.info("--- HTTP Headers ---")
            for header_name, header_value in sorted(dict(headers).items()):
                logger.info(f"  {header_name}: {_sanitize_for_logging(header_value)}")
        except Exception as e:
            logger.warning(f"Could not extract HTTP headers: {e}")
        
        logger.info("")
        logger.info("Fetching available tools...")
        
        result = await call_next(context)
        
        logger.info(f"Returning {len(result) if result else 0} tools to client")
        if result:
            logger.info("")
            logger.info("--- Available Tools ---")
            for tool in result:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                logger.info(f"  - {tool_name}")
        
        logger.info("*"*80)
        logger.info("")
        return result
    
    async def on_list_resources(self, context: MiddlewareContext, call_next):
        """Log when client requests the list of resources."""
        logger.info("[MCP] list_resources called")
        try:
            headers = get_http_headers(include_all=True)
            logger.info(f"[MCP] list_resources headers: {dict(headers)}")
        except Exception:
            pass
        return await call_next(context)
    
    async def on_list_prompts(self, context: MiddlewareContext, call_next):
        """Log when client requests the list of prompts."""
        logger.info("[MCP] list_prompts called")
        try:
            headers = get_http_headers(include_all=True)
            logger.info(f"[MCP] list_prompts headers: {dict(headers)}")
        except Exception:
            pass
        return await call_next(context)


# =============================================================================
# Server Initialization with Logging
# =============================================================================

_log_separator("MCP SERVER INITIALIZATION", "#")
logger.info(f"Timestamp: {datetime.now().isoformat()}")
logger.info(f"Server Name: mcp-invoice-data")
logger.info(f"Host: {settings.host}")
logger.info(f"Port: {settings.port}")
logger.info(f"Debug Mode: {settings.debug}")
logger.info("")

# Configure authentication
logger.info("--- Configuring Authentication ---")
logger.info(f"Auth Type: StaticTokenVerifier")
logger.info(f"Token configured: {'Yes' if settings.api_key else 'No'}")
logger.info(f"Client ID: invoice-data-client")
logger.info(f"Scopes: ['read']")

auth = StaticTokenVerifier(
    tokens={
        settings.api_key: {
            "client_id": "invoice-data-client",
            "scopes": ["read"],
        }
    }
)
logger.info("Authentication configured successfully")
logger.info("")

# Create the FastMCP server
logger.info("--- Creating FastMCP Server Instance ---")
mcp = FastMCP(
    name="mcp-invoice-data",
    instructions="""
    Invoice and purchase order data tools.
    
    Use these tools to:
    - Validate purchase order numbers
    - Retrieve invoice details by ID
    - Retrieve purchase order details by PO number
    
    Data includes sample invoices and purchase orders with realistic
    information for invoice approval workflow demos.
    """,
    auth=auth,
)
logger.info("FastMCP server instance created")

# Add the logging middleware
logger.info("")
logger.info("--- Adding Middleware ---")
mcp.add_middleware(MCPLoggingMiddleware())
logger.info("MCPLoggingMiddleware added - all tool calls will be logged")
logger.info("")
logger.info("#"*80)
logger.info("")


# =============================================================================
# Invoice Data Tools
# =============================================================================


@mcp.tool
def check_po(po_number: str, ctx: Context) -> dict:
    """Check if a purchase order number exists and is valid for invoicing.

    Args:
        po_number: The purchase order number to check (e.g., 'PO-2024-001').

    Returns:
        Validation result with exists, is_valid flags and a message.
    """
    # Enhanced logging with context information
    request_id = ctx.get_state("request_id") or "unknown"
    headers = ctx.get_state("request_headers") or {}
    
    logger.info(f"[TOOL:check_po] Request ID: {request_id}")
    logger.info(f"[TOOL:check_po] Input: po_number={po_number}")
    logger.info(f"[TOOL:check_po] Caller Agent: {headers.get('x-caller-agent', 'unknown')}")
    logger.info(f"[TOOL:check_po] Session ID: {headers.get('x-session-id', 'unknown')}")
    
    result = _check_po(po_number)
    
    logger.info(f"[TOOL:check_po] Result: exists={result.exists}, is_valid={result.is_valid}")
    return result.model_dump()


# @mcp.tool
# def get_invoice(id: str, ctx: Context) -> Optional[dict]:
#     """Get invoice details by ID or invoice number.

#     Args:
#         id: The invoice ID or invoice number (e.g., 'INV-2024-0001' or 'inv-001').

#     Returns:
#         Invoice details including vendor, amounts, line items, and status.
#         Returns None if invoice not found.
#     """
#     # Enhanced logging with context information
#     request_id = ctx.get_state("request_id") or "unknown"
#     headers = ctx.get_state("request_headers") or {}
    
#     logger.info(f"[TOOL:get_invoice] Request ID: {request_id}")
#     logger.info(f"[TOOL:get_invoice] Input: id={id}")
#     logger.info(f"[TOOL:get_invoice] Caller Agent: {headers.get('x-caller-agent', 'unknown')}")
#     logger.info(f"[TOOL:get_invoice] Session ID: {headers.get('x-session-id', 'unknown')}")
    
#     result = _get_invoice(id)
    
#     if result:
#         logger.info(f"[TOOL:get_invoice] Found invoice: {result.invoice_number}, vendor={result.vendor_name}, amount={result.total_amount}")
#         return result.model_dump()
#     else:
#         logger.info(f"[TOOL:get_invoice] Invoice not found for id={id}")
#         return None


@mcp.tool
def send_report(subject: str, text: str, ctx: Context) -> dict:
    """Send a PO validation report notification.

    Args:
        subject: The report subject line.
        text: The report body text.
    Returns:
        Result with success status and message ID.
    """
    import uuid
    import httpx
    
    # Enhanced logging with context information
    request_id = ctx.get_state("request_id") or "unknown"
    headers = ctx.get_state("request_headers") or {}
    
    logger.info(f"[TOOL:send_report] Request ID: {request_id}")
    logger.info(f"[TOOL:send_report] Caller Agent: {headers.get('x-caller-agent', 'unknown')}")
    logger.info(f"[TOOL:send_report] Session ID: {headers.get('x-session-id', 'unknown')}")
    
    # Logic App HTTP trigger URL
    logic_app_url = (
        "https://prod-70.eastus.logic.azure.com:443/workflows/de4fbd31b1e54dc7a3abbfc9dda4dd37/triggers/When_an_HTTP_request_is_received/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2FWhen_an_HTTP_request_is_received%2Frun&sv=1.0&sig=sWLLyRKSpPgqMr729fnQ6UFD5-uEPa3D-gaEwEH1h1E"
    )
    
    # Prepare payload for Logic App
    payload = {
        "email_subject": subject,
        "email_body": text,
    }
    
    # Generate a message ID for tracking
    message_id = f"MSG-{uuid.uuid4().hex[:12].upper()}"
    
    logger.info(f"[TOOL:send_report] Sending report via Logic App: message_id={message_id}")
    logger.info(f"[TOOL:send_report] Subject: {subject}")
    logger.info(f"[TOOL:send_report] Body length: {len(text)} chars")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                logic_app_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        
        logger.info(f"[TOOL:send_report] Logic App responded with status: {response.status_code}")
        
        return {
            "success": True,
            "message_id": message_id,
            "subject": subject,
            "status": "sent",
            "logic_app_status_code": response.status_code,
            "timestamp": datetime.now().isoformat(),
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"[TOOL:send_email] Logic App HTTP error: {e.response.status_code} - {e.response.text}")
        return {
            "success": False,
            "message_id": message_id,
            "subject": subject,
            "status": "failed",
            "error": f"HTTP {e.response.status_code}: {e.response.text}",
            "timestamp": datetime.now().isoformat(),
        }
    except httpx.RequestError as e:
        logger.error(f"[TOOL:send_email] Logic App request error: {e}")
        return {
            "success": False,
            "message_id": message_id,
            "subject": subject,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@mcp.tool
def create_event(subject: str, start_time: str, end_time: str, ctx: Context) -> dict:
    """Create a calendar event placeholder.

    Args:
        subject: Event subject/title.
        start_time: ISO timestamp for start (e.g., 2025-12-26T09:00:00), normally due-date at 09:00.
        end_time: ISO timestamp for end (e.g., 2025-12-26T09:00:00), normally due-date at 09:15.
    Returns:
        Result with success flag, normalized times, and request metadata.
    """
    import uuid
    import httpx

    request_id = ctx.get_state("request_id") or "unknown"
    headers = ctx.get_state("request_headers") or {}

    logger.info(f"[TOOL:create_event] Request ID: {request_id}")
    logger.info(f"[TOOL:create_event] Caller Agent: {headers.get('x-caller-agent', 'unknown')}")
    logger.info(f"[TOOL:create_event] Session ID: {headers.get('x-session-id', 'unknown')}")
    logger.info(f"[TOOL:create_event] Subject: {subject}")
    logger.info(f"[TOOL:create_event] Start: {start_time}")
    logger.info(f"[TOOL:create_event] End (input): {end_time or '[auto]'}")

    try:
        start_dt = datetime.fromisoformat(start_time)
    except ValueError:
        logger.error("[TOOL:create_event] Invalid start_time format; expected ISO 8601")
        return {
            "success": False,
            "error": "Invalid start_time format; expected ISO 8601 (e.g., 2025-12-26T09:00:00)",
            "request_id": request_id,
        }

    computed_end = start_dt + timedelta(minutes=15)

    if end_time:
        try:
            provided_end = datetime.fromisoformat(end_time)
            if provided_end != computed_end:
                logger.info(
                    "[TOOL:create_event] Adjusting end_time to 15 minutes after start_time"
                )
        except ValueError:
            logger.warning("[TOOL:create_event] Invalid end_time provided; recalculating")
        finally:
            end_dt = computed_end
    else:
        end_dt = computed_end

    logic_app_url = (
        "https://prod-05.eastus.logic.azure.com:443/workflows/02ae72c000254564abc000c5bedd8a6a/triggers/When_an_HTTP_request_is_received/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2FWhen_an_HTTP_request_is_received%2Frun&sv=1.0&sig=uo0zDeQmpVuzEpBHi6vawacmy1kjRE1nXoQ2pW-A894"
    )

    payload = {
        "event_subject": subject,
        "event_start": start_dt.isoformat(),
        "event_end": end_dt.isoformat(),
        "duration_minutes": 15,
    }

    event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"

    logger.info(f"[TOOL:create_event] Sending event to Logic App: event_id={event_id}")
    logger.info(f"[TOOL:create_event] Start: {payload['event_start']} -> End: {payload['event_end']}")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                logic_app_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        logger.info(f"[TOOL:create_event] Logic App responded with status: {response.status_code}")

        return {
            "success": True,
            "event_id": event_id,
            "subject": subject,
            "start_time": payload["event_start"],
            "end_time": payload["event_end"],
            "duration_minutes": 15,
            "status": "created",
            "logic_app_status_code": response.status_code,
            "request_id": request_id,
        }
    except httpx.HTTPStatusError as e:
        logger.error(
            f"[TOOL:create_event] Logic App HTTP error: {e.response.status_code} - {e.response.text}"
        )
        return {
            "success": False,
            "event_id": event_id,
            "subject": subject,
            "status": "failed",
            "error": f"HTTP {e.response.status_code}: {e.response.text}",
            "request_id": request_id,
        }
    except httpx.RequestError as e:
        logger.error(f"[TOOL:create_event] Logic App request error: {e}")
        return {
            "success": False,
            "event_id": event_id,
            "subject": subject,
            "status": "failed",
            "error": str(e),
            "request_id": request_id,
        }


@mcp.tool
def get_po(po_number: str, ctx: Context) -> Optional[dict]:
    """Get purchase order details by PO number.

    Args:
        po_number: The purchase order number (e.g., 'PO-2024-001').

    Returns:
        Purchase order details including vendor, amounts, line items, and status.
        Returns None if purchase order not found.
    """
    # Enhanced logging with context information
    request_id = ctx.get_state("request_id") or "unknown"
    headers = ctx.get_state("request_headers") or {}
    
    logger.info(f"[TOOL:get_po] Request ID: {request_id}")
    logger.info(f"[TOOL:get_po] Input: po_number={po_number}")
    logger.info(f"[TOOL:get_po] Caller Agent: {headers.get('x-caller-agent', 'unknown')}")
    logger.info(f"[TOOL:get_po] Session ID: {headers.get('x-session-id', 'unknown')}")
    
    result = _get_po(po_number)
    
    if result:
        logger.info(f"[TOOL:get_po] Found PO: {result.po_number}, vendor={result.vendor_name}, status={result.status}")
        return result.model_dump()
    else:
        logger.info(f"[TOOL:get_po] PO not found for po_number={po_number}")
        return None


# =============================================================================
# Health Check
# =============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request):
    """Health check endpoint for load balancers and monitoring."""
    # Log health check requests (but less verbosely)
    logger.debug(f"[HEALTH] Health check from {request.client.host if request.client else 'unknown'}")
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-invoice-data",
    })


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request: Request):
    """Readiness check for Kubernetes/Container Apps."""
    logger.debug(f"[READY] Readiness check from {request.client.host if request.client else 'unknown'}")
    return JSONResponse({"status": "ready"})


# =============================================================================
# Debug Endpoint for Inspecting Request
# =============================================================================

@mcp.custom_route("/debug/request", methods=["GET", "POST"])
async def debug_request(request: Request):
    """Debug endpoint to inspect incoming request details.
    
    Useful for debugging MCP client behavior and header inspection.
    """
    _log_separator("DEBUG REQUEST INSPECTION", "~")
    
    # Collect all request information
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client": {
            "host": request.client.host if request.client else None,
            "port": request.client.port if request.client else None,
        },
        "headers": {},
    }
    
    # Log all headers
    logger.info("--- Request Headers ---")
    for name, value in request.headers.items():
        sanitized = _sanitize_for_logging(value)
        request_info["headers"][name] = sanitized
        logger.info(f"  {name}: {sanitized}")
    
    # Try to read body for POST requests
    if request.method == "POST":
        try:
            body = await request.body()
            body_str = body.decode("utf-8")
            request_info["body"] = _sanitize_for_logging(body_str, max_length=2000)
            logger.info("")
            logger.info("--- Request Body ---")
            logger.info(request_info["body"])
        except Exception as e:
            request_info["body_error"] = str(e)
            logger.warning(f"Could not read body: {e}")
    
    logger.info("~"*80)
    
    return JSONResponse(request_info)
