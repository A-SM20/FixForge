# FixForge Sandbox Image
# Minimal image with Python, ripgrep, git, and common test runners
#
# Design decision: Pre-built image with tools pre-installed so
# container startup is fast (no apt-get during each run).

FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ripgrep \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install common Python test runners and tools
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-xdist \
    tox \
    coverage

# Set up a non-root user for security
RUN useradd --create-home --shell /bin/bash sandbox
USER sandbox

WORKDIR /workspace

# Default command — keep the container alive for exec_run calls
CMD ["sleep", "infinity"]
