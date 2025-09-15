# Python 3.11 base image with pip
FROM mcr.microsoft.com/devcontainers/python:3.11

# Install any OS dependencies here if needed
# RUN apt-get update && apt-get install -y <package-name>

# Set workdir
WORKDIR /workspace

# Copy requirements for pre-caching (optional, speeds up builds)
# COPY setup/requirements.txt /tmp/requirements.txt

# Install Python dependencies
# RUN pip install --upgrade pip \
#     && pip install -r /tmp/requirements.txt

USER vscode

# Default command
CMD ["sleep", "infinity"]
