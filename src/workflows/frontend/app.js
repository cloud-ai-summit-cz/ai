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
    - kind: SetVariable
      id: action-1764883765010
      variable: Local.InvoiceOK
      value: =false
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
            - kind: SetVariable
              id: action-1764883750258
              variable: Local.InvoiceOK
              value: =true
            - kind: InvokeAzureAgent
              id: invoice-process-summary-agent
              agent:
                name: invoice-process-summary-agent
              input:
                messages: =System.LastMessage
              output:
                autoSend: true
          id: if-action-1764883723763-0
      id: action-1764883723763
      elseActions:
        - kind: SendActivity
          activity: Vypada to spatne...
          id: action-1764884732691
        - kind: Question
          variable: Local.InvoiceKOUser
          id: action-1764885497445
          entity: StringPrebuiltEntity
          skipQuestionMode: SkipOnFirstExecutionIfVariableHasValue
          prompt: OK?
        - kind: SetVariable
          id: action-1764883918865
          variable: Local.InvoiceOK
          value: =false
        - kind: SendActivity
          activity: The Invoice is wrong! {Local.InvoiceKOUser}
          id: action-1764884001355
id: ""
name: wf2
description: ""

`;
const WORKFLOW_PROMPT_DEMO_USE = true
const WORKFLOW_PROMPT_DEMO = `
    {
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
}
    `;

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

// State
let selectedFile = null;
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

// Simple YAML parser for the workflow structure
// For reliability, we'll use a pre-parsed structure that matches WORKFLOW_YAML
function getWorkflowStructure() {
    return {
        name: 'wf2',
        trigger: {
            kind: 'OnConversationStart',
            id: 'trigger_wf',
            actions: [
                {
                    kind: 'SetVariable',
                    id: 'action-1764883765010',
                    variable: 'Local.InvoiceOK',
                    value: '=false'
                },
                {
                    kind: 'InvokeAzureAgent',
                    id: 'invoice-validation-agent',
                    agentName: 'invoice-validation-agent'
                },
                {
                    kind: 'ConditionGroup',
                    id: 'action-1764883723763',
                    condition: '=!IsBlank(Find("<INV_OK>", Last(Local.LastMessage).Text))',
                    conditions: [
                        {
                            id: 'if-action-1764883723763-0',
                            condition: '=!IsBlank(Find("<INV_OK>", Last(Local.LastMessage).Text))',
                            actions: [
                                {
                                    kind: 'SetVariable',
                                    id: 'action-1764883750258',
                                    variable: 'Local.InvoiceOK',
                                    value: '=true'
                                },
                                {
                                    kind: 'InvokeAzureAgent',
                                    id: 'invoice-process-summary-agent',
                                    agentName: 'invoice-process-summary-agent'
                                }
                            ]
                        }
                    ],
                    elseActions: [
                        {
                            kind: 'SendActivity',
                            id: 'action-1764884732691',
                            activity: 'Vypada to spatne...'
                        },
                        {
                            kind: 'Question',
                            id: 'action-1764885497445',
                            prompt: 'OK?'
                        },
                        {
                            kind: 'SetVariable',
                            id: 'action-1764883918865',
                            variable: 'Local.InvoiceOK',
                            value: '=false'
                        },
                        {
                            kind: 'SendActivity',
                            id: 'action-1764884001355',
                            activity: 'The Invoice is wrong!'
                        }
                    ]
                }
            ]
        }
    };
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
        
        // Create main row for: Start -> SetVariable -> Agent -> Condition
        const mainRow = document.createElement('div');
        mainRow.className = 'diagram-row';
        
        // Add Start node
        const startNode = createNodeElement({ kind: 'OnConversationStart', id: 'trigger_wf' }, true);
        console.log('6. Start node created:', startNode.outerHTML.substring(0, 100));
        mainRow.appendChild(startNode);
        mainRow.appendChild(createConnector());
        
        // Add SetVariable node
        if (actions[0]) {
            mainRow.appendChild(createNodeElement(actions[0]));
            mainRow.appendChild(createConnector());
        }
        
        // Add Agent node  
        if (actions[1]) {
            mainRow.appendChild(createNodeElement(actions[1]));
            mainRow.appendChild(createConnector());
        }
        
        // Add Condition node
        const conditionAction = actions[2];
        if (conditionAction) {
            mainRow.appendChild(createNodeElement(conditionAction));
        }
        
        console.log('7. Main row children:', mainRow.children.length);
        container.appendChild(mainRow);
        
        // Create IF branch row
        if (conditionAction && conditionAction.conditions && conditionAction.conditions[0]) {
            const ifRow = document.createElement('div');
            ifRow.className = 'diagram-branch-row';
            ifRow.appendChild(createConditionLabel('if'));
            
            const ifActions = conditionAction.conditions[0].actions || [];
            ifActions.forEach((action, idx) => {
                if (idx > 0) ifRow.appendChild(createConnector());
                ifRow.appendChild(createNodeElement(action));
            });
            container.appendChild(ifRow);
            console.log('8. IF row added, children:', ifRow.children.length);
        }
        
        // Create ELSE branch row
        if (conditionAction && conditionAction.elseActions) {
            const elseRow = document.createElement('div');
            elseRow.className = 'diagram-branch-row';
            elseRow.appendChild(createConditionLabel('else'));
            
            const elseActions = conditionAction.elseActions;
            elseActions.forEach((action, idx) => {
                if (idx > 0) elseRow.appendChild(createConnector());
                elseRow.appendChild(createNodeElement(action));
            });
            container.appendChild(elseRow);
            console.log('9. ELSE row added, children:', elseRow.children.length);
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
}

// Handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        selectedFile = file;
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
    formData.append('message', WORKFLOW_PROMPT_DEMO_USE ? WORKFLOW_PROMPT_DEMO : prompt);
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
        // Mark any remaining running actors as completed
        markAllActorsCompleted();
    } else if (type === 'workflow_failed' || type === 'error') {
        workflowStatus.textContent = 'Failed';
        workflowStatus.className = 'status-badge failed';
        // Mark any remaining running actors as failed
        markAllActorsFailed();
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
        // Global event (workflow lifecycle, response events without action_id)
        addGlobalEvent(event);
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

// Create a new actor container
function createActorContainer(actionId) {
    console.log('Creating actor container for:', actionId);
    
    // Filter out actors that start with "action-"
    if (actionId && actionId.startsWith('action-')) {
        console.log('Skipping actor display (filtered):', actionId);
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
        </div>
        <div class="actor-events"></div>
    `;
    
    eventsContainer.appendChild(container);
    actorContainers[actionId] = container;
    
    console.log('Actor container created, total containers:', Object.keys(actorContainers).length);
    
    // Scroll to bottom
    eventsContainer.scrollTop = eventsContainer.scrollHeight;
}

// Add event to actor container
function addActorEvent(actionId, event) {
    const container = actorContainers[actionId];
    if (!container) return;
    
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
    resultContent.textContent = finalText.trim() || 'No text output received.';
    
    // Show conversation badge if we have a conversation ID
    if (currentConversationId) {
        conversationBadge.textContent = `Conversation: ${currentConversationId.slice(0, 12)}...`;
        conversationBadge.classList.remove('hidden');
    }
    
    // Clear and focus follow-up input
    followupInput.value = '';
    followupInput.focus();
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
    
    // Reset only text accumulator and actorContainers (keep totalAgentCount)
    finalText = '';
    actorContainers = {};
    workflowStatus.textContent = 'Running';
    workflowStatus.className = 'status-badge running';
    
    // Re-render diagram and reset node states
    renderWorkflowDiagram();
    
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
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', init);
