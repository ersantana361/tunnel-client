FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY proxy.py .

# Default environment variables
ENV PROXY_PORT=8080
ENV TARGETS_FILE=/etc/frp/tunnel_targets.json
ENV CREDENTIALS_FILE=/etc/frp/credentials.json
ENV METRICS_BUFFER_SIZE=100
ENV METRICS_FLUSH_INTERVAL=30

EXPOSE 8080

CMD ["python", "proxy.py"]
