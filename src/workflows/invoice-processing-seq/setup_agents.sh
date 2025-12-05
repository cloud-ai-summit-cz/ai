#!/bin/bash
# Setup Invoice Processing Workflow
# This script destroys existing agents and creates them fresh
#
# Usage: ./setup_workflow.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Invoice agents in processing order
AGENTS=(
    "agent-invoice-intake"
    "agent-invoice-validation"
    "agent-invoice-summary"
)

echo "=== Invoice Processing Workflow Setup ==="
echo "Source directory: ${SRC_DIR}"
echo ""

for agent in "${AGENTS[@]}"; do
    AGENT_DIR="${SRC_DIR}/${agent}"
    
    if [[ ! -d "${AGENT_DIR}" ]]; then
        echo "ERROR: Agent directory not found: ${AGENT_DIR}"
        exit 1
    fi
    
    echo "----------------------------------------"
    echo "Processing: ${agent}"
    echo "----------------------------------------"
    
    cd "${AGENT_DIR}"
    
    # Re-create new agent
    echo "[${agent}] Creating agent..."
    uv run python provision.py create
    
    echo "[${agent}] Done."
    echo ""
done

echo "=== All invoice agents provisioned successfully ==="
echo ""
echo "Agents created:"
for agent in "${AGENTS[@]}"; do
    echo "  - ${agent}"
done
