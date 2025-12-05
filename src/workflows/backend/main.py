"""
FastAPI backend for running agentic workflows with SSE streaming.
"""

import asyncio
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from typing import AsyncGenerator

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ResponseStreamEventType
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Thread pool for running synchronous Azure SDK calls
executor = ThreadPoolExecutor(max_workers=4)


# -----------------------------------------------------------------------------
# Event Models for Streaming
# -----------------------------------------------------------------------------


class WorkflowEventType(str, Enum):
    """Types of events emitted during workflow execution."""
    
    # Lifecycle events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    # Response events
    RESPONSE_CREATED = "response_created"
    RESPONSE_IN_PROGRESS = "response_in_progress"
    RESPONSE_COMPLETED = "response_completed"
    RESPONSE_FAILED = "response_failed"
    
    # Actor/Action events
    ACTOR_STARTED = "actor_started"
    ACTOR_COMPLETED = "actor_completed"
    
    # Content events
    TEXT_DELTA = "text_delta"
    TEXT_DONE = "text_done"
    MESSAGE_COMPLETED = "message_completed"
    
    # MCP events
    MCP_TOOLS_LISTED = "mcp_tools_listed"
    MCP_CALL_IN_PROGRESS = "mcp_call_in_progress"
    MCP_CALL_COMPLETED = "mcp_call_completed"
    MCP_CALL_FAILED = "mcp_call_failed"
    
    # Reasoning events
    REASONING_COMPLETED = "reasoning_completed"
    
    # Error events
    ERROR = "error"


class WorkflowEvent(BaseModel):
    """Base event model for workflow streaming."""
    
    type: WorkflowEventType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: dict = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "healthy"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WorkflowRequest(BaseModel):
    """Request to run a workflow."""
    
    workflow_name: str = "wf1"
    workflow_version: str = "1"
    message: str = "Please extract the data from this invoice."
    conversation_id: str | None = None  # Optional: continue existing conversation


# -----------------------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------------------


