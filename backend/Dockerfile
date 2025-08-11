# Stage 1: Builder - Install dependencies
FROM python:3.11 as builder

# Set working directory
WORKDIR /app

# Install uv, the fast package installer
RUN pip install uv

# Copy only the dependency file to leverage Docker layer caching
COPY pyproject.toml .

# Install dependencies into a virtual environment using uv
RUN uv venv
RUN uv pip install --system .

# Stage 2: Final Image - Create the production-ready image
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