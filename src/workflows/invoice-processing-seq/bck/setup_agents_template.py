"""Lightweight helper that provisions the three invoice workflow agents."""

from __future__ import annotations

import os

from azure.ai.projects import AIProjectClient, models
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential

DEFAULT_PROJECT_ENDPOINT = "https://ai-foundry-mma-ncus.services.ai.azure.com/api/projects/proj-default"
DEFAULT_MODEL_DEPLOYMENT = "gpt-4o-mini"
ENV_PROJECT_ENDPOINT = "AZURE_AI_PROJECT_ENDPOINT"
ENV_MODEL_DEPLOYMENT = "AZURE_AI_MODEL_DEPLOYMENT_NAME"

INVOICE_EXTRACTION_SCHEMA: dict[str, object] = {
	"type": "object",
	"properties": {
		"po_number": {"type": "string"},
		"invoice_number": {"type": "string"},
		"invoice_date": {"type": "string", "description": "ISO 8601 date"},
		"due_date": {"type": "string", "description": "ISO 8601 date"},
		"currency": {"type": "string", "description": "Three letter ISO currency code"},
		"supplier": {
			"type": "object",
			"properties": {
				"name": {"type": "string"},
				"address": {"type": "string"},
				"email": {"type": "string"},
				"phone": {"type": "string"},
			},
			"required": ["name"],
		},
		"bill_to": {
			"type": "object",
			"properties": {
				"name": {"type": "string"},
				"address": {"type": "string"},
				"department": {"type": "string"},
			},
		},
		"line_items": {
			"type": "array",
			"items": {
				"type": "object",
				"properties": {
					"description": {"type": "string"},
					"quantity": {"type": "number"},
					"unit_price": {"type": "number"},
					"uom": {"type": "string"},
					"total": {"type": "number"},
				},
				"required": ["description", "quantity", "unit_price", "total"],
			},
		},
		"subtotal": {"type": "number"},
		"tax": {"type": "number"},
		"shipping": {"type": "number"},
		"total": {"type": "number"},
		"confidence": {"type": "number", "description": "0-1 confidence score"},
		"notes": {"type": "string"},
	},
	"required": ["invoice_number", "invoice_date", "supplier", "line_items", "total"],
}


VALIDATION_SCHEMA: dict[str, object] = {
	"type": "object",
	"properties": {
		"is_ready_for_posting": {"type": "boolean"},
		"issues": {
			"type": "array",
			"items": {
				"type": "object",
				"properties": {
					"code": {"type": "string"},
					"severity": {"type": "string", "enum": ["info", "warning", "error"]},
					"message": {"type": "string"},
					"field": {"type": "string"},
				},
				"required": ["code", "severity", "message"],
			},
		},
		"normalized_invoice": INVOICE_EXTRACTION_SCHEMA,
		"po_validation_result": {
			"type": "object",
			"properties": {
				"po_number": {"type": "string"},
				"is_valid": {"type": "boolean"},
				"tool_name": {"type": "string"},
				"notes": {"type": "string"},
			},
			"required": ["po_number", "is_valid"],
		},
		"business_rules": {
			"type": "array",
			"items": {
				"type": "object",
				"properties": {
					"rule": {"type": "string"},
					"passed": {"type": "boolean"},
					"details": {"type": "string"},
				},
				"required": ["rule", "passed"],
			},
		},
	},
	"required": ["is_ready_for_posting", "issues", "normalized_invoice"],
}


HANDOFF_SCHEMA: dict[str, object] = {
	"type": "object",
	"properties": {
		"summary": {"type": "string"},
		"next_step": {"type": "string", "enum": ["auto_post", "manual_review", "vendor_follow_up"]},
		"target_queue": {"type": "string"},
		"approved_amount": {"type": "number"},
		"hold_reason": {"type": "string"},
		"attachments": {
			"type": "array",
			"items": {
				"type": "object",
				"properties": {
					"name": {"type": "string"},
					"type": {"type": "string"},
					"uri": {"type": "string"},
				},
				"required": ["name", "uri"],
			},
		},
	},
	"required": ["summary", "next_step", "approved_amount"],
}


MCP_INVOICE_DATA_TOOL = models.MCPTool(
	server_label="MCPInvoiceData",
	server_url="https://mcp-invoice-data.bluetree-fdff5920.eastus2.azurecontainerapps.io/mcp",
	project_connection_id="MCPInvoiceData",
)


INTAKE_INSTRUCTIONS = (
	"You are the intake agent for accounts payable. You always start from the provided image or "
	"scanned invoice and optional operator hints. Perform OCR, normalize numbers, and extract the "
	"full invoice payload listed in the schema. When totals do not match the sum of line items, add "
	"a note. Always respond strictly with JSON that matches the InvoiceExtraction schema."
)


