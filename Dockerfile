FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY tunnel_client/ ./tunnel_client/

# Create directories for frpc config (shared volume)
RUN mkdir -p /etc/frp

# Expose web UI port
EXPOSE 3000

# Run the application
CMD ["python", "-m", "tunnel_client.main", "--host", "0.0.0.0", "--port", "3000"]
