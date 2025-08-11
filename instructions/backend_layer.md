Of course. Here is a comprehensive and detailed design plan for the "Lekh" backend, structured for a coding agent. This plan synthesizes all our previous discussions into a cohesive architectural blueprint.

---

### **Project: "Lekh" Backend Design Plan**

**Objective:** To create a robust, scalable backend service for the "Lekh" story generation platform. The backend will serve a RESTful API, manage real-time updates via WebSockets, and orchestrate a complex AI agent workflow for story creation.

**Core Technologies:**
*   **Language/Framework:** Python 3.11+ with FastAPI
*   **AI Orchestration:** LangGraph
*   **Task Queuing:** Celery with Redis as the message broker
*   **Authentication:** Supabase Auth (Cloud)
*   **Session Database:** Supabase Postgres (Cloud)
*   **Knowledge Graph:** Neo4j AuraDB (Cloud)

---

### **1. Directory Structure**

The coding agent should generate the following file and directory structure within the `backend/` folder.

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # FastAPI dependencies (e.g., get_current_user)
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   └── stories.py        # Routes for /stories
│   │   └── api.py              # Main API router
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic settings model to load .env variables
│   │   └── security.py         # JWT validation logic against Supabase
│   ├── db/
│   │   ├── __init__.py
│   │   └── supabase_handler.py # Functions to interact with Supabase tables
│   ├── services/
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Celery application instance definition
│   │   └── story_runner.py     # Celery task definition for running the agent
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── callback.py         # LangGraph CallbackHandler for Redis Pub/Sub
│   │   └── manager.py          # WebSocket connection manager with Redis Pub/Sub
│   ├── __init__.py
│   └── main.py                 # FastAPI application entrypoint
├── agent/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── architect.py
│   │   ├── character_smith.py
│   │   └── prose_weaver.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── knowledge_graph.py    # Tools for Neo4j interaction
│   │   └── user_interaction.py
│   ├── __init__.py
│   ├── graph.py                  # LangGraph State and Graph definition
│   └── state.py                  # Pydantic models for agent state
├── pyproject.toml
└── Dockerfile
```

---

### **2. Environment Variables & Configuration (`.env` and `app/core/config.py`)**

1.  **`.env` file:** Create a template `.env` file for all necessary secrets.
    ```env
    # Supabase Credentials
    SUPABASE_URL="https://<your-project-ref>.supabase.co"
    SUPABASE_ANON_KEY="<your-anon-key>"
    SUPABASE_SERVICE_ROLE_KEY="<your-service-role-key>"
    SUPABASE_JWT_SECRET="<your-jwt-secret-from-supabase-dashboard>"

    # Neo4j Aura Credentials
    NEO4J_URI="neo4j+s://<your-instance-id>.databases.neo4j.io"
    NEO4J_USER="neo4j"
    NEO4J_PASSWORD="<your-generated-password>"

    # Redis (e.g., from Upstash or other cloud provider)
    CELERY_BROKER_URL="redis://:<password>@<host>:<port>"
    CELERY_RESULT_BACKEND="redis://:<password>@<host>:<port>"

    # OpenAI/LLM Provider
    OPENAI_API_KEY="sk-..."
    ```

2.  **`app/core/config.py`:** Use Pydantic's `BaseSettings` to load these environment variables into a typed `Settings` object. This provides validation and autocompletion.

---

### **3. Supabase Schema (Session Database)**

The agent needs to know the SQL schema for the Supabase Postgres database.

**Table: `story_sessions`**
*   **Purpose:** Stores metadata and the workflow control state for each story.
*   **Columns:**
    *   `id` (UUID, Primary Key, default: `uuid_generate_v4()`)
    *   `owner_id` (UUID, Foreign Key to `auth.users(id)`, not nullable)
    *   `title` (TEXT, not nullable)
    *   `initial_prompt` (TEXT)
    *   `genres` (ARRAY of TEXT)
    *   `control_state` (JSONB, not nullable) - Stores the lightweight workflow state (`system_status`, `agent_question`, etc.)
    *   `created_at` (TIMESTAMPTZ, default: `now()`)
    *   `updated_at` (TIMESTAMPTZ, default: `now()`)

**Row-Level Security (RLS) Policies:**
*   Enable RLS on the `story_sessions` table.
*   Create a policy that allows a user to `SELECT`, `INSERT`, `UPDATE`, and `DELETE` rows only where `owner_id` matches their own authenticated `auth.uid()`.

---

### **4. Authentication Flow (`app/core/security.py` & `app/api/deps.py`)**

1.  **`security.py`:** Implement a function `validate_supabase_jwt(token: str) -> dict`. This function will use the `PyJWT` library to decode the JWT provided by the frontend. It must verify the signature using the `SUPABASE_JWT_SECRET`. On success, it returns the decoded token payload (which includes `sub` for user ID). On failure, it raises an `HTTPException`.

2.  **`deps.py`:** Create a FastAPI dependency `get_current_user`.
    *   It will extract the JWT from the `Authorization: Bearer <token>` header.
    *   It will call `validate_supabase_jwt` to validate the token.
    *   It will return the decoded token payload, which can then be used in the endpoint functions.

---

### **5. API Endpoints (`app/api/endpoints/stories.py`)**

All endpoints must be protected by the `get_current_user` dependency.

*   **`GET /api/stories`**
    *   **Action:** Fetches all stories for the authenticated user.
    *   **Logic:**
        1.  Get `user_id` from the dependency.
        2.  Call a function in `supabase_handler.py` to `SELECT id, title, updated_at FROM story_sessions WHERE owner_id = :user_id`.
        3.  Return the list of stories.

*   **`POST /api/stories`**
    *   **Action:** Creates a new story.
    *   **Request Body:** Pydantic model with `prompt: str` and `genres: list[str]`.
    *   **Logic:**
        1.  Get `user_id`.
        2.  Create an initial `control_state` JSON object (e.g., `{"system_status": "INITIALIZING"}`).
        3.  Call a function in `supabase_handler.py` to `INSERT` a new row into `story_sessions` with the provided data and the user's `owner_id`.
        4.  Retrieve the `id` of the newly created story.
        5.  Trigger the Celery task: `run_story_generation_task.delay(story_id=new_story_id)`.
        6.  Return the new `story_id` and title.

*   **`DELETE /api/stories`**
    *   **Action:** Deletes one or more stories.
    *   **Request Body:** A list of `story_id`s.
    *   **Logic:**
        1.  For each `story_id` in the list:
            a.  Verify ownership by checking `owner_id` in Supabase. If mismatch, raise 403.
            b.  Call a function in `agent/tools/knowledge_graph.py` to delete all nodes associated with this `story_id` from Neo4j.
            c.  Call a function in `supabase_handler.py` to delete the story record from the `story_sessions` table.
        2.  Return a success message.

*   **`WS /ws/stories/{story_id}` (Defined in `app/main.py`)**
    *   **Action:** Establishes a WebSocket connection for real-time updates for a specific story.
    *   **Logic:**
        1.  Authenticate the user via a token passed in the query parameters or initial message.
        2.  Verify the user has access to the given `story_id`.
        3.  Use the `WebSocketManager` from `app/websocket/manager.py` to handle the connection. The manager will subscribe to a Redis Pub/Sub channel named `story:{story_id}`.
        4.  It will listen for messages on that channel and forward them to the connected client.

---

### **6. AI Agent & Celery Task (`agent/` & `app/services/`)**

1.  **`app/services/celery_app.py`:** Define the `celery_app` instance, configuring it with the `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` from the settings.

2.  **`agent/graph.py`:** This is the core of the AI logic.
    *   Define the `AgentState` TypedDict.
    *   Define each agent function (`architect`, `prose_weaver`, etc.). These functions will take the `state` as input.
    *   Inside the agent functions, instantiate and use tools from `agent/tools/`. The tools should be classes that get initialized with the `story_id` so they know which data to act upon.
    *   Build the `StatefulGraph`. Define the nodes and conditional edges based on the `system_status` in the `AgentState`.
    *   Compile the graph and expose it via a function, e.g., `get_graph() -> CompiledGraph`.

3.  **`app/services/story_runner.py`:**
    *   Define the Celery task `run_story_generation_task(story_id: str)`.
    *   Inside the task:
        a.  Instantiate the `RedisStreamCallbackHandler` from `app/websocket/callback.py`, passing it the `story_id`. This handler's job is to `PUBLISH` agent steps to the Redis channel `story:{story_id}`.
        b.  Fetch the initial state for the story from Supabase.
        c.  Get the compiled `graph` from `agent.graph.get_graph()`.
        d.  Invoke the graph stream: `graph.stream(initial_state, config={"callbacks": [callback_handler]})`. This is a blocking call that will run until the agent's workflow is complete or paused.

4.  **`agent/tools/knowledge_graph.py`:**
    *   Create a `Neo4jTool` class.
    *   Its `__init__` method should connect to the Neo4j AuraDB using the credentials from `config.py`.
    *   Implement methods like `query(cypher_query: str)`, `add_character(story_id, name, details)`, `get_scene_context(story_id, scene_id)`. **Every query must be scoped with `MATCH (n {story_id: $story_id}) ...`**.

---

### **7. Dockerfile**

Excellent. Here is the detailed plan for the `Dockerfile` and `docker-compose.yml`, updated to reflect the move to cloud-managed databases and the integration of Celery.

---

**1. `Dockerfile` for the Backend (`backend/Dockerfile`)**

The goal of this `Dockerfile` is to create a single, efficient Docker image that contains all the Python code and dependencies. This one image will be used to run both the FastAPI web server and the Celery worker containers. Using `uv` and a multi-stage approach is key for performance and smaller image size.

```dockerfile
# Stage 1: Builder - Install dependencies
# We use a full python image here as it has build tools that might be needed
# by some python packages (e.g., for compiling C extensions).
FROM python:3.11 as builder

