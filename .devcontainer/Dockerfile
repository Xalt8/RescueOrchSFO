FROM node:20-bookworm

# System deps
RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    curl \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Python aliases
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create vscode user correctly
RUN useradd -m -s /bin/bash vscode && \
    echo "vscode ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode && \
    chmod 0440 /etc/sudoers.d/vscode

# Devcontainers expects this path
WORKDIR /workspaces/spot-x-2

# Ensure home ownership
RUN mkdir -p /home/vscode/.local/bin && \
    chown -R vscode:vscode /home/vscode

# Switch user
USER vscode

# Correct way to set PATH
ENV PATH="/home/vscode/.local/bin:${PATH}"
