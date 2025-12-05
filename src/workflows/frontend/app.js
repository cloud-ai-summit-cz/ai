/**
 * Invoice Processing Workflow Frontend
 * Handles SSE streaming from the backend and displays workflow events
 */

// Configuration
const API_BASE_URL = 'http://localhost:8000';
const WORKFLOW_NAME = 'wf2';
const WORKFLOW_YAML = `
kind: workflow
trigger:
  kind: OnConversationStart
  id: trigger_wf
  actions:
    - kind: InvokeAzureAgent
      id: invoice-validation-agent
      agent:
        name: invoice-validation-agent
      input:
        messages: =System.LastMessage
      output:
        autoSend: true
        messages: Local.LastMessage
    - kind: ConditionGroup
      conditions:
        - condition: =!IsBlank(Find("<INV_OK>", Last(Local.LastMessage).Text))
          actions:
            - kind: Question
              variable: Local.UserApproval
              id: action-1764937921178
              entity: StringPrebuiltEntity
              skipQuestionMode: SkipOnFirstExecutionIfVariableHasValue
              prompt: <QUESTION>Validation OK - Approve?
            - kind: InvokeAzureAgent
              id: invoice-process-summary-agent
              agent:
                name: invoice-process-summary-agent
              input:
                messages: =Local.LastMessage
              output:
                autoSend: true
                messages: Local.LastMessage
            - kind: SendActivity
              activity: |-
                <FINAL> Success! Ivoice approved for payment processing. 

                summary: {Local.LastMessage}
              id: action-1764942712798
          id: if-action-1764883723763-0
      id: action-1764883723763
      elseActions:
        - kind: Question
          variable: Local.UserApproval
          id: action-1764937921111
          entity: StringPrebuiltEntity
          skipQuestionMode: SkipOnFirstExecutionIfVariableHasValue
          prompt: <QUESTION>Validation Fail - send back?
        - kind: InvokeAzureAgent
          id: invoice-mailer-agent
          agent:
            name: invoice-mailer-agent
          input:
            messages: =Local.LastMessage
          output:
            autoSend: true
        - kind: SendActivity
          activity: <FINAL> Invoice sent back to supplier.
          id: action-1764963963215
    - kind: EndConversation
      id: action-1764936956468
id: ""
name: wf2
description: ""

`;
const WORKFLOW_PROMPT_DEMO_USE = true

// Demo invoice data - keyed by filename (without extension)
// Two sample invoices: "invoice1.json" and "invoice2.json"
// Used for demo/testing purposes
const WORKFLOW_INVOICES_DEMO = {
    "invoice1": {
        "po_number": "534",
        "invoice_number": "100",
        "invoice_date": "2025-10-15",
        "due_date": "",
        "currency": "EUR",
        "supplier": {
            "name": "Zava Specialty Coffee",
            "address": "333 3rd Ave, Seattle, WA 12345",
            "email": "",
            "phone": "123-456-7890"
        },
        "bill_to": {
            "name": "Tomas Kubica",
            "address": "Karlinska 1918, Karlin, Czechia",
            "department": "CoPilot Inc"
        },
        "line_items": [
            {
                "description": "Zava Ethiopia for Espresso",
                "quantity": 80,
                "unit_price": 20,
                "uom": "Kg",
                "total": 2000
            }
        ],
        "subtotal": 2000,
        "tax": 300,
        "shipping": 0,
        "total": 2300,
        "confidence": 0.88,
        "notes": "Handwritten PO (534) detected. Invoice # read as '100'. Invoice date read as 10/15/2025 and converted to ISO. Supplier address and purchaser/shipping address OCRed as 'Karlinska 1918, Karlin, Czechia' (minor uncertainty). Totals (subtotal 2000 + tax 300 + shipping 0 = total 2300) match the invoice."
    },
    "invoice2": {
        "invoice_number": "00012",
        "invoice_date": "2205-10-01",
        "due_date": "2205-10-16",
        "currency": "USD",
        "supplier": {
            "name": "Contoso Fin Consulting",
            "address": "450 East 78th Ave, Denver, CO 12345",
            "email": "",
            "phone": "(123) 456-7890"
        },
        "bill_to": {
            "name": "Tomas Kubica",
            "address": "Karlinska 1918, Karlin, Czechia",
            "department": ""
        },
        "line_items": [
            {
                "description": "Consultation services implementation of AI powered grinder",
                "quantity": 3,
                "unit_price": 375,
                "uom": "hours",
                "total": 1125
            }
        ],
        "subtotal": 1125,
        "tax": 0,
        "shipping": 0,
        "total": 1125,
        "confidence": 0.95,
        "notes": "Total matches the sum of line items.",
        "status": "pending"
    }
};

// DOM Elements
const inputSection = document.getElementById('input-section');
const workflowSection = document.getElementById('workflow-section');
const resultSection = document.getElementById('result-section');
const invoiceInput = document.getElementById('invoice-input');
const uploadLabel = document.getElementById('upload-label');
const imagePreview = document.getElementById('image-preview');
const previewImg = document.getElementById('preview-img');
const removeImageBtn = document.getElementById('remove-image');
const promptInput = document.getElementById('prompt-input');
const startBtn = document.getElementById('start-btn');
const workflowStatus = document.getElementById('workflow-status');
const eventsContainer = document.getElementById('events-container');
const resultContent = document.getElementById('result-content');
const restartBtn = document.getElementById('restart-btn');
const followupInput = document.getElementById('followup-input');
const followupBtn = document.getElementById('followup-btn');
const conversationBadge = document.getElementById('conversation-badge');
const workflowDiagram = document.getElementById('workflow-diagram');
const consoleOutput = document.getElementById('console-output');
const consoleClearBtn = document.getElementById('console-clear');
const consoleStatus = document.getElementById('console-status');

