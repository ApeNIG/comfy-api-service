# Start from a compatible Python 3.11 image
FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Set the working directory for your project
WORKDIR /workspaces/comfy-api-service

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git make && rm -rf /var/lib/apt/lists/*

# Install Poetry for your project
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-root

# --- NEW: Clone and install ComfyUI ---
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /opt/ComfyUI
WORKDIR /opt/ComfyUI
# Install ComfyUI's dependencies (CPU version)
RUN pip install -r requirements.txt
# ------------------------------------

# Switch back to your project directory
WORKDIR /workspaces/comfy-api-service

# Copy the rest of your application code
COPY . .