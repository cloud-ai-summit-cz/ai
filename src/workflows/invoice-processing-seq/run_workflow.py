# Before running the sample:
#    pip install --pre azure-ai-projects>=2.0.0b1
#    pip install azure-identity

import base64
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ResponseStreamEventType


project_client = AIProjectClient(
    endpoint="https://ai-foundry-mma-ncus.services.ai.azure.com/api/projects/proj-default",
    credential=DefaultAzureCredential(),
)

with project_client:

    workflow = {
        "name": "wf1",
        "version": "1",
    }
    
    openai_client = project_client.get_openai_client()
    

    conversation = openai_client.conversations.create()
    print(f"Created conversation (id: {conversation.id})")

    # invoice_path = Path(__file__).resolve().parent / "data" / "invoice1.jpg"
    invoice_path = Path(__file__).resolve().parent / "data" / "invoice2.jpg"
    # invoice_path = Path(__file__).resolve().parent / "data" / "invoice3.jpg"
    with invoice_path.open("rb") as invoice_file:
        base64_invoice = base64.b64encode(invoice_file.read()).decode("ascii")

    # user_message = [
    #     {
    #         "role": "user",
    #         "content": [
    #             {"type": "input_text", "text": "Hi test - please review the attached invoice."},
    #             {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_invoice}"},
    #         ],
    #     }
    # ]

    user_message =[
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Please extract the data from this invoice."},
                    {"type": "input_image", "detail": "auto", "image_url": f"data:image/jpeg;base64,{base64_invoice}"},
                ],
            }
        ]

    # # Add user message with the invoice image
    # openai_client.conversations.items.create(
    #     conversation_id=conversation.id,
    #     items=[
    #         {
    #             "type": "message",
    #             "role": "user",
    #             "content": [
    #                 {"type": "input_text", "text": "Please extract the data from this invoice."},
    #                 {"type": "input_image", "detail": "auto", "image_url": f"data:image/jpeg;base64,{base64_invoice}"},
    #             ],
    #         }
    #     ],
    # )
    # print("Added invoice image to conversation")

    # # print conversation items
    # items = openai_client.conversations.items.list(conversation_id=conversation.id)
    # for item in items:
    #     print(item.content[0:100])


    stream = openai_client.responses.create(
        conversation=conversation.id,
        extra_body={"agent": {"name": workflow["name"], "type": "agent_reference"}},
        input=user_message,
        # input="",
        stream=True,
        metadata={"x-ms-debug-mode-enabled": "1"},
    )

    for event in stream:
        # Response lifecycle events
        if event.type == ResponseStreamEventType.RESPONSE_CREATED:
            print(f"Response created (id: {event.response.id})")
            items = openai_client.conversations.items.list(conversation_id=conversation.id)
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_IN_PROGRESS:
            print(f"Response in progress (status: {event.response.status})")
        elif event.type == ResponseStreamEventType.RESPONSE_COMPLETED:
            usage = event.response.usage
            if usage:
                print(f"Response completed (tokens: {usage.total_tokens} total, {usage.input_tokens} in, {usage.output_tokens} out)")
            else:
                print("Response completed")
        elif event.type == ResponseStreamEventType.RESPONSE_FAILED:
            print(f"Response failed: {event.response.error}")
        elif event.type == ResponseStreamEventType.RESPONSE_INCOMPLETE:
            print(f"Response incomplete: {event.response.incomplete_details}")

        # Output item events
        elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_ADDED:
            if event.item.type == "workflow_action":
                print(f"********************************\nActor - '{event.item.action_id}' :")
            else:
                print(f"New output item of type '{event.item.type}' added: {event.item}")
        elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_DONE:
            if event.item.type == "workflow_action":
                print(f"Workflow Item '{event.item.action_id}' is '{event.item.status}' - (previous item was: '{event.item.previous_action_id}')")
            elif event.item.type == "message":
                print(f"Message completed (id: {event.item.id})")
            elif event.item.type == "mcp_list_tools":
                tools = [t.name for t in event.item.tools] if event.item.tools else []
                print(f"MCP tools listed for '{event.item.server_label}': {tools}")
            elif event.item.type == "reasoning":
                print(f"Reasoning step completed (id: {event.item.id})")
            else:
                print(f"Output item done (type: {event.item.type})")

        # Content part events
        elif event.type == ResponseStreamEventType.RESPONSE_CONTENT_PART_ADDED:
            pass  # Content part being added, text will come via delta/done events
        elif event.type == ResponseStreamEventType.RESPONSE_CONTENT_PART_DONE:
            pass

        # Text output events
        elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DELTA:
            # print(event.delta)
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DONE:
            print("\t", event.text)

        # MCP events
        elif event.type == ResponseStreamEventType.RESPONSE_MCP_LIST_TOOLS_IN_PROGRESS:
            print("MCP list tools in progress...")
        elif event.type == ResponseStreamEventType.RESPONSE_MCP_LIST_TOOLS_COMPLETED:
            print("MCP list tools completed")
        elif event.type == ResponseStreamEventType.RESPONSE_MCP_LIST_TOOLS_FAILED:
            print(f"MCP list tools failed")
        elif event.type == ResponseStreamEventType.RESPONSE_MCP_CALL_IN_PROGRESS:
            print("MCP call in progress...")
        elif event.type == ResponseStreamEventType.RESPONSE_MCP_CALL_ARGUMENTS_DELTA:
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_MCP_CALL_ARGUMENTS_DONE:
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_MCP_CALL_COMPLETED:
            print("MCP call completed")
        elif event.type == ResponseStreamEventType.RESPONSE_MCP_CALL_FAILED:
            print("MCP call failed")

        # Reasoning events
        elif event.type == ResponseStreamEventType.RESPONSE_REASONING_DELTA:
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_REASONING_DONE:
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_REASONING_SUMMARY_PART_ADDED:
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_REASONING_SUMMARY_PART_DONE:
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_REASONING_SUMMARY_TEXT_DELTA:
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_REASONING_SUMMARY_TEXT_DONE:
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_REASONING_SUMMARY_DELTA:
            pass
        elif event.type == ResponseStreamEventType.RESPONSE_REASONING_SUMMARY_DONE:
            pass

        # Error event
        elif event.type == ResponseStreamEventType.ERROR:
            print(f"Error: {event}")

        else:
            print(f"Unknown event {event.type}: {event}")

    # openai_client.conversations.delete(conversation_id=conversation.id)
    print("Conversation deleted")
