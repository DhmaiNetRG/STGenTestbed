FROM python:3.12-slim

# Set working directory
WORKDIR /home/stgen

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    iproute2 \
    iptables \
    net-tools \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy entire project
COPY . /home/stgen/

# Create non-root user for development
RUN useradd -m -s /bin/bash stgen && \
    chown -R stgen:stgen /home/stgen

# Setup Python virtual environment
RUN python3 -m venv /home/stgen/myenv

# Activate venv and install Python dependencies
ENV PATH="/home/stgen/myenv/bin:$PATH"
RUN . /home/stgen/myenv/bin/activate && \
    pip install --upgrade pip && \
    pip install fastapi uvicorn websockets psutil pydantic python-multipart aiofiles

# Install frontend dependencies
WORKDIR /home/stgen/stgen-ui/frontend
RUN npm install --legacy-peer-deps

# Configure passwordless sudo for network emulation
RUN echo "stgen ALL=(ALL) NOPASSWD: /sbin/tc, /sbin/ip" > /etc/sudoers.d/stgen && \
    chmod 0440 /etc/sudoers.d/stgen

# Switch to stgen user
USER stgen

# Expose ports
EXPOSE 3000 8000

# Set working directory for startup
WORKDIR /home/stgen

# Start script
CMD ["bash", "-c", "cd /home/stgen/stgen-ui && ./start.sh"]