app = FastAPI(
    title="Invoice Processing Workflow API",
    description="API for running agentic invoice processing workflows with SSE streaming",
    version="0.1.0",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Azure AI Project configuration
AZURE_AI_ENDPOINT = "https://ai-foundry-mma-ncus.services.ai.azure.com/api/projects/proj-default"


def get_project_client() -> AIProjectClient:
    """Create and return an Azure AI Project client."""
    return AIProjectClient(
        endpoint=AZURE_AI_ENDPOINT,
        credential=DefaultAzureCredential(),
    )


def create_event(event_type: WorkflowEventType, **data) -> str:
    """Create a Server-Sent Event formatted string."""
    event = WorkflowEvent(type=event_type, data=data)
    return f"data: {event.model_dump_json()}\n\n"


def run_workflow_sync(
    workflow_name: str,
    workflow_version: str,
    message: str,
    image_base64: str | None,
    conversation_id: str | None,
    event_queue: Queue,
):
    """
    Synchronous workflow runner that pushes events to a queue.
    Runs in a separate thread to not block the async event loop.
    
    Args:
        workflow_name: Name of the workflow to run.
        workflow_version: Version of the workflow.
        message: User message to process.
        image_base64: Optional base64-encoded image data.
        conversation_id: Optional existing conversation ID to continue.
        event_queue: Queue to push events to.
    """
    # Track current action context
    current_action_id: str | None = None
    
    try:
        event_queue.put(create_event(WorkflowEventType.WORKFLOW_STARTED,
                                     workflow_name=workflow_name,
                                     workflow_version=workflow_version))

        project_client = get_project_client()

        with project_client:
            openai_client = project_client.get_openai_client()
            
            # Create new conversation or use existing one
            if conversation_id:
                # Use existing conversation
                conversation_id_to_use = conversation_id
                is_new_conversation = False
            else:
                # Create new conversation
                conversation = openai_client.conversations.create()
                conversation_id_to_use = conversation.id
                is_new_conversation = True

            event_queue.put(create_event(WorkflowEventType.RESPONSE_CREATED,
                                         conversation_id=conversation_id_to_use,
                                         is_new_conversation=is_new_conversation))

            # Build user message content
            content = [{"type": "input_text", "text": message}]
            if image_base64:
                content.append({
                    "type": "input_image",
                    "detail": "auto",
                    "image_url": f"data:image/jpeg;base64,{image_base64}",
                })

            user_message = [
                {
                    "type": "message",
                    "role": "user",
                    "content": content,
                }
            ]

            workflow = {"name": workflow_name, "version": workflow_version}

            stream = openai_client.responses.create(
                conversation=conversation_id_to_use,
                extra_body={"agent": {"name": workflow["name"], "type": "agent_reference"}},
                input=user_message,
                stream=True,
                metadata={"x-ms-debug-mode-enabled": "1"},
            )

            for event in stream:
                # Response lifecycle events
                if event.type == ResponseStreamEventType.RESPONSE_CREATED:
                    event_queue.put(create_event(WorkflowEventType.RESPONSE_CREATED,
                                                 response_id=event.response.id))

                elif event.type == ResponseStreamEventType.RESPONSE_IN_PROGRESS:
                    event_queue.put(create_event(WorkflowEventType.RESPONSE_IN_PROGRESS,
                                                 status=event.response.status))

                elif event.type == ResponseStreamEventType.RESPONSE_COMPLETED:
                    usage = event.response.usage
                    usage_data = {}
                    if usage:
                        usage_data = {
                            "total_tokens": usage.total_tokens,
                            "input_tokens": usage.input_tokens,
                            "output_tokens": usage.output_tokens,
                        }
                    event_queue.put(create_event(WorkflowEventType.RESPONSE_COMPLETED, **usage_data))

                elif event.type == ResponseStreamEventType.RESPONSE_FAILED:
                    event_queue.put(create_event(WorkflowEventType.RESPONSE_FAILED,
                                                 error=str(event.response.error)))

                # Output item events
                elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_ADDED:
                    if event.item.type == "workflow_action":
                        current_action_id = event.item.action_id
                        event_queue.put(create_event(WorkflowEventType.ACTOR_STARTED,
                                                     action_id=event.item.action_id))
                    elif event.item.type == "reasoning":
                        event_queue.put(create_event(WorkflowEventType.REASONING_COMPLETED,
                                                     reasoning_id=event.item.id,
                                                     action_id=current_action_id))
                    elif event.item.type == "message":
                        event_queue.put(create_event(WorkflowEventType.MESSAGE_COMPLETED,
                                                     message_id=event.item.id,
                                                     action_id=current_action_id,
                                                     status="started"))

                elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_DONE:
                    if event.item.type == "workflow_action":
                        event_queue.put(create_event(WorkflowEventType.ACTOR_COMPLETED,
                                                     action_id=event.item.action_id,
                                                     status=event.item.status,
                                                     previous_action_id=event.item.previous_action_id))
                        current_action_id = None
                    elif event.item.type == "message":
                        event_queue.put(create_event(WorkflowEventType.MESSAGE_COMPLETED,
                                                     message_id=event.item.id,
                                                     action_id=current_action_id,
                                                     status="completed"))
                    elif event.item.type == "mcp_list_tools":
                        tools = [t.name for t in event.item.tools] if event.item.tools else []
                        event_queue.put(create_event(WorkflowEventType.MCP_TOOLS_LISTED,
                                                     server_label=event.item.server_label,
                                                     tools=tools,
                                                     action_id=current_action_id))
                    elif event.item.type == "reasoning":
                        pass  # Already handled in ADDED

                # Text output events
                elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DELTA:
                    event_queue.put(create_event(WorkflowEventType.TEXT_DELTA, 
                                                 delta=event.delta,
                                                 action_id=current_action_id))

                elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DONE:
                    event_queue.put(create_event(WorkflowEventType.TEXT_DONE, 
                                                 text=event.text,
                                                 action_id=current_action_id))

                # MCP events
                elif event.type == ResponseStreamEventType.RESPONSE_MCP_CALL_IN_PROGRESS:
                    event_queue.put(create_event(WorkflowEventType.MCP_CALL_IN_PROGRESS,
                                                 action_id=current_action_id))

                elif event.type == ResponseStreamEventType.RESPONSE_MCP_CALL_COMPLETED:
                    event_queue.put(create_event(WorkflowEventType.MCP_CALL_COMPLETED,
                                                 action_id=current_action_id))

                elif event.type == ResponseStreamEventType.RESPONSE_MCP_CALL_FAILED:
                    event_queue.put(create_event(WorkflowEventType.MCP_CALL_FAILED,
                                                 action_id=current_action_id))

                # Error event
                elif event.type == ResponseStreamEventType.ERROR:
                    event_queue.put(create_event(WorkflowEventType.ERROR, error=str(event)))

            event_queue.put(create_event(WorkflowEventType.WORKFLOW_COMPLETED,
                                         conversation_id=conversation_id_to_use))

    except Exception as e:
        event_queue.put(create_event(WorkflowEventType.WORKFLOW_FAILED, error=str(e)))
    finally:
        # Signal end of stream
        event_queue.put(None)


async def run_workflow_stream(
    workflow_name: str,
    workflow_version: str,
    message: str,
    image_base64: str | None = None,
    conversation_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Run an agentic workflow and stream events.
    
    Args:
        workflow_name: Name of the workflow to run.
        workflow_version: Version of the workflow.
        message: User message to process.
        image_base64: Optional base64-encoded image data.
        conversation_id: Optional existing conversation ID to continue.
        
    Yields:
        Server-Sent Event formatted strings.
    """
    event_queue: Queue = Queue()
    loop = asyncio.get_event_loop()
    
    # Start the synchronous workflow in a thread
    future = loop.run_in_executor(
        executor,
        run_workflow_sync,
        workflow_name,
        workflow_version,
        message,
        image_base64,
        conversation_id,
        event_queue,
    )
    
    # Yield events as they arrive
    while True:
        try:
            # Check queue with small timeout to allow async cooperation
            event_data = await loop.run_in_executor(
                None,
                lambda: event_queue.get(timeout=0.1)
            )
            if event_data is None:
                # End of stream
                break
            yield event_data
        except Empty:
            # Check if the thread is still running
            if future.done():
                # Drain remaining events
                while True:
                    try:
                        event_data = event_queue.get_nowait()
                        if event_data is None:
                            break
                        yield event_data
                    except Empty:
                        break
                break
            continue


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse()


@app.post("/workflow/run")
async def run_workflow(
    message: str = Form(default="Please extract the data from this invoice."),
    workflow_name: str = Form(default="wf1"),
    workflow_version: str = Form(default="1"),
    conversation_id: str | None = Form(default=None),
    invoice: UploadFile | None = File(default=None),
):
    """
    Run an agentic workflow with optional invoice image.
    
    Args:
        message: User message to process.
        workflow_name: Name of the workflow to run.
        workflow_version: Version of the workflow.
        conversation_id: Optional existing conversation ID to continue.
        invoice: Optional invoice image file.
    
    Returns a Server-Sent Events stream of workflow events.
    """
    image_base64 = None
    if invoice:
        content = await invoice.read()
        image_base64 = base64.b64encode(content).decode("ascii")
    
    return StreamingResponse(
        run_workflow_stream(
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            message=message,
            image_base64=image_base64,
            conversation_id=conversation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/workflow/run/json")
async def run_workflow_json(request: WorkflowRequest):
    """
    Run an agentic workflow without an image (JSON body).
    
    Args:
        request: Workflow request with message, workflow name/version, and optional conversation_id.
    
    Returns a Server-Sent Events stream of workflow events.
    """
    return StreamingResponse(
        run_workflow_stream(
            workflow_name=request.workflow_name,
            workflow_version=request.workflow_version,
            message=request.message,
            image_base64=None,
            conversation_id=request.conversation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
