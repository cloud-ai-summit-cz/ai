"""Application Insights Trace Poller for real-time SSE events.

Implements ADR-005: Real-time Agent Observability via OpenTelemetry and Application Insights.

This module polls Application Insights for traces matching a session's operation_Id,
parses them into SSE-friendly events, and streams them to the frontend.

Why Polling?
- Azure AI Foundry Hosted Agents execute tools SERVER-SIDE
- MAF's stream_callback only receives text tokens, not tool calls from hosted agents
- App Insights captures ALL spans (including subagent tool calls) via OpenTelemetry
- Polling App Insights provides unified visibility across all agent types

Architecture:
1. Session starts → parent span created with operation_Id
2. All subagent/tool spans inherit this operation_Id via W3C Trace Context
3. Poller queries App Insights for spans matching operation_Id
4. New spans are parsed and emitted as SSE events

Latency Expectation:
- App Insights has 2-5 second ingestion delay
- Polling every 2 seconds → total latency ~4-7 seconds from action to SSE
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator

from azure.core.exceptions import HttpResponseError
from azure.identity.aio import DefaultAzureCredential
from azure.monitor.query.aio import LogsQueryClient
from azure.monitor.query import LogsQueryStatus

from models import SSEEvent, SSEEventType

logger = logging.getLogger(__name__)

# Polling configuration
POLL_INTERVAL_SECONDS = 2.0  # How often to query App Insights
INITIAL_LOOKBACK_SECONDS = 30  # How far back to look on first poll
MAX_RESULTS_PER_POLL = 100  # Limit results to prevent overwhelming the SSE stream


class TraceEvent:
    """Parsed trace event from Application Insights."""
    
    def __init__(
        self,
        timestamp: datetime,
        name: str,
        operation_id: str,
        span_id: str | None = None,
        parent_id: str | None = None,
        duration_ms: float | None = None,
        success: bool | None = None,
        custom_dimensions: dict[str, Any] | None = None,
        trace_type: str = "trace",  # 'trace', 'dependency', 'request'
    ):
        self.timestamp = timestamp
        self.name = name
        self.operation_id = operation_id
        self.span_id = span_id
        self.parent_id = parent_id
        self.duration_ms = duration_ms
        self.success = success
        self.custom_dimensions = custom_dimensions or {}
        self.trace_type = trace_type
    
    @property
    def agent_name(self) -> str | None:
        """Extract agent name from custom dimensions."""
        return (
            self.custom_dimensions.get("gen_ai.agent.name") or
            self.custom_dimensions.get("agent.name") or
            self.custom_dimensions.get("agent_name")
        )
    
    @property
    def tool_name(self) -> str | None:
        """Extract tool name from custom dimensions or span name."""
        tool = self.custom_dimensions.get("tool.name")
        if tool:
            return tool
        # Check if span name indicates a tool call
        if self.name.startswith("tool.") or self.name.startswith("mcp."):
            return self.name.split(".", 1)[1] if "." in self.name else self.name
        return None
    
    @property
    def mcp_server(self) -> str | None:
        """Extract MCP server name from custom dimensions."""
        return self.custom_dimensions.get("mcp.server")
    
    @property
    def is_tool_call(self) -> bool:
        """Check if this trace represents a tool call."""
        return (
            self.name.startswith("tool.") or
            self.name.startswith("mcp.") or
            self.custom_dimensions.get("tool.name") is not None or
            self.trace_type == "dependency"
        )
    
    @property
    def is_agent_invocation(self) -> bool:
        """Check if this trace represents an agent invocation."""
        return (
            self.name.startswith("agent.") or
            self.name.startswith("delegate_to_") or
            self.custom_dimensions.get("tool.type") == "subagent"
        )
    
    @property
    def session_id(self) -> str | None:
        """Extract session ID from custom dimensions."""
        return self.custom_dimensions.get("session.id")
    
    def __repr__(self) -> str:
        return f"TraceEvent(name={self.name}, agent={self.agent_name}, tool={self.tool_name}, duration_ms={self.duration_ms})"


class AppInsightsTracePoller:
    """Polls Application Insights for session traces and emits SSE events.
    
    Usage:
        async with AppInsightsTracePoller(workspace_id, session_id, operation_id) as poller:
            async for event in poller.poll_traces():
                yield event  # SSEEvent
    
    Thread Safety:
        Each instance should be used by a single session's SSE stream.
        The poller maintains internal state (last_poll_time, seen_spans).
    """
    
    def __init__(
        self,
        workspace_id: str,
        session_id: str,
        operation_id: str,
        credential: DefaultAzureCredential | None = None,
    ):
        """Initialize the trace poller.
        
        Args:
            workspace_id: Log Analytics Workspace ID (GUID).
            session_id: Research session ID for event tagging.
            operation_id: The operation_Id (trace ID) to filter by.
            credential: Optional credential (creates new one if not provided).
        """
        self.workspace_id = workspace_id
        self.session_id = session_id
        self.operation_id = operation_id
        self._credential = credential
        self._owns_credential = credential is None
        self._client: LogsQueryClient | None = None
        self._last_poll_time: datetime | None = None
        self._seen_span_ids: set[str] = set()  # Deduplicate spans
        self._is_running = False
        self._poll_count = 0
        self._total_traces_found = 0
        
        logger.info(
            f"AppInsightsTracePoller initialized: "
            f"session_id={session_id[:8]}..., "
            f"operation_id={operation_id[:16]}..., "
            f"workspace_id={workspace_id[:8]}..."
        )
    
    async def __aenter__(self) -> "AppInsightsTracePoller":
        """Initialize the Azure Monitor client."""
        if self._owns_credential:
            self._credential = DefaultAzureCredential()
        
        self._client = LogsQueryClient(self._credential)
        self._is_running = True
        
        logger.info(f"TracePoller started for session {self.session_id[:8]}...")
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Cleanup resources."""
        self._is_running = False
        
        if self._client:
            await self._client.close()
            self._client = None
        
        if self._owns_credential and self._credential:
            await self._credential.close()
            self._credential = None
        
        logger.info(
            f"TracePoller stopped for session {self.session_id[:8]}...: "
            f"polls={self._poll_count}, traces_found={self._total_traces_found}"
        )
    
    def _build_query(self, since: datetime) -> str:
        """Build the KQL query for fetching traces.
        
        Args:
            since: Only fetch traces after this timestamp.
            
        Returns:
            KQL query string.
        """
        # Format timestamp for KQL
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        # Query both AppTraces and AppDependencies tables (Azure Monitor schema)
        # - AppTraces: Custom spans, log messages
        # - AppDependencies: HTTP calls, database queries, MCP tool calls
        # Note: Azure Monitor uses different table names than classic Application Insights
        query = f"""
        union 
            (AppTraces 
            | where OperationId == "{self.operation_id}"
            | where TimeGenerated > datetime({since_str})
            | extend spanId = tostring(Properties["SpanId"])
            | extend parentId = ParentId
            | extend durationMs = todouble(Properties["duration_ms"])
            | extend traceType = "trace"
            | project timestamp=TimeGenerated, name=OperationName, message=Message, severityLevel=SeverityLevel, 
                      operation_Id=OperationId, spanId, parentId, durationMs, 
                      customDimensions=Properties, traceType, success=true),
            (AppDependencies
            | where OperationId == "{self.operation_id}"
            | where TimeGenerated > datetime({since_str})
            | extend spanId = Id
            | extend parentId = ParentId
            | extend durationMs = DurationMs
            | extend traceType = "dependency"
            | project timestamp=TimeGenerated, name=Name, message="", severityLevel=0,
                      operation_Id=OperationId, spanId, parentId, durationMs,
                      customDimensions=Properties, traceType, success=Success)
        | order by timestamp asc
        | take {MAX_RESULTS_PER_POLL}
        """
        return query
    
    def _parse_trace_row(self, row: list[Any], columns: list[str]) -> TraceEvent | None:
        """Parse a query result row into a TraceEvent.
        
        Args:
            row: List of values from the query result.
            columns: Column names corresponding to the values.
            
        Returns:
            Parsed TraceEvent or None if parsing fails.
        """
        try:
            # Build a dict from row and columns
            data = dict(zip(columns, row))
            
            # Parse timestamp
            timestamp = data.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now(timezone.utc)
            
            # Parse custom dimensions (may be JSON string or dict)
            custom_dims = data.get("customDimensions", {})
            if isinstance(custom_dims, str):
                import json
                try:
                    custom_dims = json.loads(custom_dims)
                except json.JSONDecodeError:
                    custom_dims = {}
            
            # Extract span name - prefer 'name' field, fall back to message
            name = data.get("name") or data.get("message") or "unknown"
            
            return TraceEvent(
                timestamp=timestamp,
                name=str(name),
                operation_id=str(data.get("operation_Id", "")),
                span_id=str(data.get("spanId", "")) or None,
                parent_id=str(data.get("parentId", "")) or None,
                duration_ms=float(data.get("durationMs", 0)) if data.get("durationMs") else None,
                success=data.get("success"),
                custom_dimensions=custom_dims,
                trace_type=str(data.get("traceType", "trace")),
            )
        except Exception as e:
            logger.warning(f"Failed to parse trace row: {e}")
            return None
    
    def _trace_to_sse_event(self, trace: TraceEvent) -> SSEEvent | None:
        """Convert a TraceEvent to an SSEEvent.
        
        Determines the appropriate SSE event type based on trace characteristics.
        
        Args:
            trace: Parsed trace event.
            
        Returns:
            SSEEvent or None if trace should be filtered out.
        """
        # Skip internal/noise traces
        if trace.name in ("heartbeat", "health_check", "/health"):
            return None
        
        # Determine event type and build payload
        if trace.is_agent_invocation:
            # Agent invocation span
            event_type = SSEEventType.TRACE_SPAN_COMPLETED if trace.duration_ms else SSEEventType.TRACE_SPAN_STARTED
            data = {
                "span_name": trace.name,
                "agent_name": trace.agent_name or self._extract_agent_from_name(trace.name),
                "operation_id": trace.operation_id,
                "timestamp": trace.timestamp.isoformat(),
            }
            if trace.duration_ms:
                data["duration_ms"] = int(trace.duration_ms)
                data["success"] = trace.success
            
            logger.info(
                f"TracePoller: Agent invocation - {trace.name}, "
                f"agent={data.get('agent_name')}, duration_ms={trace.duration_ms}"
            )
        
        elif trace.is_tool_call:
            # Tool/MCP call span
            event_type = SSEEventType.TRACE_TOOL_CALL
            tool_name = trace.tool_name or trace.name
            data = {
                "span_name": trace.name,
                "tool_name": tool_name,
                "agent_name": trace.agent_name,
                "mcp_server": trace.mcp_server,
                "operation_id": trace.operation_id,
                "timestamp": trace.timestamp.isoformat(),
            }
            if trace.duration_ms:
                data["duration_ms"] = int(trace.duration_ms)
                data["success"] = trace.success
            
            logger.info(
                f"TracePoller: Tool call - {tool_name}, "
                f"agent={trace.agent_name}, mcp={trace.mcp_server}, duration_ms={trace.duration_ms}"
            )
        
        else:
            # Generic span - might be workflow phases, etc.
            # Only emit if it has meaningful content
            if not trace.duration_ms and not trace.custom_dimensions:
                return None
            
            event_type = SSEEventType.TRACE_SPAN_COMPLETED if trace.duration_ms else SSEEventType.TRACE_SPAN_STARTED
            data = {
                "span_name": trace.name,
                "operation_id": trace.operation_id,
                "timestamp": trace.timestamp.isoformat(),
            }
            if trace.duration_ms:
                data["duration_ms"] = int(trace.duration_ms)
            if trace.agent_name:
                data["agent_name"] = trace.agent_name
            
            logger.debug(f"TracePoller: Generic span - {trace.name}")
        
        return SSEEvent(
            event_type=event_type,
            session_id=self.session_id,
            timestamp=trace.timestamp,
            data=data,
        )
    
    def _extract_agent_from_name(self, span_name: str) -> str | None:
        """Extract agent name from span name patterns.
        
        Args:
            span_name: The span name (e.g., "delegate_to_market-analyst").
            
        Returns:
            Extracted agent name or None.
        """
        if span_name.startswith("delegate_to_"):
            return span_name.replace("delegate_to_", "")
        if span_name.startswith("agent."):
            return span_name.replace("agent.", "")
        return None
    
    async def poll_once(self) -> list[SSEEvent]:
        """Execute a single poll and return new events.
        
        Returns:
            List of new SSE events since last poll.
        """
        if not self._client:
            raise RuntimeError("Poller not initialized. Use 'async with' context manager.")
        
        self._poll_count += 1
        
        # Determine time range
        now = datetime.now(timezone.utc)
        if self._last_poll_time is None:
            # First poll - look back a bit to catch early spans
            since = now - timedelta(seconds=INITIAL_LOOKBACK_SECONDS)
        else:
            # Subsequent polls - only get new traces
            # Add small overlap to handle timing issues
            since = self._last_poll_time - timedelta(seconds=1)
        
        query = self._build_query(since)
        
        logger.info(
            f"TracePoller poll #{self._poll_count}: "
            f"session={self.session_id[:8]}..., operation_id={self.operation_id}, since={since.isoformat()}"
        )
        logger.info(f"TracePoller KQL query (first 500 chars):\n{query[:500]}...")
        
        events: list[SSEEvent] = []
        
        try:
            # Query App Insights
            response = await self._client.query_workspace(
                workspace_id=self.workspace_id,
                query=query,
                timespan=timedelta(hours=1),  # Max lookback window
            )
            
            if response.status == LogsQueryStatus.SUCCESS:
                total_rows = sum(len(table.rows) for table in response.tables)
                logger.info(f"TracePoller query SUCCESS: {total_rows} rows returned from Log Analytics")
                
                # Log sample of raw data for debugging
                if total_rows > 0:
                    for table in response.tables:
                        columns = [col.name for col in table.columns]
                        logger.info(f"TracePoller columns: {columns}")
                        for i, row in enumerate(table.rows[:3]):  # Log first 3 rows
                            logger.info(f"TracePoller row[{i}]: {dict(zip(columns, row))}")
                
                for table in response.tables:
                    columns = [col.name for col in table.columns]
                    
                    for row in table.rows:
                        trace = self._parse_trace_row(row, columns)
                        if not trace:
                            continue
                        
                        # Deduplicate by span ID
                        if trace.span_id and trace.span_id in self._seen_span_ids:
                            continue
                        if trace.span_id:
                            self._seen_span_ids.add(trace.span_id)
                        
                        # Convert to SSE event
                        sse_event = self._trace_to_sse_event(trace)
                        if sse_event:
                            events.append(sse_event)
                            self._total_traces_found += 1
                
                logger.info(
                    f"TracePoller poll #{self._poll_count} complete: "
                    f"found {len(events)} new events"
                )
            
            elif response.status == LogsQueryStatus.PARTIAL:
                logger.warning(
                    f"TracePoller partial result: {response.partial_error}"
                )
                # Still process partial data
                for table in response.partial_data or []:
                    columns = [col.name for col in table.columns]
                    for row in table.rows:
                        trace = self._parse_trace_row(row, columns)
                        if trace and trace.span_id not in self._seen_span_ids:
                            if trace.span_id:
                                self._seen_span_ids.add(trace.span_id)
                            sse_event = self._trace_to_sse_event(trace)
                            if sse_event:
                                events.append(sse_event)
            
            else:
                logger.error(f"TracePoller query failed: {response}")
        
        except HttpResponseError as e:
            logger.error(f"TracePoller HTTP error: {e.status_code} - {e.message}")
            logger.error(f"TracePoller HTTP error details: {e}")
        except Exception as e:
            logger.exception(f"TracePoller unexpected error: {e}")
            import traceback
            logger.error(f"TracePoller full traceback: {traceback.format_exc()}")
        
        # Update last poll time
        self._last_poll_time = now
        
        return events
    
    async def poll_traces(self) -> AsyncGenerator[SSEEvent, None]:
        """Continuously poll for traces and yield SSE events.
        
        This generator runs until stopped or the context manager exits.
        It yields SSE events as they are discovered from App Insights.
        
        Yields:
            SSEEvent objects for each discovered trace.
        """
        logger.info(f"TracePoller starting continuous polling for session {self.session_id[:8]}...")
        
        while self._is_running:
            try:
                events = await self.poll_once()
                for event in events:
                    yield event
                
                # Wait before next poll
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
            
            except asyncio.CancelledError:
                logger.info(f"TracePoller cancelled for session {self.session_id[:8]}...")
                break
            except Exception as e:
                logger.exception(f"TracePoller error during polling: {e}")
                # Continue polling after error
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        
        logger.info(f"TracePoller stopped for session {self.session_id[:8]}...")
    
    def stop(self) -> None:
        """Signal the poller to stop."""
        logger.info(f"TracePoller stop requested for session {self.session_id[:8]}...")
        self._is_running = False


# Convenience function for creating a poller from config
async def create_trace_poller(
    workspace_id: str,
    session_id: str,
    operation_id: str,
) -> AppInsightsTracePoller:
    """Create and initialize a trace poller.
    
    Args:
        workspace_id: Log Analytics Workspace ID.
        session_id: Research session ID.
        operation_id: The operation_Id (trace ID) to filter by.
        
    Returns:
        Initialized AppInsightsTracePoller (must be used with async with).
    """
    return AppInsightsTracePoller(
        workspace_id=workspace_id,
        session_id=session_id,
        operation_id=operation_id,
    )