# Set working directory
WORKDIR /app

# Install uv, the fast package installer
RUN pip install uv

# Copy only the dependency file to leverage Docker layer caching
COPY pyproject.toml .

# Install dependencies into a virtual environment using uv
# This creates a self-contained environment in /app/.venv
RUN uv venv
RUN uv pip install --system .


# Stage 2: Final Image - Create the production-ready image
# We switch to a slim image to reduce the final image size.
FROM python:3.11-slim

# Set working directory
WORKDIR /code

# Copy the virtual environment with all dependencies from the builder stage
COPY --from=builder /usr/local/ /usr/local/

# Copy the application source code
COPY ./app /code/app
COPY ./agent /code/agent

# Expose the port that the FastAPI server will run on
EXPOSE 8000

# The default command is to start the web server.
# This will be used by the 'backend' service in docker-compose.
# The 'celery_worker' service will override this command.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Improvements in this Dockerfile:**
*   **Multi-Stage Build:** This separates the build environment from the final runtime environment, resulting in a smaller, more secure production image.
*   **`uv` for Speed:** Uses `uv` for significantly faster dependency installation during the build process.
*   **Layer Caching:** By copying `pyproject.toml` first and installing dependencies, Docker will only re-run this slow step if the dependencies change, not every time you change your application code.

