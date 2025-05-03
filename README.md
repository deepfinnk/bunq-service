# Deepfinnk Bunq Agent Server

This project implements a Flask-based Multi-Agent Collaboration Platform (MCP) server designed to interact with the Bunq API using the CAMEL AI framework.

## Features

*   **Flask API Server:** Provides HTTP endpoints for interaction.
*   **CAMEL AI Integration:** Utilizes the `OwlRolePlaying` paradigm for agentic task execution.
*   **Bunq API Integration:** Includes tools and endpoints to interact with Bunq accounts, payments, etc. (requires Bunq SDK setup).
*   **Swagger UI:** Automatically generated API documentation accessible via the `/apidocs` endpoint.
*   **Dependency Management:** Uses `uv` for fast dependency resolution and environment management.
*   **Docker Support:** Includes `Dockerfile` and `compose.yaml` for containerized deployment.

## Prerequisites

*   Python 3.12+
*   [uv](https://github.com/astral-sh/uv)
*   Docker & Docker Compose (Optional, for containerized deployment)
*   Bunq API Key and configuration (See Setup)

## Setup

1.  **Clone the repository:**
    ```sh
    git clone <repository-url>
    cd mcp-server
    ```

2.  **Configure Environment Variables:**
    *   Copy the example environment file (if one exists) or create a `.env` file:
        ```sh
        cp .env.example .env # Or create manually
        ```
    *   Edit the `.env` file and add your Bunq API credentials and any other required settings (e.g., `BUNQ_API_KEY`, `BUNQ_ENVIRONMENT`).

3.  **Install Dependencies:**
    *   Create a virtual environment:
        ```sh
        uv venv
        ```
    *   Activate the environment:
        ```sh
        source .venv/bin/activate
        ```
    *   Sync dependencies:
        ```sh
        uv sync
        ```

## Running Locally

1.  Ensure your `.env` file is correctly configured.
2.  Activate the virtual environment (`source .venv/bin/activate`).
3.  Run the Flask development server:
    ```sh
    uv run python service.py
    ```
    Alternatively, you can use the Flask CLI:
    ```sh
    uv run flask --app service run --port 42069
    ```

The server will start, typically listening on `http://0.0.0.0:42069`.

## Running with Docker

1.  Ensure Docker Desktop or Docker Engine is running.
2.  Ensure your `.env` file is correctly configured in the project root (Docker Compose should automatically pick it up).
3.  Build and start the container:
    ```sh
    docker compose up --build
    ```
    To run in detached mode:
    ```sh
    docker compose up --build -d
    ```

The server will be accessible at `http://localhost:42069`.

## API Documentation

Once the server is running (either locally or via Docker), you can access the Swagger UI for interactive API documentation in your browser:

[http://localhost:42069/apidocs](http://localhost:42069/apidocs)

This interface details all available endpoints, parameters, and expected responses.

## Configuration

*   **Environment Variables:** Core configuration like API keys and environment type (Sandbox/Production) is managed via the `.env` file.
*   **Agent Configuration:** Specific agent or MCP settings might be configured in `mcp_servers_config.json`.
