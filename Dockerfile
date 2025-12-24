FROM python:3.11-slim

WORKDIR /app

# Install frpc
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and install frpc
ARG FRP_VERSION=0.52.3
RUN curl -fsSL https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz | tar xz \
    && mv frp_${FRP_VERSION}_linux_amd64/frpc /usr/local/bin/ \
    && rm -rf frp_${FRP_VERSION}_linux_amd64

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY tunnels.example.yaml .

# Create directories for frpc config
RUN mkdir -p /etc/frp

# Expose web UI port
EXPOSE 3000

# Run the application
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "3000"]
