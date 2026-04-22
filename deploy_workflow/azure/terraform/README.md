# Terraform - Workflow Infrastructure

This Terraform deploys the workflow runtime components:

- ACR for building/pushing images via ACR Tasks
- Container Apps (workflow backend + mcp-invoice-data)
- User Assigned Managed Identity shared by both apps
- Azure AI Foundry account + project, with model deployments (gpt-5, gpt-4o-mini)

## Usage

```bash
terraform init
cp terraform.tfvars.example terraform.tfvars
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```
