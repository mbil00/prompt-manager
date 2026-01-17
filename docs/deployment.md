# Remote Deployment Guide

This guide covers deploying Prompt Manager API on a remote server (VPS, Raspberry Pi, home server) so multiple clients can share the same prompt database.

## Quick Start with Docker Compose

The fastest way to deploy:

```bash
# Clone the repository
git clone https://github.com/yourusername/prompt-manager.git
cd prompt-manager

# Set your API key
export PM_API_KEY=$(openssl rand -hex 32)
echo "PM_API_KEY=$PM_API_KEY" > .env

# Start the server
docker compose up -d

# Check status
docker compose logs -f
```

The API will be available at `http://your-server:8000`.

## Deployment Options

### Option 1: Docker Compose with SQLite (Recommended)

SQLite is the default and works well for personal use.

```bash
# Create .env file with your settings
cat > .env << EOF
PM_API_KEY=$(openssl rand -hex 32)
PM_LOG_LEVEL=INFO
EOF

# Start services
docker compose up -d

# View logs
docker compose logs -f api

# Stop services
docker compose down

# Stop and remove data
docker compose down -v
```

### Option 2: Docker Compose with PostgreSQL

For larger deployments or when you need PostgreSQL features:

```bash
# Create .env file
cat > .env << EOF
PM_API_KEY=$(openssl rand -hex 32)
POSTGRES_USER=pmuser
POSTGRES_PASSWORD=$(openssl rand -hex 16)
POSTGRES_DB=prompts
PM_LOG_LEVEL=INFO
EOF

# Start with PostgreSQL compose file
docker compose -f docker-compose.postgres.yml up -d

# View logs
docker compose -f docker-compose.postgres.yml logs -f
```

### Option 3: Docker Compose with nginx + SSL

For production deployments with HTTPS:

```bash
# Create .env file
cat > .env << EOF
PM_API_KEY=$(openssl rand -hex 32)
PM_LOG_LEVEL=INFO
SSL_CERT_DIR=/path/to/your/certs
EOF

# Your certificate directory should contain:
# - fullchain.pem (certificate + intermediates)
# - privkey.pem (private key)

# Start with nginx compose file
docker compose -f docker-compose.nginx.yml up -d

# View logs
docker compose -f docker-compose.nginx.yml logs -f
```

**Using Let's Encrypt certificates:**

```bash
# If using certbot, certificates are typically at:
SSL_CERT_DIR=/etc/letsencrypt/live/yourdomain.com

# Or copy them to a local directory:
mkdir -p ./certs
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./certs/
sudo chown $USER:$USER ./certs/*.pem
```

**Self-signed certificates for testing:**

```bash
mkdir -p ./certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./certs/privkey.pem \
  -out ./certs/fullchain.pem \
  -subj "/CN=localhost"
```

The API will be available at `https://your-server`.

### Option 4: Direct Docker/Podman Commands

Without Docker Compose:

```bash
# Build the image
docker build -t prompt-manager .

# Create a volume for data persistence
docker volume create pm_data

# Run the container
docker run -d \
  --name prompt-manager \
  -p 8000:8000 \
  -v pm_data:/data \
  -e PM_API_KEY=your-secret-key \
  -e PM_ALLOW_LOCALHOST_BYPASS=false \
  --restart unless-stopped \
  prompt-manager

# View logs
docker logs -f prompt-manager

# Stop
docker stop prompt-manager

# Remove
docker rm prompt-manager
```

**Podman users:** Add `:Z` suffix to volumes on SELinux systems:

```bash
podman run -d \
  --name prompt-manager \
  -p 8000:8000 \
  -v pm_data:/data:Z \
  -e PM_API_KEY=your-secret-key \
  -e PM_ALLOW_LOCALHOST_BYPASS=false \
  --restart unless-stopped \
  prompt-manager
```

### Option 5: Direct Python Installation

For systems without container support:

```bash
# Install Python 3.11+
sudo apt install python3.11 python3.11-venv

# Create application directory
sudo mkdir -p /opt/prompt-manager
sudo chown $USER:$USER /opt/prompt-manager
cd /opt/prompt-manager

# Clone and setup
git clone https://github.com/yourusername/prompt-manager.git .
python3.11 -m venv venv
source venv/bin/activate
pip install -e .

# For PostgreSQL support
pip install -e ".[postgres]"

# Create data directory
mkdir -p /var/lib/prompt-manager

# Create systemd service
sudo tee /etc/systemd/system/prompt-manager.service << EOF
[Unit]
Description=Prompt Manager API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/prompt-manager
Environment="PM_API_KEY=your-secret-key"
Environment="PM_DATABASE_URL=sqlite+aiosqlite:///var/lib/prompt-manager/prompts.db"
Environment="PM_ALLOW_LOCALHOST_BYPASS=false"
ExecStart=/opt/prompt-manager/venv/bin/pm serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable prompt-manager
sudo systemctl start prompt-manager

# Check status
sudo systemctl status prompt-manager
sudo journalctl -u prompt-manager -f
```

