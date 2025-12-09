# Arboris Novel - Project Context

## Project Overview

**Arboris Novel** is an AI-assisted long-form novel writing desktop application. It is designed for local use, offering a privacy-focused environment where all data is stored on the user's machine. The application facilitates a complete writing workflow, from initial concept generation to detailed chapter writing, powered by Large Language Models (LLMs).

### Core Technologies

*   **Backend:** Python (FastAPI, SQLAlchemy Async, Uvicorn)
*   **Frontend:** Python (PyQt6)
*   **Database:** SQLite (stored locally in `storage/`)
*   **AI/LLM:** OpenAI API compatible (supports GPT, Claude, Local Ollama, etc.)

## Architecture

The application uses a **Client-Server** architecture running locally:

*   **Backend (`backend/`):** A FastAPI server providing RESTful endpoints for novel management, LLM interaction, and data persistence.
    *   Runs on: `http://127.0.0.1:8123` (default)
*   **Frontend (`frontend/`):** A PyQt6 desktop GUI acting as the client, communicating with the backend via HTTP.

### Key Directories

*   `backend/`
    *   `app/`: Core backend logic (`api/`, `services/`, `models/`, `schemas/`).
    *   `prompts/`: Markdown templates for LLM interactions.
    *   `run_server.py`: Backend entry point.
*   `frontend/`
    *   `windows/`: Main application windows (e.g., `main_window.py`).
    *   `pages/`: Individual page views (e.g., `home_page.py`).
    *   `components/`: Reusable UI components (`dialogs.py`, `loading_spinner.py`).
    *   `themes/`: UI styling and theming logic.
    *   `api/`: HTTP client for backend communication.
    *   `main.py`: Frontend entry point.
*   `storage/`: Stores the SQLite database (`arboris.db`), vector store, and logs.
*   `run_app.py`: Root script to launch the application (backend + frontend).

## Building and Running

### Prerequisites

*   **OS:** Windows (win32)
*   **Python:** Version 3.10 or higher

### Starting the Application

**Recommended:**
Run the unified entry point script:
```bash
python run_app.py
```
*This script typically starts the backend in a background thread and the frontend in the main thread.*

**Manual Start:**

1.  **Backend:**
    ```bash
    cd backend
    # Install dependencies
    pip install -r requirements.txt
    # Run server
    python run_server.py
    ```

2.  **Frontend:**
    ```bash
    cd frontend
    # Install dependencies
    pip install -r requirements.txt
    # Run client
    python main.py
    ```

## Development Conventions

*   **Code Style:** Standard Python PEP 8.
*   **Async:** The backend uses `asyncio` heavily.
*   **Frontend Structure:** The frontend has been refactored from a monolithic `ui` folder into modular `components`, `pages`, and `windows`.
*   **Configuration:** LLM settings are managed via the GUI and stored in the local database.
*   **Logging:** Check `storage/` for application logs if issues arise.

## Key Features

*   **Local Privacy:** No external account required; data stays on your machine.
*   **AI Workflow:**
    1.  **Concept:** Chat with AI to brainstorm.
    2.  **Blueprint:** Generate world-building, characters, and outline.
    3.  **Writing:** Generate and review chapter content.
*   **Multi-Model Support:** Configurable endpoint for various LLM providers.
