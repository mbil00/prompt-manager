# Deploying with nginx + SSL

This guide covers deploying Prompt Manager behind nginx with HTTPS/SSL termination.

## Quick Start

```bash
# Set your API key and certificate path
cat > .env << EOF
PM_API_KEY=$(openssl rand -hex 32)
SSL_CERT_DIR=/path/to/your/certs
EOF

# Start services
docker compose -f docker-compose.nginx.yml up -d
```

Your API will be available at `https://your-server`.

## Client Configuration

After starting the server, configure your local CLI to connect:

```bash
# Set the remote API URL (use your domain or IP)
pm config set api-url https://prompts.example.com

# Set your API key (must match PM_API_KEY on server)
pm config set api-key your-secret-key

# Verify connection
pm list
```

To find your API key:
```bash
# On the server, check the .env file
cat .env | grep PM_API_KEY
```

## Certificate Setup

### Option 1: Let's Encrypt (Production)

If you have certbot configured:

```bash
# Certificates are typically at:
SSL_CERT_DIR=/etc/letsencrypt/live/yourdomain.com

# Or copy to a local directory:
mkdir -p ./certs
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./certs/
sudo chown $USER:$USER ./certs/*.pem

echo "SSL_CERT_DIR=./certs" >> .env
```

### Option 2: Self-Signed (Testing/Development)

```bash
mkdir -p ./certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./certs/privkey.pem \
  -out ./certs/fullchain.pem \
  -subj "/CN=localhost"

echo "SSL_CERT_DIR=./certs" >> .env
```

### Option 3: Existing Certificates

Ensure your certificate directory contains:
- `fullchain.pem` - Your certificate chain (certificate + intermediates)
- `privkey.pem` - Your private key

```bash
echo "SSL_CERT_DIR=/path/to/your/certs" >> .env
```

## Starting the Services

```bash
# Build and start
docker compose -f docker-compose.nginx.yml up -d

# View logs
docker compose -f docker-compose.nginx.yml logs -f

# View nginx logs only
docker compose -f docker-compose.nginx.yml logs -f nginx

# Stop services
docker compose -f docker-compose.nginx.yml down
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PM_API_KEY` | `changeme` | API authentication key |
| `SSL_CERT_DIR` | `./certs` | Path to SSL certificates |
| `PM_LOG_LEVEL` | `INFO` | API logging level |

### nginx Settings

The default nginx configuration (`nginx/nginx.conf`) includes:

- **HTTP to HTTPS redirect** - All HTTP traffic redirects to HTTPS
- **Large request body support** - `client_max_body_size 10M` for large prompts
- **Modern SSL settings** - TLS 1.2/1.3 with secure cipher suites
- **HSTS header** - Strict Transport Security enabled
- **Health check passthrough** - `/health` accessible over HTTP for load balancers

### Customizing nginx

To modify nginx settings, edit `nginx/nginx.conf`:

```bash
# Edit configuration
vim nginx/nginx.conf

# Reload nginx without downtime
docker compose -f docker-compose.nginx.yml exec nginx nginx -s reload
```

Common customizations:

```nginx
# Increase max body size for very large prompts
client_max_body_size 50M;

# Add rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
location / {
    limit_req zone=api burst=20 nodelay;
    # ... rest of config
}

# Custom server name
server_name prompts.example.com;
```

## Certificate Renewal

### Automatic Renewal with Let's Encrypt

If using certbot with systemd timer, certificates renew automatically. Reload nginx after renewal:

```bash
# Add to /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
#!/bin/bash
docker compose -f /path/to/prompt-manager/docker-compose.nginx.yml exec nginx nginx -s reload
```

### Manual Renewal

```bash
# Renew certificates
sudo certbot renew

# Copy new certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/*.pem ./certs/
sudo chown $USER:$USER ./certs/*.pem

# Reload nginx
docker compose -f docker-compose.nginx.yml exec nginx nginx -s reload
```

## Troubleshooting

### Check nginx configuration

```bash
docker compose -f docker-compose.nginx.yml exec nginx nginx -t
```

### Certificate issues

```bash
# Verify certificate files exist
ls -la ./certs/

# Check certificate details
openssl x509 -in ./certs/fullchain.pem -text -noout | head -20

# Test SSL connection
openssl s_client -connect localhost:443 -servername localhost
```

### Connection refused

```bash
# Check containers are running
docker compose -f docker-compose.nginx.yml ps

# Check nginx logs
docker compose -f docker-compose.nginx.yml logs nginx

# Check API health
docker compose -f docker-compose.nginx.yml exec api curl http://localhost:8000/health
```

### 502 Bad Gateway

The API container may not be ready:

```bash
# Check API logs
docker compose -f docker-compose.nginx.yml logs api

# Verify API is healthy
docker compose -f docker-compose.nginx.yml ps
```

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           Docker Network                │
Internet            │                                         │
    │               │  ┌─────────┐         ┌──────────────┐  │
    │  :80/:443     │  │  nginx  │  :8000  │  API Server  │  │
    └───────────────┼──│  (SSL)  │─────────│  (internal)  │  │
                    │  └─────────┘         └──────────────┘  │
                    │                             │          │
                    │                      ┌──────┴──────┐   │
                    │                      │   /data     │   │
                    │                      │  (volume)   │   │
                    │                      └─────────────┘   │
                    └─────────────────────────────────────────┘
```

- **nginx** - Handles SSL termination, serves on ports 80/443
- **API Server** - Only accessible within Docker network on port 8000
- **/data volume** - Persistent SQLite database storage