---

**2. `docker-compose.yml` (Root Directory)**

This file orchestrates the local development environment. Since Supabase and Neo4j are now cloud services, they are no longer defined as services in this file. The primary role of this file is to run our application's backend services and a local Redis container for Celery.

```yaml
version: '3.8'

# This file defines the services that make up the Lekh application's backend.
# It is designed for local development and testing.
# Frontend, Supabase, and Neo4j are managed separately.

services:
  # The FastAPI Web Server
  # This container accepts API requests from the frontend.
  backend:
    container_name: lekh-backend-api
    # Uses the Dockerfile located in the ./backend directory to build the image
    build:
      context: ./backend
    # This service runs the default CMD from the Dockerfile (uvicorn)
    ports:
      - "8000:8000" # Maps port 8000 on the host to port 8000 in the container
    env_file:
      - .env # Loads all secrets and configuration from the .env file
    # The backend needs to connect to Redis to queue tasks.
    depends_on:
      - redis
    networks:
      - lekh-net

  # The Celery Worker
  # This container processes the long-running AI story generation tasks.
  celery_worker:
    container_name: lekh-backend-worker
    # CRITICAL: It uses the exact same image as the backend service.
    # This is efficient as it avoids building two separate images.
    build:
      context: ./backend
    # OVERRIDE COMMAND: Instead of starting a web server, this container starts a Celery worker.
    # It tells Celery to look for the 'celery_app' instance defined in 'app.services.celery_app'.
    command: ["celery", "-A", "app.services.celery_app", "worker", "--loglevel=info", "--pool=gevent"]
    env_file:
      - .env # The worker also needs all the same secrets (DB, LLM keys, etc.)
    # The worker depends on Redis to receive tasks.
    depends_on:
      - redis
    networks:
      - lekh-net
    # Optional: Deploy more workers for higher throughput
    # deploy:
    #   replicas: 2


  # Redis for Celery Task Queuing and WebSocket Pub/Sub
  # This is the only database/infra service we run locally now.
  redis:
    container_name: lekh-redis
    image: redis:7-alpine # Use a lightweight alpine-based Redis image
    ports:
      - "6379:6379" # Expose to host for optional debugging with a Redis client
    networks:
      - lekh-net

# Define the shared network for inter-container communication
networks:
  lekh-net:
    driver: bridge
```

#### **Instructions for the Coding Agent & Developer**

1.  **Create Cloud Accounts:** Before running `docker-compose up`, you must:
    *   Create a **Supabase** project and get your URL, anon key, service role key, and JWT secret.
    *   Create a **Neo4j AuraDB** Free instance and get your URI, user, and password.
    *   Create a **Cloud Redis** instance (e.g., from Upstash's free tier) and get your full connection URL.

2.  **Populate `.env` File:** Create a `.env` file in the project root and fill it with all the credentials obtained in the step above.

3.  **Build and Run:**
    *   Navigate to the project root directory (`lekh/`).
    *   Run `docker-compose build`. This will build the single `lekh-backend` image using the new `Dockerfile`.
    *   Run `docker-compose up`. This will start three containers: `lekh-backend-api`, `lekh-backend-worker`, and `lekh-redis`.

**How it All Connects:**
*   The `backend` container will listen on `http://localhost:8000` for API calls from the frontend.
*   When a story is created, the `backend` container will place a task message into the `redis` container.
*   The `celery_worker` container, which is constantly listening to `redis`, will pick up the task and start executing the LangGraph agent logic.
*   During execution, the `celery_worker` will make outbound connections to the cloud Neo4j and Supabase services. It will also publish real-time updates back to `redis` on a specific channel.
*   The `backend` container, handling the WebSocket connection, will listen to that same Redis channel and forward messages to the user's browser.

This setup provides a clean, professional, and scalable architecture for local development while leveraging the power and convenience of managed cloud services for data persistence.

This detailed plan provides a clear, step-by-step blueprint for the coding agent, covering architecture, database schema, authentication, API design, and the AI orchestration workflow.