## Client Configuration

After deploying the server, configure your local CLI to connect.

### Setting the API URL

```bash
# For direct Docker deployment (no SSL)
pm config set api-url http://your-server:8000

# For nginx + SSL deployment
pm config set api-url https://your-server
```

### Setting the API Key

The API key on your client must match `PM_API_KEY` on the server.

```bash
# Set your API key
pm config set api-key your-secret-key

# Verify current configuration
pm config show
```

To find your server's API key:

```bash
# On the server, check the .env file
cat .env | grep PM_API_KEY
```

### Generating a New API Key

If you need to generate a new API key:

```bash
# Generate a secure random key
openssl rand -hex 32

# Update server .env file
echo "PM_API_KEY=your-new-key" > .env

# Restart the server
docker compose restart

# Update your client
pm config set api-key your-new-key
```

### Testing the Connection

```bash
# List prompts (should work if configured correctly)
pm list

# Check API health directly
curl -H "X-API-Key: your-key" http://your-server:8000/api/v1/prompts
```

### Configuration File Location

Client configuration is stored at `~/.config/prompt-manager/config.toml`. You can also edit it directly:

```bash
cat ~/.config/prompt-manager/config.toml
```

## Backup and Restore

### SQLite Backup

```bash
# Backup (container must be running)
docker exec prompt-manager sqlite3 /data/prompts.db ".backup /data/backup.db"
docker cp prompt-manager:/data/backup.db ./prompts-backup.db

# Or stop container and copy directly
docker compose stop
docker cp prompt-manager:/data/prompts.db ./prompts-backup.db
docker compose start

# Restore
docker cp ./prompts-backup.db prompt-manager:/data/prompts.db
docker compose restart
```

### PostgreSQL Backup

```bash
# Backup
docker exec prompt-manager-db pg_dump -U pmuser prompts > backup.sql

# Restore
docker exec -i prompt-manager-db psql -U pmuser prompts < backup.sql
```

### Automated Backups

Create a cron job for regular backups:

```bash
# Add to crontab (crontab -e)
0 2 * * * docker exec prompt-manager sqlite3 /data/prompts.db ".backup /data/backup-$(date +\%Y\%m\%d).db"
```

## Security Considerations

### 1. Use HTTPS (Required for Production)

Use a reverse proxy like Caddy, nginx, or Traefik:

**Caddy (automatic HTTPS):**

```bash
# Install Caddy
sudo apt install caddy

# Configure /etc/caddy/Caddyfile
prompts.yourdomain.com {
    reverse_proxy localhost:8000
}

# Restart Caddy
sudo systemctl restart caddy
```

**nginx:**

```nginx
server {
    listen 443 ssl http2;
    server_name prompts.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/prompts.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/prompts.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Strong API Key

Generate a secure API key:

```bash
openssl rand -hex 32
```

### 3. Firewall Configuration

Only expose necessary ports:

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (for HTTPS redirect)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Do NOT expose port 8000 directly - use reverse proxy
```

### 4. Keep Updated

Regularly update the container:

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

## Raspberry Pi Notes

Prompt Manager runs well on Raspberry Pi 3B+ or newer.

### Recommended Setup

1. Use Raspberry Pi OS Lite (64-bit)
2. SQLite is recommended (lower resource usage)
3. Consider using an SSD for better database performance

### Docker on Raspberry Pi

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Log out and back in, then:
docker compose up -d
```

### Memory Considerations

If memory is limited, you can constrain the container:

```yaml
# In docker-compose.yml, add under api service:
services:
  api:
    # ... other settings ...
    deploy:
      resources:
        limits:
          memory: 256M
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs api

# Common issues:
# - Port 8000 already in use: change port in docker-compose.yml
# - Permission issues: check volume permissions
```

### Database connection errors

```bash
# Check database file exists (SQLite)
docker exec prompt-manager ls -la /data/

# Check PostgreSQL is healthy
docker compose -f docker-compose.postgres.yml ps
```

### Client can't connect

```bash
# Test from server
curl http://localhost:8000/health

# Test authentication
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/prompts

# Check firewall
sudo ufw status

# Check API key matches
pm config show
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PM_API_KEY` | `dev-secret-key` | API authentication key |
| `PM_DATABASE_URL` | `sqlite+aiosqlite:////data/prompts.db` | Database connection URL |
| `PM_HOST` | `0.0.0.0` | API bind address |
| `PM_PORT` | `8000` | API port |
| `PM_ALLOW_LOCALHOST_BYPASS` | `false` (container) | Skip auth for localhost |
| `PM_LOG_LEVEL` | `INFO` | Logging verbosity |