// State
let selectedFile = null;
let selectedInvoiceData = null; // Invoice data selected based on filename
let finalText = '';
let actorContainers = {}; // Map action_id -> container element
let currentConversationId = null; // Track conversation ID for follow-ups
let totalAgentCount = 0; // Track total agents across all turns
let diagramNodes = {}; // Map action_id -> diagram node element

// Event Icons mapping
const eventIcons = {
    workflow_started: { icon: '🚀', class: 'workflow', label: 'Workflow Started' },
    workflow_completed: { icon: '✅', class: 'workflow', label: 'Workflow Completed' },
    workflow_failed: { icon: '❌', class: 'error', label: 'Workflow Failed' },
    response_created: { icon: '📝', class: 'response', label: 'Response Created' },
    response_in_progress: { icon: '⏳', class: 'response', label: 'Processing' },
    response_completed: { icon: '✓', class: 'response', label: 'Response Done' },
    response_failed: { icon: '⚠️', class: 'error', label: 'Response Failed' },
    actor_started: { icon: '🤖', class: 'actor', label: 'Agent' },
    actor_completed: { icon: '✓', class: 'actor', label: 'Agent Done' },
    text_delta: { icon: '💬', class: 'text', label: 'Text' },
    text_done: { icon: '📄', class: 'text', label: 'Output' },
    message_completed: { icon: '💬', class: 'text', label: 'Message' },
    mcp_tools_listed: { icon: '🔧', class: 'mcp', label: 'Tools' },
    mcp_call_in_progress: { icon: '⚙️', class: 'mcp', label: 'MCP Call' },
    mcp_call_completed: { icon: '✓', class: 'mcp', label: 'MCP Done' },
    mcp_call_failed: { icon: '⚠️', class: 'error', label: 'MCP Failed' },
    reasoning_completed: { icon: '🧠', class: 'reasoning', label: 'Thinking' },
    error: { icon: '❌', class: 'error', label: 'Error' },
};

// Workflow node type configuration
const nodeTypes = {
    'OnConversationStart': { icon: '▶️', class: 'node-start', label: 'Start' },
    'SetVariable': { icon: '(x)', class: 'node-variable', label: 'Set variable' },
    'InvokeAzureAgent': { icon: '🤖', class: 'node-agent', label: 'Agent' },
    'ConditionGroup': { icon: '⚡', class: 'node-condition', label: 'If/Else condition' },
    'SendActivity': { icon: '💬', class: 'node-message', label: 'Send message' },
    'Question': { icon: '❓', class: 'node-question', label: 'Ask a question' },
};

