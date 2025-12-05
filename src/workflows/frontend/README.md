# Invoice Processing Workflow Frontend

Simple frontend for demonstrating the agentic invoice processing workflow.

## Features

- Upload invoice image
- Enter custom prompt
- Real-time event streaming display
- Final result view
- Dark mode UI (ChatGPT-like)

## Running

### Option 1: Python HTTP Server

```bash
cd src/workflows/frontend
python -m http.server 3000
```

### Option 2: Node.js (npx)

```bash
cd src/workflows/frontend
npx serve -p 3000
```

Then open http://localhost:3000

## Requirements

- Backend running at http://localhost:8000
- Start backend first:
  ```bash
  cd src/workflows/backend
  uv run python main.py
  ```

## Usage

1. Upload an invoice image (optional)
2. Enter or modify the prompt
3. Click "Start Workflow"
4. Watch events stream in real-time
5. View the final result
6. Click "Start Over" to try again
