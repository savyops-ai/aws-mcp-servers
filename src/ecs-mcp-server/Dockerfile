# Stage 1: Use Astral's uv base image with uv and uvx preinstalled
FROM ghcr.io/astral-sh/uv:latest AS uv

# Stage 2: Final minimal image
FROM python:3.11-slim

# Copy uv and uvx binaries from the uv image
COPY --from=uv /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy application source code
COPY . .

# Expose the port your client expects
EXPOSE 8000

# Start the application using uv
CMD ["uv", "--directory", "/app", "run", "awslabs/ecs_mcp_server/main.py", "--host", "0.0.0.0", "--port", "8000"]
