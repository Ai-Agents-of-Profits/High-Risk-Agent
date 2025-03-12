# Comprehensive Deployment Guide for Autonomous Crypto Trading Agent
# Linux Server Deployment

This guide provides detailed instructions for deploying your Autonomous Crypto Trading Agent on a Linux server. It covers every step from initial server setup to application deployment, security measures, and ongoing maintenance.

## Table of Contents

1. [Server Preparation](#1-server-preparation)
   - [Server Requirements](#server-requirements)
   - [Setting Up a Linux Server](#setting-up-a-linux-server)
   - [Initial Server Security](#initial-server-security)

2. [Environment Setup](#2-environment-setup)
   - [Installing Required Packages](#installing-required-packages)
   - [Installing Docker and Docker Compose](#installing-docker-and-docker-compose)
   - [Docker Post-Installation Setup](#docker-post-installation-setup)

3. [Application Deployment](#3-application-deployment)
   - [Cloning the Repository](#cloning-the-repository)
   - [Setting Up Environment Variables](#setting-up-environment-variables)
   - [Creating Docker Compose Configuration](#creating-docker-compose-configuration)
   - [Updating the MCP Configuration](#updating-the-mcp-configuration)
   - [Building and Starting the Containers](#building-and-starting-the-containers)

4. [Web Server and Domain Configuration](#4-web-server-and-domain-configuration)
   - [Installing and Configuring Nginx](#installing-and-configuring-nginx)
   - [Setting Up SSL with Certbot](#setting-up-ssl-with-certbot)
   - [Domain Configuration](#domain-configuration)

5. [Security Considerations](#5-security-considerations)
   - [Firewall Configuration](#firewall-configuration)
   - [Secure API Key Management](#secure-api-key-management)
   - [Regular Security Updates](#regular-security-updates)

6. [Monitoring and Maintenance](#6-monitoring-and-maintenance)
   - [Setting Up Container Monitoring](#setting-up-container-monitoring)
   - [Log Management](#log-management)
   - [Backup Strategy](#backup-strategy)
   - [Automated Updates](#automated-updates)

7. [Troubleshooting](#7-troubleshooting)
   - [Common Issues and Solutions](#common-issues-and-solutions)
   - [Debugging Steps](#debugging-steps)

---

## 1. Server Preparation

### Server Requirements

For optimal performance, your server should meet the following specifications:

- **CPU**: 2+ cores (4 recommended)
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 25GB SSD (minimum)
- **Network**: Stable connection with low latency to Binance servers
- **Operating System**: Ubuntu 22.04 LTS (recommended)

### Setting Up a Linux Server

These instructions are for Ubuntu 22.04 LTS, but can be adapted for other distributions.

1. **Access your server** via SSH:

```bash
ssh username@your_server_ip
```

2. **Update your system**:

```bash
sudo apt update && sudo apt upgrade -y
```

3. **Set the correct timezone** for accurate trading timestamps:

```bash
sudo timedatectl set-timezone UTC
```

You can confirm the timezone with:

```bash
timedatectl
```

### Initial Server Security

1. **Create a non-root user** with sudo privileges:

```bash
sudo adduser trading
sudo usermod -aG sudo trading
```

2. **Set up SSH key authentication** (on your local machine):

```bash
# Generate key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy key to server
ssh-copy-id trading@your_server_ip
```

3. **Disable password authentication** for SSH:

```bash
sudo nano /etc/ssh/sshd_config
```

Find and modify these lines:
```
PasswordAuthentication no
PermitRootLogin no
```

Restart SSH service:
```bash
sudo systemctl restart sshd
```

4. **Set up a basic firewall**:

```bash
sudo apt install ufw
sudo ufw allow OpenSSH
sudo ufw enable
```

## 2. Environment Setup

### Installing Required Packages

```bash
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    nano \
    htop
```

### Installing Docker and Docker Compose

1. **Install Docker**:

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
```

2. **Verify Docker installation**:

```bash
sudo docker run hello-world
```

3. **Install Docker Compose**:

```bash
sudo curl -L "https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

4. **Verify Docker Compose installation**:

```bash
docker-compose --version
```

### Docker Post-Installation Setup

Allow your user to run Docker commands without sudo:

```bash
sudo usermod -aG docker ${USER}
```

Log out and back in for this to take effect, or run:

```bash
su - ${USER}
```

## 3. Application Deployment

### Cloning the Repository

1. **Clone the repository**:

```bash
git clone https://github.com/Ai-Agents-of-Profits/High-Risk-Agent.git
cd High-Risk-Agent
```

### Setting Up Environment Variables

1. **Create an environment file**:

```bash
nano .env
```

2. **Add the following variables**:

```
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key

# Binance API Credentials
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key

# Application Settings
FLASK_ENV=production
FLASK_APP=app.py
```

3. **Set proper permissions** for the .env file:

```bash
chmod 600 .env
```

### Creating Docker Compose Configuration

Create a docker-compose.yml file:

```bash
nano docker-compose.yml
```

Add the following content:

```yaml
version: '3'

services:
  crypto-mcp:
    build:
      context: .
      dockerfile: crypto-mcp.Dockerfile
    restart: always
    ports:
      - "127.0.0.1:8081:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - crypto_mcp_data:/app/data
    networks:
      - trading_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
  
  binance-futures-mcp:
    build:
      context: .
      dockerfile: binance-futures-mcp.Dockerfile
    restart: always
    ports:
      - "127.0.0.1:8082:8000"
    environment:
      - BINANCE_API_KEY=${BINANCE_API_KEY}
      - BINANCE_SECRET_KEY=${BINANCE_SECRET_KEY}
    volumes:
      - binance_mcp_data:/app/data
    networks:
      - trading_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
  
  web-app:
    build:
      context: .
    restart: always
    ports:
      - "127.0.0.1:5000:5000"
    depends_on:
      - crypto-mcp
      - binance-futures-mcp
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FLASK_ENV=production
      - FLASK_APP=app.py
    volumes:
      - app_data:/app/data
    networks:
      - trading_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  trading_network:
    driver: bridge

volumes:
  crypto_mcp_data:
  binance_mcp_data:
  app_data:
```

### Updating the MCP Configuration

The MCP configuration needs to be updated to use the internal Docker network names:

```bash
nano mcp_config.json
```

Update with these settings:

```json
{
  "mcp_servers": {
    "crypto": "http://crypto-mcp:8000",
    "binance-futures": "http://binance-futures-mcp:8000"
  }
}
```

### Building and Starting the Containers

1. **Build and start the containers**:

```bash
docker-compose up -d
```

2. **Check if containers are running**:

```bash
docker-compose ps
```

3. **View logs for troubleshooting**:

```bash
docker-compose logs -f
```

## 4. Web Server and Domain Configuration

### Installing and Configuring Nginx

1. **Install Nginx**:

```bash
sudo apt install -y nginx
```

2. **Create a Nginx configuration file**:

```bash
sudo nano /etc/nginx/sites-available/trading-agent
```

3. **Add the following configuration**:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Increase max request size if needed (for uploading data)
    client_max_body_size 10M;
    
    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
```

4. **Enable the site**:

```bash
sudo ln -s /etc/nginx/sites-available/trading-agent /etc/nginx/sites-enabled/
sudo nginx -t  # Test the configuration
sudo systemctl restart nginx
```

5. **Open HTTP and HTTPS ports in the firewall**:

```bash
sudo ufw allow 'Nginx Full'
```

### Setting Up SSL with Certbot

1. **Install Certbot**:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

2. **Obtain an SSL certificate**:

```bash
sudo certbot --nginx -d your-domain.com
```

Follow the prompts to complete the process.

3. **Verify auto-renewal**:

```bash
sudo systemctl status certbot.timer
```

### Domain Configuration

1. **Log in to your domain registrar** and update the DNS records:
   - Create an A record pointing to your server's IP address
   - Example: `A record: your-domain.com -> your-server-ip`

2. **Verify DNS propagation**:

```bash
dig +short your-domain.com
```

## 5. Security Considerations

### Firewall Configuration

Ensure your firewall only allows necessary traffic:

```bash
sudo ufw status
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw reload
```

### Secure API Key Management

1. **File permissions** for sensitive files:

```bash
chmod 600 .env
chmod 600 mcp_config.json
```

2. **Consider using Docker secrets** for production:

```bash
echo "your_binance_api_key" | docker secret create binance_api_key -
echo "your_binance_secret_key" | docker secret create binance_secret_key -
```

Then update your docker-compose.yml to use secrets instead of environment variables.

### Regular Security Updates

Set up automatic security updates:

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 6. Monitoring and Maintenance

### Setting Up Container Monitoring

1. **Basic Docker monitoring**:

```bash
docker stats
```

2. **Install cAdvisor** for more detailed monitoring:

```bash
docker run \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --volume=/dev/disk/:/dev/disk:ro \
  --publish=8080:8080 \
  --detach=true \
  --name=cadvisor \
  --restart=always \
  gcr.io/cadvisor/cadvisor:v0.47.0
```

Access it at: http://your-server-ip:8080

### Log Management

1. **View container logs**:

```bash
docker-compose logs -f
```

2. **Set up log rotation** for Docker:

```bash
sudo nano /etc/docker/daemon.json
```

Add the following:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:

```bash
sudo systemctl restart docker
```

### Backup Strategy

1. **Create a backup script**:

```bash
nano backup.sh
```

Add the following:

```bash
#!/bin/bash
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/home/trading/backups"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Back up volumes
echo "Backing up Docker volumes..."
docker run --rm \
  -v trading-agent_crypto_mcp_data:/source/crypto_mcp_data:ro \
  -v trading-agent_binance_mcp_data:/source/binance_mcp_data:ro \
  -v trading-agent_app_data:/source/app_data:ro \
  -v $BACKUP_DIR:/backup \
  ubuntu \
  tar czf /backup/volumes_$TIMESTAMP.tar.gz /source

# Back up configuration files
echo "Backing up configuration files..."
tar czf $BACKUP_DIR/configs_$TIMESTAMP.tar.gz \
  docker-compose.yml \
  .env \
  mcp_config.json

echo "Backup completed: $BACKUP_DIR/volumes_$TIMESTAMP.tar.gz and $BACKUP_DIR/configs_$TIMESTAMP.tar.gz"

# Remove backups older than 7 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

2. **Make it executable and set up a cron job**:

```bash
chmod +x backup.sh
crontab -e
```

Add a line to run it daily at 1 AM:

```
0 1 * * * /home/trading/High-Risk-Agent/backup.sh
```

### Automated Updates

Create a script to pull the latest code and update your deployment:

```bash
nano update.sh
```

Add the following:

```bash
#!/bin/bash
cd /home/trading/High-Risk-Agent

# Pull the latest changes
git pull

# Rebuild and restart containers
docker-compose down
docker-compose up -d --build

echo "Update completed at $(date)"
```

Make it executable:

```bash
chmod +x update.sh
```

Set a cronjob to check for updates weekly:

```
0 2 * * 0 /home/trading/High-Risk-Agent/update.sh
```

## 7. Troubleshooting

### Common Issues and Solutions

1. **Container fails to start**:

Check logs for error messages:
```bash
docker-compose logs [service_name]
```

2. **MCP services can't communicate**:

Verify network configuration:
```bash
docker network inspect trading_network
```

3. **Nginx shows 502 Bad Gateway**:

Check if the Flask app is running:
```bash
docker-compose ps
curl http://localhost:5000
```

Verify Nginx configuration:
```bash
sudo nginx -t
```

4. **API credentials issues**:

Verify the .env file has the correct credentials:
```bash
cat .env
```

Check if environment variables are being passed to containers:
```bash
docker-compose exec web-app env | grep BINANCE
```

### Debugging Steps

1. **Check container status**:

```bash
docker-compose ps
```

2. **Check application logs**:

```bash
docker-compose logs -f web-app
```

3. **Access container shell**:

```bash
docker-compose exec web-app bash
```

4. **Verify network connectivity between containers**:

```bash
docker-compose exec web-app ping crypto-mcp
docker-compose exec web-app curl http://crypto-mcp:8000/health
```

5. **Restart specific services**:

```bash
docker-compose restart web-app
```

6. **Rebuild containers after changes**:

```bash
docker-compose up -d --build
```

---

## Conclusion

Following this guide will help you successfully deploy your Autonomous Crypto Trading Agent on a Linux server. The setup ensures:

- Secure deployment with proper user permissions
- Containerization for isolation and scalability
- Proper web server configuration with SSL
- Monitoring and backup strategies

Remember to regularly check your trading agent's performance, monitor system resources, and keep everything updated for optimal operation.

For further assistance or updates to this guide, refer to the GitHub repository or contact the development team.