// Minimal YAML parser tailored for the workflow definition
// Handles objects, arrays, and scalars using indentation only (no anchors/tags)
function parseSimpleYaml(yamlStr) {
    const rawLines = yamlStr.split('\n');
    const cleanedLines = rawLines.filter(line => line.trim() && !line.trim().startsWith('#'));

    const root = {};
    const stack = [{ indent: -1, value: root }];

    const parseValue = (raw) => {
        const unquoted = raw.replace(/^['"]|['"]$/g, '');
        if (unquoted === 'true') return true;
        if (unquoted === 'false') return false;
        if (unquoted === 'null') return null;
            if (unquoted.trim() !== '' && !/^\d+$/.test(unquoted)) return unquoted; // Preserve strings with leading zeros
        return unquoted;
    };

    const peekNextNonEmpty = (startIdx) => {
        for (let j = startIdx + 1; j < cleanedLines.length; j++) {
            const ln = cleanedLines[j].trim();
            if (ln) return cleanedLines[j];
        }
        return null;
    };

    cleanedLines.forEach((line, idx) => {
        const indent = line.search(/\S/);
        const content = line.trim();

        while (stack.length && indent <= stack[stack.length - 1].indent) {
            stack.pop();
        }

        const parent = stack[stack.length - 1]?.value;
        if (parent === undefined) return;

        // Array item
        if (content.startsWith('- ')) {
            if (!Array.isArray(parent)) return; // malformed YAML; ignore

            const itemContent = content.slice(2).trim();
            if (!itemContent.includes(':')) {
                parent.push(parseValue(itemContent));
                return;
            }

            const [k, ...rest] = itemContent.split(':');
            const rawVal = rest.join(':').trim();
            const obj = {};
            if (rawVal) {
                obj[k.trim()] = parseValue(rawVal);
            } else {
                obj[k.trim()] = {};
            }

            parent.push(obj);
            stack.push({ indent, value: obj });
            return;
        }

        // Key/value line
        const colonIdx = content.indexOf(':');
        if (colonIdx === -1) return; // skip invalid

        const key = content.slice(0, colonIdx).trim();
        const rawVal = content.slice(colonIdx + 1).trim();

        if (rawVal === '') {
            const nextLine = peekNextNonEmpty(idx);
            const nextIndent = nextLine ? nextLine.search(/\S/) : indent + 2;
            if (nextLine && nextLine.trim().startsWith('-') && nextIndent > indent) {
                parent[key] = [];
            } else {
                parent[key] = {};
            }
            stack.push({ indent, value: parent[key] });
        } else {
            parent[key] = parseValue(rawVal);
        }
    });

    return root;
}

// Parse workflow YAML and convert to structure for diagram rendering
function getWorkflowStructure() {
    try {
        const parsed = parseSimpleYaml(WORKFLOW_YAML);
        
        // Transform parsed YAML to expected structure
        const workflow = {
            name: parsed.name || 'workflow',
            trigger: {
                kind: parsed.trigger?.kind || 'OnConversationStart',
                id: parsed.trigger?.id || 'trigger',
                actions: []
            }
        };
        
        // Helper to process actions recursively
        function processActions(actionsArray) {
            if (!Array.isArray(actionsArray)) return [];
            
            return actionsArray.map(actionObj => {
                const action = { ...actionObj };
                if (!action.id) {
                    action.id = `${action.kind || 'action'}-${Math.random().toString(36).slice(2, 8)}`;
                }
                
                // Extract agent name for InvokeAzureAgent
                if (action.kind === 'InvokeAzureAgent' && action.agent) {
                    action.agentName = action.agent.name || action.id;
                }
                
                // Process nested conditions
                if (action.kind === 'ConditionGroup' && action.conditions) {
                    action.conditions = action.conditions.map(cond => ({
                        ...cond,
                        actions: processActions(cond.actions || [])
                    }));
                    if (action.elseActions) {
                        action.elseActions = processActions(action.elseActions);
                    }
                }
                
                return action;
            });
        }
        
        // Process trigger actions
        if (parsed.trigger?.actions) {
            workflow.trigger.actions = processActions(parsed.trigger.actions);
        }
        
        console.log('Parsed workflow structure:', workflow);
        return workflow;
        
    } catch (error) {
        console.error('Failed to parse WORKFLOW_YAML:', error);
        // Return minimal fallback structure
        return {
            name: 'wf2',
            trigger: {
                kind: 'OnConversationStart',
                id: 'trigger_wf',
                actions: []
            }
        };
    }
}

// Create a workflow node element
function createNodeElement(action, isStart = false) {
    const config = isStart 
        ? nodeTypes['OnConversationStart']
        : (nodeTypes[action.kind] || { icon: '•', class: 'node-default', label: action.kind });
    
    let label = config.label;
    if (action.kind === 'InvokeAzureAgent' && action.agentName) {
        label = action.agentName;
    } else if (action.kind === 'SetVariable') {
        label = 'Set variable';
    } else if (action.kind === 'SendActivity') {
        label = 'Send message';
    } else if (action.kind === 'Question') {
        label = 'Ask a question';
    } else if (action.kind === 'ConditionGroup') {
        label = 'If/Else condition';
    }
    
    const node = document.createElement('div');
    node.className = `wf-node ${config.class}`;
    node.dataset.actionId = action.id || '';
    
    // Add tooltip for conditions
    let tooltipHtml = '';
    if (action.condition) {
        tooltipHtml = `<div class="wf-node-tooltip">${escapeHtml(action.condition)}</div>`;
    }
    
    node.innerHTML = `
        <div class="wf-node-icon">${config.icon}</div>
        <span class="wf-node-label">${escapeHtml(label)}</span>
        <span class="wf-node-menu">⋯</span>
        ${tooltipHtml}
    `;
    
    // Store reference for status updates
    if (action.id) {
        diagramNodes[action.id] = node;
    }
    
    return node;
}

// Create a connector element
function createConnector() {
    const connector = document.createElement('div');
    connector.className = 'wf-connector';
    return connector;
}

// Create condition label
function createConditionLabel(type) {
    const label = document.createElement('div');
    label.className = `wf-condition-label ${type}-label`;
    label.innerHTML = `<span>${type === 'if' ? 'If' : 'Else'}</span>`;
    return label;
}

// Render the workflow diagram
function renderWorkflowDiagram() {
    console.log('=== renderWorkflowDiagram START ===');
    
    // Re-query the diagram element
    const diagramEl = document.getElementById('workflow-diagram');
    console.log('1. diagramEl found:', !!diagramEl);
    
    if (!diagramEl) {
        console.error('Workflow diagram element not found');
        return;
    }
    
    const container = diagramEl.querySelector('.diagram-container');
    console.log('2. container found:', !!container);
    
    if (!container) {
        console.error('Diagram container not found');
        return;
    }
    
    // Clear and rebuild
    container.innerHTML = '';
    diagramNodes = {};
    
    console.log('3. Container cleared');
    
    try {
        const workflow = getWorkflowStructure();
        console.log('4. Workflow structure:', workflow);

        const actions = workflow.trigger?.actions || [];
        console.log('5. Actions count:', actions.length);

        const conditionIdx = actions.findIndex(action => action.kind === 'ConditionGroup');
        const preActions = conditionIdx === -1 ? actions : actions.slice(0, conditionIdx);
        const conditionAction = conditionIdx === -1 ? null : actions[conditionIdx];
        const postActions = conditionIdx === -1 ? [] : actions.slice(conditionIdx + 1);

        const mainRow = document.createElement('div');
        mainRow.className = 'diagram-row';

        const startNode = createNodeElement({ kind: 'OnConversationStart', id: workflow.trigger?.id || 'trigger_wf' }, true);
        mainRow.appendChild(startNode);

        const appendActionsToRow = (row, actionList) => {
            actionList.forEach((action, idx) => {
                row.appendChild(createConnector());
                row.appendChild(createNodeElement(action));
            });
        };

        appendActionsToRow(mainRow, preActions);

        if (conditionAction) {
            mainRow.appendChild(createConnector());
            mainRow.appendChild(createNodeElement(conditionAction));
        }

        container.appendChild(mainRow);

        const appendBranchRow = (label, branchActions) => {
            const row = document.createElement('div');
            row.className = 'diagram-branch-row';
            row.appendChild(createConditionLabel(label));

            const renderActions = [...(branchActions || [])];
            renderActions.forEach((action, idx) => {
                row.appendChild(createConnector());
                row.appendChild(createNodeElement(action));
            });

            container.appendChild(row);
        };

        if (conditionAction && Array.isArray(conditionAction.conditions) && conditionAction.conditions.length) {
            const ifActions = conditionAction.conditions[0].actions || [];
            appendBranchRow('if', ifActions);
        }

        if (conditionAction && Array.isArray(conditionAction.elseActions)) {
            appendBranchRow('else', conditionAction.elseActions);
        }

        if (conditionAction && postActions.length) {
            const postRow = document.createElement('div');
            postRow.className = 'diagram-branch-row';

            const postLabel = document.createElement('div');
            postLabel.className = 'wf-condition-label then-label';
            postLabel.innerHTML = '<span>Then</span>';
            postRow.appendChild(postLabel);

            postActions.forEach(action => {
                postRow.appendChild(createConnector());
                postRow.appendChild(createNodeElement(action));
            });

            container.appendChild(postRow);
        }

        if (!conditionAction) {
            appendActionsToRow(mainRow, postActions);
        }

        console.log('10. Final container innerHTML length:', container.innerHTML.length);
        console.log('=== renderWorkflowDiagram END ===');

    } catch (error) {
        console.error('Failed to render workflow diagram:', error);
        console.error('Error stack:', error.stack);
        container.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; padding: 1.25rem; color: #b4b4b4;">
                <span>⚠️</span>
                <span>Error: ${error.message}</span>
            </div>
        `;
    }
}

// Update diagram node status
function updateDiagramNodeStatus(actionId, status) {
    console.log('updateDiagramNodeStatus called:', actionId, status);
    console.log('Available diagram nodes:', Object.keys(diagramNodes));
    
    const node = diagramNodes[actionId];
    if (!node) {
        console.log('Node not found for actionId:', actionId);
        return;
    }
    
    node.classList.remove('active', 'completed', 'failed');
    
    // Remove any existing status indicator
    const existingIndicator = node.querySelector('.wf-node-status');
    if (existingIndicator) {
        existingIndicator.remove();
    }
    
    if (status === 'running') {
        node.classList.add('active');
        // Add spinner indicator
        const spinner = document.createElement('div');
        spinner.className = 'wf-node-status running';
        spinner.innerHTML = '<span class="node-spinner"></span>';
        node.appendChild(spinner);
    } else if (status === 'completed') {
        node.classList.add('completed');
        // Add checkmark indicator
        const checkmark = document.createElement('div');
        checkmark.className = 'wf-node-status completed';
        checkmark.innerHTML = '✓';
        node.appendChild(checkmark);
    } else if (status === 'failed') {
        node.classList.add('failed');
        // Add error indicator
        const errorMark = document.createElement('div');
        errorMark.className = 'wf-node-status failed';
        errorMark.innerHTML = '✗';
        node.appendChild(errorMark);
    }
    
    // Also update connector before this node
    const prevSibling = node.previousElementSibling;
    if (prevSibling && prevSibling.classList.contains('wf-connector')) {
        prevSibling.classList.remove('active', 'completed');
        if (status === 'running') {
            prevSibling.classList.add('active');
        } else if (status === 'completed') {
            prevSibling.classList.add('completed');
        }
    }
}

// Initialize
function init() {
    // Set default prompt
    promptInput.value = 'Please extract the data from this invoice.';
    
    // Event listeners
    invoiceInput.addEventListener('change', handleFileSelect);
    removeImageBtn.addEventListener('click', removeImage);
    startBtn.addEventListener('click', startWorkflow);
    restartBtn.addEventListener('click', restart);
    followupBtn.addEventListener('click', sendFollowup);
    
    // Allow Enter to send follow-up (Shift+Enter for new line)
    followupInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendFollowup();
        }
    });
    
    // Console clear button
    if (consoleClearBtn) {
        consoleClearBtn.addEventListener('click', clearConsole);
    }
}

// Handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        selectedFile = file;
        
        // Extract invoice key from filename (without extension)
        const filenameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
        selectedInvoiceData = WORKFLOW_INVOICES_DEMO[filenameWithoutExt] || null;
        
        if (selectedInvoiceData) {
            console.log(`Selected invoice data for: ${filenameWithoutExt}`, selectedInvoiceData);
        } else {
            console.warn(`No demo invoice data found for filename: ${filenameWithoutExt}`);
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            uploadLabel.classList.add('hidden');
            imagePreview.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }
}

// Remove selected image
function removeImage() {
    selectedFile = null;
    selectedInvoiceData = null;
    invoiceInput.value = '';
    previewImg.src = '';
    imagePreview.classList.add('hidden');
    uploadLabel.classList.remove('hidden');
}

// Start workflow
async function startWorkflow() {
    const prompt = promptInput.value.trim();
    if (!prompt) {
        alert('Please enter a prompt');
        return;
    }

    // Disable start button
    startBtn.disabled = true;
    
    // Switch to workflow view
    inputSection.classList.add('hidden');
    workflowSection.classList.remove('hidden');
    resultSection.classList.add('hidden');
    
    // Reset state
    eventsContainer.innerHTML = '';
    finalText = '';
    actorContainers = {};
    totalAgentCount = 0;
    workflowStatus.textContent = 'Running';
    workflowStatus.className = 'status-badge running';
    
    // Update console status
    updateConsoleStatus('Running');
    clearConsole();
    
    // Render the workflow diagram
    try {
        console.log('About to call renderWorkflowDiagram');
        renderWorkflowDiagram();
        console.log('renderWorkflowDiagram completed');
    } catch (e) {
        console.error('Error calling renderWorkflowDiagram:', e);
    }

    
    // Prepare form data
    const formData = new FormData();
    
    // Determine message: use selected invoice data if available, otherwise fall back to demo or prompt
    let message;
    if (selectedInvoiceData && WORKFLOW_PROMPT_DEMO_USE) {
        message = JSON.stringify(selectedInvoiceData, null, 2);
    } else {
        message = prompt;
    }
    
    formData.append('message', message);
    formData.append('workflow_name', WORKFLOW_NAME);
    formData.append('workflow_version', '1');
    if (selectedFile) {
        formData.append('invoice', selectedFile);
    }

    try {
        // Use fetch with streaming
        const response = await fetch(`${API_BASE_URL}/workflow/run`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            
            // Process complete SSE messages
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // Keep incomplete message in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    try {
                        const event = JSON.parse(jsonStr);
                        handleEvent(event);
                    } catch (e) {
                        console.error('Failed to parse event:', e);
                    }
                }
            }
        }

        // Show result
        showResult();
    } catch (error) {
        console.error('Workflow error:', error);
        addGlobalEvent({
            type: 'error',
            data: { error: error.message },
        });
        workflowStatus.textContent = 'Failed';
        workflowStatus.className = 'status-badge failed';
    }
}

// Handle incoming event
function handleEvent(event) {
    const { type, data, timestamp } = event;
    const actionId = data?.action_id;
    
    console.log('Event:', type, 'action_id:', actionId, 'data:', data);
    
    // Log ALL events to console (no filtering)
    logToConsole(event);
    
    // Capture conversation_id from response_created event
    if (type === 'response_created' && data.conversation_id) {
        currentConversationId = data.conversation_id;
        console.log('Conversation ID captured:', currentConversationId);
    }
    
    // Keep only the last text from text_done events
    if (type === 'text_done' && data.text) {
        finalText = data.text;
    }
    
    // Update diagram node status
    if (type === 'actor_started' && actionId) {
        updateDiagramNodeStatus(actionId, 'running');
    } else if (type === 'actor_completed' && actionId) {
        updateDiagramNodeStatus(actionId, data.status === 'failed' ? 'failed' : 'completed');
    }
    
    // Update status on completion/failure
    if (type === 'workflow_completed') {
        workflowStatus.textContent = 'Completed';
        workflowStatus.className = 'status-badge completed';
        updateConsoleStatus('Completed');
        // Mark any remaining running actors as completed
        markAllActorsCompleted();
        markDiagramNodes('completed');
    } else if (type === 'workflow_failed' || type === 'error') {
        workflowStatus.textContent = 'Failed';
        workflowStatus.className = 'status-badge failed';
        updateConsoleStatus('Failed');
        // Mark any remaining running actors as failed
        markAllActorsFailed();
        markDiagramNodes('failed');
    }
    
    // Skip text_delta events (too noisy)
    if (type === 'text_delta') {
        return;
    }
    
    // Skip these event types from UI display (only logged in console above)
    const uiSkipEvents = [
        'response_created',
        'response_in_progress',
        'response_completed',
        'workflow_completed',
        'workflow_started'
    ];
    if (uiSkipEvents.includes(type)) {
        return;
    }
    
    // Determine if this is an actor-scoped event or global event
    if (type === 'actor_started') {
        // Create new actor container
        createActorContainer(data.action_id);
    } else if (type === 'actor_completed') {
        // Mark actor as completed
        completeActorContainer(data.action_id, data.status);
    } else if (actionId && actorContainers[actionId]) {
        // Add to existing actor container
        console.log('Adding to actor container:', actionId);
        addActorEvent(actionId, event);
    } else {
        // Skip rendering events that are not scoped to an actor container
        return;
    }
}

// Mark all running actors as completed (called when workflow finishes)
function markAllActorsCompleted() {
    Object.keys(actorContainers).forEach(actionId => {
        const container = actorContainers[actionId];
        if (container && !container.classList.contains('completed')) {
            completeActorContainer(actionId, 'completed');
        }
    });
}

// Mark all running actors as failed (called when workflow fails)
function markAllActorsFailed() {
    Object.keys(actorContainers).forEach(actionId => {
        const container = actorContainers[actionId];
        if (container && !container.classList.contains('completed')) {
            completeActorContainer(actionId, 'failed');
        }
    });
}

// Mark any pending diagram nodes with a final status
function markDiagramNodes(status) {
    Object.values(diagramNodes).forEach(node => {
        if (!node) return;
        const isActive = node.classList.contains('active');
        const isFinished = node.classList.contains('completed') || node.classList.contains('failed');
        if (!isActive || isFinished) return;
        const actionId = node.dataset.actionId;
        if (actionId) {
            updateDiagramNodeStatus(actionId, status);
        }
    });
}

// Create a new actor container
function createActorContainer(actionId) {
    console.log('Creating actor container for:', actionId);
    
    // Filter out actors that start with "action-"
    if (actionId && actionId.startsWith('action-')) {
        console.log('Skipping actor display (filtered):', actionId);
        return;
    }

    // Reuse existing container to preserve history across turns
    if (actorContainers[actionId]) {
        const container = actorContainers[actionId];
        const statusEl = container.querySelector('.actor-status');
        if (statusEl) {
            statusEl.className = 'actor-status running';
            statusEl.innerHTML = '<span class="spinner"></span>\n                Running';
        }
        container.classList.remove('completed');
        setActorCollapsed(actionId, false);
        return;
    }
    
    const container = document.createElement('div');
    container.className = 'actor-container';
    container.id = `actor-${actionId}`;
    
    // Increment total agent count and use for naming
    totalAgentCount++;
    const actorName = `${actionId}`;
    
    container.innerHTML = `
        <div class="actor-header">
            <div class="actor-icon">🤖</div>
            <div class="actor-title">
                <span class="actor-name">${actorName}</span>
                <span class="actor-id">agent-${totalAgentCount}</span>
            </div>
            <div class="actor-status running">
                <span class="spinner"></span>
                Running
            </div>
            <button class="actor-toggle" type="button" aria-label="Toggle actor details" aria-expanded="true">
                <span class="actor-toggle-icon">▾</span>
            </button>
        </div>
        <div class="actor-events"></div>
    `;
    
    eventsContainer.appendChild(container);
    actorContainers[actionId] = container;

    const toggleBtn = container.querySelector('.actor-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleActorCollapse(actionId);
        });
    }
    
    console.log('Actor container created, total containers:', Object.keys(actorContainers).length);
    
    // Scroll to bottom
    eventsContainer.scrollTop = eventsContainer.scrollHeight;
}

function toggleActorCollapse(actionId) {
    const container = actorContainers[actionId];
    if (!container) return;
    const collapsed = container.classList.contains('collapsed');
    setActorCollapsed(actionId, !collapsed);
}

function setActorCollapsed(actionId, collapsed) {
    const container = actorContainers[actionId];
    if (!container) return;
    container.classList.toggle('collapsed', collapsed);
    const eventsDiv = container.querySelector('.actor-events');
    if (eventsDiv) {
        eventsDiv.style.display = collapsed ? 'none' : 'flex';
    }
    const icon = container.querySelector('.actor-toggle-icon');
    const toggleBtn = container.querySelector('.actor-toggle');
    if (toggleBtn) {
        toggleBtn.setAttribute('aria-expanded', (!collapsed).toString());
    }
    if (icon) {
        icon.textContent = collapsed ? '▸' : '▾';
    }
}

// Add event to actor container
function addActorEvent(actionId, event) {
    const container = actorContainers[actionId];
    if (!container) return;

    if (container.classList.contains('collapsed') && !container.classList.contains('completed')) {
        setActorCollapsed(actionId, false);
    }
    
    const eventsDiv = container.querySelector('.actor-events');
    const { type, data, timestamp } = event;
    const config = eventIcons[type] || { icon: '•', class: 'response', label: type };
    
    // Build message based on event type
    let message = buildEventMessage(type, data);
    if (!message) return; // Skip if no message
    
    const eventEl = document.createElement('div');
    eventEl.className = 'actor-event';
    
    eventEl.innerHTML = `
        <div class="event-icon-small ${config.class}">${config.icon}</div>
        <div class="event-content">
            <span class="event-label">${config.label}:</span>
            <span class="event-text">${escapeHtml(message)}</span>
        </div>
    `;
    
    eventsDiv.appendChild(eventEl);
    
    // Scroll to bottom
    eventsContainer.scrollTop = eventsContainer.scrollHeight;
}

// Complete actor container
function completeActorContainer(actionId, status) {
    const container = actorContainers[actionId];
    if (!container) return;
    
    const statusEl = container.querySelector('.actor-status');
    statusEl.className = `actor-status ${status === 'completed' ? 'completed' : 'failed'}`;
    statusEl.innerHTML = status === 'completed' ? '✓ Done' : '✗ Failed';
    
    setActorCollapsed(actionId, true);
    container.classList.add('completed');
}

// Add global event (not scoped to an actor)
function addGlobalEvent(event) {
    const { type, data, timestamp } = event;
    const config = eventIcons[type] || { icon: '•', class: 'response', label: type };
    
    // Build message based on event type
    let message = buildEventMessage(type, data);
    if (!message) return;
    
    // Create event element
    const eventEl = document.createElement('div');
    eventEl.className = 'event-item global-event';
    
    const time = timestamp ? new Date(timestamp).toLocaleTimeString() : '';
    
    eventEl.innerHTML = `
        <div class="event-icon ${config.class}">${config.icon}</div>
        <div class="event-content">
            <div class="event-type">${config.label}</div>
            <div class="event-message">${escapeHtml(message)}</div>
        </div>
        <div class="event-time">${time}</div>
    `;
    
    eventsContainer.appendChild(eventEl);
    eventsContainer.scrollTop = eventsContainer.scrollHeight;
}

// Build event message
function buildEventMessage(type, data) {
    switch (type) {
        case 'workflow_started':
            return `Starting workflow: ${data.workflow_name} v${data.workflow_version}`;
        case 'workflow_completed':
            return 'Workflow finished successfully';
        case 'workflow_failed':
            return `Error: ${data.error || 'Unknown error'}`;
        case 'response_created':
            return data.conversation_id ? `Conversation: ${data.conversation_id.slice(0, 16)}...` : 'Response created';
        case 'response_in_progress':
            return `Status: ${data.status || 'processing'}`;
        case 'response_completed':
            if (data.total_tokens) {
                return `Tokens: ${data.total_tokens} (${data.input_tokens} in, ${data.output_tokens} out)`;
            }
            return 'Response completed';
        case 'reasoning_completed':
            return 'Processing...';
        case 'text_done':
            const text = data.text || '';
            return text.length > 150 ? text.slice(0, 150) + '...' : text;
        case 'message_completed':
            return data.status === 'started' ? 'Generating response...' : 'Response ready';
        case 'mcp_tools_listed':
            const tools = data.tools || [];
            return `${data.server_label || 'Server'}: ${tools.length} tools available`;
        case 'mcp_call_in_progress':
            return 'Calling tool...';
        case 'mcp_call_completed':
            return 'Tool call completed';
        case 'mcp_call_failed':
            return 'Tool call failed';
        case 'error':
            return data.error || 'An error occurred';
        default:
            return null;
    }
}

// Add a visual separator for follow-up messages
function addFollowupSeparator(message) {
    const separator = document.createElement('div');
    separator.className = 'followup-separator';
    separator.innerHTML = `
        <div class="separator-line"></div>
        <div class="separator-content">
            <span class="separator-icon">💬</span>
            <span class="separator-text">Follow-up: ${escapeHtml(message.length > 50 ? message.slice(0, 50) + '...' : message)}</span>
        </div>
        <div class="separator-line"></div>
    `;
    eventsContainer.appendChild(separator);
    eventsContainer.scrollTop = eventsContainer.scrollHeight;
}

// Show final result
function showResult() {
    resultSection.classList.remove('hidden');
    const text = finalText.trim() || 'No text output received.';
    
    // Get or create question buttons container
    let questionBtnsContainer = document.getElementById('question-buttons');
    const followupContainer = document.querySelector('.followup-container');
    
    // Get or create final result container
    let finalResultContainer = document.getElementById('final-result-container');
    if (!finalResultContainer) {
        finalResultContainer = document.createElement('div');
        finalResultContainer.id = 'final-result-container';
        finalResultContainer.className = 'final-result-container hidden';
        finalResultContainer.innerHTML = `
            <div class="final-result-icon">✅</div>
            <div class="final-result-text"></div>
            <div class="final-result-badge">Workflow Complete</div>
        `;
        // Insert before the followup container
        followupContainer.parentNode.insertBefore(finalResultContainer, followupContainer);
    }
    
    if (!questionBtnsContainer) {
        // Create the question buttons container (initially hidden)
        questionBtnsContainer = document.createElement('div');
        questionBtnsContainer.id = 'question-buttons';
        questionBtnsContainer.className = 'question-buttons-container hidden';
        questionBtnsContainer.innerHTML = `
            <button class="question-btn yes-btn" data-value="yes">✓ Yes</button>
            <button class="question-btn no-btn" data-value="no">✗ No</button>
        `;
        // Insert before the followup container
        followupContainer.parentNode.insertBefore(questionBtnsContainer, followupContainer);
        
        // Add event listeners for the buttons
        questionBtnsContainer.querySelectorAll('.question-btn').forEach(btn => {
            btn.addEventListener('click', () => handleQuestionResponse(btn.dataset.value));
        });
    }
    
    // Check if the text starts with <FINAL> - end of workflow
    if (text.startsWith('<FINAL>')) {
        // Extract the final text (remove the tag)
        const finalText = text.replace('<FINAL>', '').trim();
        resultContent.textContent = '';
        
        // Update and show the final result container
        finalResultContainer.querySelector('.final-result-text').textContent = finalText || 'Workflow completed successfully!';
        finalResultContainer.classList.remove('hidden');
        
        // Hide question buttons and follow-up textarea
        questionBtnsContainer.classList.add('hidden');
        followupContainer.classList.add('hidden');
    }
    // Check if the text starts with <QUESTION>
    else if (text.startsWith('<QUESTION>')) {
        // Extract the question text (remove the tag)
        const questionText = text.replace('<QUESTION>', '').trim();
        resultContent.textContent = questionText || 'Please respond:';
        
        // Show question buttons, hide follow-up textarea and final container
        questionBtnsContainer.classList.remove('hidden');
        followupContainer.classList.add('hidden');
        finalResultContainer.classList.add('hidden');
    } else {
        // Normal text - show textarea, hide question buttons and final container
        resultContent.textContent = text;
        questionBtnsContainer.classList.add('hidden');
        followupContainer.classList.remove('hidden');
        finalResultContainer.classList.add('hidden');
        
        // Clear and focus follow-up input
        followupInput.value = '';
        followupInput.focus();
    }
    
    // Show conversation badge if we have a conversation ID
    if (currentConversationId) {
        conversationBadge.textContent = `Conversation: ${currentConversationId.slice(0, 12)}...`;
        conversationBadge.classList.remove('hidden');
    }
}

// Handle yes/no question response
async function handleQuestionResponse(value) {
    if (!currentConversationId) {
        alert('No active conversation. Please start a new workflow.');
        return;
    }
    
    // Disable buttons while processing
    const questionBtnsContainer = document.getElementById('question-buttons');
    const buttons = questionBtnsContainer.querySelectorAll('.question-btn');
    buttons.forEach(btn => btn.disabled = true);
    
    // Switch to workflow view, keep result visible
    workflowSection.classList.remove('hidden');
    
    // Add separator for the response
    addFollowupSeparator(`Response: ${value}`);
    
    // Reset text accumulator for this turn; keep previous actor state visible
    finalText = '';
    workflowStatus.textContent = 'Running';
    workflowStatus.className = 'status-badge running';
    
    // Prepare form data with conversation_id
    const formData = new FormData();
    formData.append('message', value);
    formData.append('workflow_name', WORKFLOW_NAME);
    formData.append('workflow_version', '1');
    formData.append('conversation_id', currentConversationId);
    
    try {
        const response = await fetch(`${API_BASE_URL}/workflow/run`, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    try {
                        const event = JSON.parse(jsonStr);
                        handleEvent(event);
                    } catch (e) {
                        console.error('Failed to parse event:', e);
                    }
                }
            }
        }
        
        // Show updated result
        showResult();
    } catch (error) {
        console.error('Question response error:', error);
        addGlobalEvent({
            type: 'error',
            data: { error: error.message },
        });
        workflowStatus.textContent = 'Failed';
        workflowStatus.className = 'status-badge failed';
    } finally {
        buttons.forEach(btn => btn.disabled = false);
    }
}

// Send follow-up message
async function sendFollowup() {
    const message = followupInput.value.trim();
    if (!message) {
        return;
    }
    if (!currentConversationId) {
        alert('No active conversation. Please start a new workflow.');
        return;
    }
    
    // Disable follow-up while processing
    followupBtn.disabled = true;
    followupInput.disabled = true;
    
    // Switch to workflow view, keep result visible
    workflowSection.classList.remove('hidden');
    
    // Add separator for follow-up (keep previous events)
    addFollowupSeparator(message);
    
    // Reset text accumulator for this turn; keep previous actor state visible
    finalText = '';
    workflowStatus.textContent = 'Running';
    workflowStatus.className = 'status-badge running';
    
    // Prepare form data with conversation_id
    const formData = new FormData();
    formData.append('message', message);
    formData.append('workflow_name', WORKFLOW_NAME);
    formData.append('workflow_version', '1');
    formData.append('conversation_id', currentConversationId);
    
    try {
        const response = await fetch(`${API_BASE_URL}/workflow/run`, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    try {
                        const event = JSON.parse(jsonStr);
                        handleEvent(event);
                    } catch (e) {
                        console.error('Failed to parse event:', e);
                    }
                }
            }
        }
        
        // Show updated result
        showResult();
    } catch (error) {
        console.error('Follow-up error:', error);
        addGlobalEvent({
            type: 'error',
            data: { error: error.message },
        });
        workflowStatus.textContent = 'Failed';
        workflowStatus.className = 'status-badge failed';
    } finally {
        followupBtn.disabled = false;
        followupInput.disabled = false;
    }
}

// Restart workflow
function restart() {
    // Reset UI
    inputSection.classList.remove('hidden');
    workflowSection.classList.add('hidden');
    resultSection.classList.add('hidden');
    
    // Reset state
    startBtn.disabled = false;
    eventsContainer.innerHTML = '';
    resultContent.textContent = '';
    finalText = '';
    actorContainers = {};
    totalAgentCount = 0;
    currentConversationId = null;
    diagramNodes = {};
    
    // Clear diagram
    const diagramContainer = workflowDiagram.querySelector('.diagram-container');
    if (diagramContainer) {
        diagramContainer.innerHTML = '';
    }
    
    // Hide conversation badge
    conversationBadge.classList.add('hidden');
    
    // Reset console
    updateConsoleStatus('Ready');
    clearConsole();
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Console logging functions
function getConsoleEventClass(type) {
    if (type.startsWith('workflow')) return 'console-workflow';
    if (type.startsWith('actor')) return 'console-actor';
    if (type.startsWith('response')) return 'console-response';
    if (type.startsWith('text')) return 'console-text-event';
    if (type.startsWith('mcp')) return 'console-mcp';
    if (type.startsWith('reasoning')) return 'console-reasoning';
    if (type === 'error') return 'console-error';
    if (type.startsWith('message')) return 'console-response';
    return 'console-info';
}

function getConsolePrefix(type) {
    const prefixes = {
        workflow_started: '[WF:START]',
        workflow_completed: '[WF:DONE]',
        workflow_failed: '[WF:FAIL]',
        response_created: '[RSP:NEW]',
        response_in_progress: '[RSP:RUN]',
        response_completed: '[RSP:DONE]',
        response_failed: '[RSP:FAIL]',
        actor_started: '[AGENT:▶]',
        actor_completed: '[AGENT:✓]',
        text_delta: '[TXT:Δ]',
        text_done: '[TXT:DONE]',
        message_completed: '[MSG:DONE]',
        mcp_tools_listed: '[MCP:LIST]',
        mcp_call_in_progress: '[MCP:CALL]',
        mcp_call_completed: '[MCP:DONE]',
        mcp_call_failed: '[MCP:FAIL]',
        reasoning_completed: '[THINK]',
        error: '[ERROR]',
    };
    return prefixes[type] || `[${type.toUpperCase()}]`;
}

function getConsoleMessage(type, data) {
    switch (type) {
        case 'workflow_started':
            return `Workflow "${data.workflow_name}" v${data.workflow_version} started`;
        case 'workflow_completed':
            return 'Workflow completed successfully';
        case 'workflow_failed':
            return `Workflow failed: ${data.error || 'Unknown error'}`;
        case 'response_created':
            return `New response created${data.conversation_id ? ` (conv: ${data.conversation_id.slice(0, 8)}...)` : ''}`;
        case 'response_in_progress':
            return `Response processing: ${data.status || 'in progress'}`;
        case 'response_completed':
            return data.total_tokens ? `Response done (${data.total_tokens} tokens)` : 'Response completed';
        case 'actor_started':
            return `Agent started: ${data.action_id}`;
        case 'actor_completed':
            return `Agent finished: ${data.action_id} (${data.status})`;
        case 'text_delta':
            const delta = data.text || '';
            return delta.length > 60 ? delta.slice(0, 60) + '...' : delta;
        case 'text_done':
            const text = data.text || '';
            return text.length > 80 ? text.slice(0, 80) + '...' : text;
        case 'message_completed':
            return `Message ${data.status || 'completed'}`;
        case 'mcp_tools_listed':
            return `${data.server_label || 'Server'}: ${(data.tools || []).length} tools available`;
        case 'mcp_call_in_progress':
            return `Calling tool: ${data.tool_name || 'unknown'}`;
        case 'mcp_call_completed':
            return `Tool call completed: ${data.tool_name || ''}`;
        case 'mcp_call_failed':
            return `Tool call failed: ${data.error || 'unknown error'}`;
        case 'reasoning_completed':
            return 'Reasoning/thinking completed';
        case 'error':
            return data.error || 'An error occurred';
        default:
            return JSON.stringify(data).slice(0, 100);
    }
}

function logToConsole(event) {
    if (!consoleOutput) return;
    
    const { type, data, timestamp } = event;
    
    // Filter out text_delta events (too noisy even for console)
    if (type === 'text_delta') return;
    const actionId = data?.action_id;
    
    const line = document.createElement('div');
    line.className = `console-line console-new ${getConsoleEventClass(type)}`;
    
    // Format timestamp
    const time = timestamp ? new Date(timestamp).toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    }) : '';
    
    const message = getConsoleMessage(type, data);
    const actionIdHtml = actionId ? `<span class="console-action-id">[${actionId}]</span>` : '';
    
    line.innerHTML = `
        <span class="console-timestamp">${time}</span>
        <span class="console-prefix">${getConsolePrefix(type)}</span>
        <span class="console-text">${escapeHtml(message)}${actionIdHtml}</span>
    `;
    
    consoleOutput.appendChild(line);
    
    // Auto-scroll to bottom
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
    
    // Remove animation class after animation completes
    setTimeout(() => {
        line.classList.remove('console-new');
    }, 300);
}

function clearConsole() {
    if (!consoleOutput) return;
    consoleOutput.innerHTML = `
        <div class="console-line console-info">
            <span class="console-prefix">[INFO]</span>
            <span class="console-text">Console cleared. Waiting for events...</span>
        </div>
    `;
}

function updateConsoleStatus(status) {
    if (!consoleStatus) return;
    consoleStatus.textContent = status;
    consoleStatus.className = 'console-status' + (status === 'Running' ? ' running' : '');
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    init();
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
});