VALIDATION_INSTRUCTIONS = (
	"You are the validation agent. You receive the intake JSON plus optional ERP context. Check for "
	"missing or inconsistent values, confirm totals, verify PO availability, and flag duplicates. "
	"You have access to a set of MCP-provided tools that expose enterprise systems and knowledge bases. "
	"Always consider which tools can supply authoritative data before responding. You MUST extract the "
	"`po_number` field from the intake payload (when present) and populate the `po_validation_result` "
	"field, recording a corresponding entry in `business_rules`. You MUST use the available tools "
	"whenever they can improve accuracy, coverage, or confidence—even if that requires multiple tool "
	"calls. Return JSON that states whether the invoice can move forward, include issues that require a "
	"human, and always echo back a normalized invoice payload that downstream systems can reuse."
)


SUMMARY_INSTRUCTIONS = (
	"You are invoice backoffice agent. Summarize the output JSON from the invoice-processing pipeline."
)


def delete_agent_if_exists(client: AIProjectClient, name: str) -> None:
	try:
		client.agents.delete(agent_name=name)
		print(f"Deleted existing agent '{name}'.")
	except HttpResponseError as exc:
		if exc.status_code != 404:
			raise


def main() -> None:
	endpoint = os.getenv(ENV_PROJECT_ENDPOINT, DEFAULT_PROJECT_ENDPOINT)
	deployment = os.getenv(ENV_MODEL_DEPLOYMENT, DEFAULT_MODEL_DEPLOYMENT)
	if not endpoint or not deployment:
		raise RuntimeError("Project endpoint and model deployment must be configured.")
	with DefaultAzureCredential() as credential:
		with AIProjectClient(endpoint=endpoint, credential=credential) as client:
			# delete_agent_if_exists(client, "invoice-intake-agent")
			# delete_agent_if_exists(client, "invoice-process-summary-agent")
			# delete_agent_if_exists(client, "invoice-validation-agent")
			# exit(0)  # Remove this line to enable agent creation

			delete_agent_if_exists(client, "invoice-intake-agent")
			client.agents.create(
				name="invoice-intake-agent",
				definition=models.PromptAgentDefinition(
					model=deployment,
					instructions=INTAKE_INSTRUCTIONS,
					temperature=0.0,
					text=models.PromptAgentDefinitionText(
						format=models.ResponseTextFormatConfigurationJsonSchema(
							name="InvoiceExtraction",
							description="Structured invoice payload produced by the intake agent",
							schema=INVOICE_EXTRACTION_SCHEMA,
							strict=False,
						)
					),
				),
				description="Invoice Intake Agent",
				metadata={
					"workflow_sequence": "1",
					"workflow_role": "intake",
					"workflow_display_name": "Invoice Intake Agent",
				},
			)
			delete_agent_if_exists(client, "invoice-validation-agent")
			client.agents.create(
				name="invoice-validation-agent",
				definition=models.PromptAgentDefinition(
					model=deployment,
					instructions=VALIDATION_INSTRUCTIONS,
					temperature=0.1,
					tools=[MCP_INVOICE_DATA_TOOL],
					text=models.PromptAgentDefinitionText(
						format=models.ResponseTextFormatConfigurationJsonSchema(
							name="InvoiceValidation",
							description="Validation results with normalized invoice data",
							schema=VALIDATION_SCHEMA,
							strict=False,
						)
					),
				),
				description="Invoice Validation Agent",
				metadata={
					"workflow_sequence": "2",
					"workflow_role": "validation",
					"workflow_display_name": "Invoice Validation Agent",
					"workflow_handoff": "invoice-process-summary-agent",
				},
			)
			delete_agent_if_exists(client, "invoice-process-summary-agent")
			client.agents.create(
				name="invoice-process-summary-agent",
				definition=models.PromptAgentDefinition(
					model=deployment,
					instructions=SUMMARY_INSTRUCTIONS,
					temperature=0.2,
					text=models.PromptAgentDefinitionText(
						format=models.ResponseTextFormatConfigurationJsonSchema(
							name="InvoiceProcessSummary",
							description="Summary of the invoice processing pipeline output",
							schema=HANDOFF_SCHEMA,
							strict=False,
						)
					),
				),
				description="Invoice Process Summary Agent",
				metadata={
					"workflow_sequence": "3",
					"workflow_role": "summary",
					"workflow_display_name": "Invoice Process Summary Agent",
				},
			)
	print("Provisioned invoice workflow agents.")


if __name__ == "__main__":
	main()
