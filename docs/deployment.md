# Deployment Guide for Remote VM

This guide covers deploying CellXGene Explorer on a remote VM (Ubuntu, CentOS, or similar Linux distributions).

## Prerequisites

- **Operating System**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **CPU**: Recommended 16 cores for production
- **RAM**: Minimum 8GB for testing, recommended 48GB+ for production (10 workers)
- **Disk Space**: 50GB+ (depending on dataset sizes)
- **Network**: Open ports 80 (HTTP) and optionally 443 (HTTPS)

## Step 1: Install Docker

### Ubuntu/Debian
```bash
# Update package index
sudo apt-get update

# Install dependencies
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

### CentOS/RHEL
```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group
sudo usermod -aG docker $USER
```

## Step 2: Transfer Application Files

### Option A: Git Clone (Recommended)
```bash
# Install git if not present
sudo apt-get install -y git  # Ubuntu/Debian
# or
sudo yum install -y git      # CentOS/RHEL

# Clone repository
cd /opt  # or your preferred location
git clone <repository-url> cellxgene_stack
cd cellxgene_stack
```

### Option B: SCP/SFTP Transfer
```bash
# From your local machine:
tar -czf cellxgene_stack.tar.gz cellxgene_stack/
scp cellxgene_stack.tar.gz user@remote-vm:/opt/

# On remote VM:
cd /opt
tar -xzf cellxgene_stack.tar.gz
cd cellxgene_stack
```

## Step 3: Configure Environment

1. Create the environment configuration:
```bash
cp .env.example .env
```

2. Edit `.env` with your settings:
```bash
nano .env  # or vim, emacs, etc.
```

### Critical Configuration for Remote VM

**Update these values for remote deployment:**

```bash
# Data Storage - Use absolute paths on VM
HOST_DATA_DIRECTORY=/opt/cellxgene_stack/data/datasets
HOST_LOG_DIRECTORY=/opt/cellxgene_stack/data/logs

# Service Ports - Change if 80 is in use
NGINX_PORT=80              # Main web interface port
LANDING_PAGE_PORT=8000     # Internal - usually doesn't need changing
CELLXGENE_PORT=5005        # Internal - usually doesn't need changing

# Resource Limits - Adjust based on your VM's RAM
# Production (16 cores, 48GB RAM):
CELLXGENE_WORKERS=10
CELLXGENE_MEMORY_PER_WORKER_GB=4

# Development/Testing configurations:
# CELLXGENE_WORKERS=2      # For 8GB RAM (lighter workload)
# CELLXGENE_WORKERS=5      # For 16GB RAM (moderate workload)

# Debug Settings - Keep false in production
LANDING_PAGE_DEBUG=false
LANDING_PAGE_LOG_LEVEL=INFO
```

### Private Datasets Configuration

To enable private dataset functionality with access control:

```bash
# Private datasets directory
HOST_PRIVATE_DATA_DIRECTORY=/opt/cellxgene_stack/data/private

# Admin panel authentication (REQUIRED - generate a secure random token)
ADMIN_TOKEN=your-secure-admin-token-here

# Flask session secret key (REQUIRED - generate a secure random string)
SECRET_KEY=your-secure-secret-key-here

# Base URL for shareable links (use your public domain)
BASE_URL=https://your-domain.com

# Email configuration for sending access codes and share links (optional)
SMTP_HOST=smtp.your-email-provider.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=noreply@your-domain.com
```

**Generate secure tokens:**
```bash
# Generate ADMIN_TOKEN
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Admin Panel Access:**
- URL: `https://your-domain.com/admin`
- Enter the `ADMIN_TOKEN` to authenticate
- Features: Grant email access, create shareable links, view statistics

### Memory Recommendations by VM Size

| VM RAM | CPU Cores | CELLXGENE_WORKERS | Memory per Worker | Max Concurrent Datasets |
|--------|-----------|-------------------|-------------------|------------------------|
| 8 GB   | 4         | 2                 | 2GB               | 2                      |
| 16 GB  | 8         | 4                 | 3GB               | 4                      |
| 32 GB  | 12        | 6                 | 4GB               | 6                      |
| 48 GB  | 16        | 10                | 4GB               | 10 (Production)        |
| 64 GB+ | 16+       | 12                | 4GB               | 12+                    |

## Step 4: Prepare Data Directory

```bash
# Create data directories
mkdir -p data/datasets data/logs

# Set proper permissions
chmod 755 data/datasets
chmod 755 data/logs

# Copy your h5ad datasets
# Example: scp from local machine
# scp *.h5ad user@remote-vm:/opt/cellxgene_stack/data/datasets/

# Or download directly on VM
# wget https://example.com/dataset.h5ad -P data/datasets/
```

### Dataset Requirements

Each dataset needs:
1. **H5AD file**: `dataset_name.h5ad` - AnnData format
2. **Metadata JSON**: `dataset_name.json` - Companion metadata file

Example metadata JSON (`dataset_name.json`):
```json
{
  "name": "PBMC 3k Dataset",
  "description": "3,000 PBMCs from 10x Genomics",
  "organism": "Homo sapiens",
  "tissue": "peripheral blood",
  "assay": "10x 3' v3",
  "cell_count": 3000,
  "gene_count": 32738,
  "publication": "https://doi.org/example",
  "doi": "10.1000/example"
}
```

## Step 5: Build and Deploy

### Development
```bash
# Build Docker images
docker compose build

# Start services in background (faster healthchecks for dev)
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f landing-page
```

### Production
```bash
# Build Docker images
docker compose build

# Start services with production overrides (longer healthcheck timeouts)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check service status
docker compose ps
```

**Note:** The production compose file (`docker-compose.prod.yml`) uses:
- Longer healthcheck intervals (30s vs 5s) to avoid false positives under load
- Longer start periods (40s vs 10s) for slower startup environments
- Log rotation to prevent disk fill

### Verify Deployment

1. **Check services are running:**
```bash
docker compose ps

# Expected output:
# NAME                     STATUS                 PORTS
# cellxgene-landing-page   Up (healthy)          0.0.0.0:8000->8000/tcp
# cellxgene-nginx          Up (healthy)          0.0.0.0:80->80/tcp
```

2. **Check health endpoints:**
```bash
curl http://localhost/api/health
# Should return: {"status": "healthy"}

curl http://localhost/api/datasets
# Should return JSON with your datasets
```

3. **Access from browser:**
   - Open `http://<your-vm-ip>` or `http://<your-domain>`
   - You should see the dataset catalog

## Step 6: Firewall Configuration

### Ubuntu (UFW)
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp  # If using HTTPS
sudo ufw reload
```

### CentOS (firewalld)
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https  # If using HTTPS
sudo firewall-cmd --reload
```

### Cloud Provider Firewalls
- **AWS**: Configure Security Group to allow inbound on port 80 (and 443)
- **GCP**: Configure Firewall Rules to allow tcp:80 (and tcp:443)
- **Azure**: Configure Network Security Group inbound rules
- **OpenNebula**: Configure security groups or network templates

## Step 7: Optional - Enable HTTPS

### Using Let's Encrypt (Certbot)

1. Install Certbot:
```bash
# Ubuntu/Debian
sudo apt-get install -y certbot python3-certbot-nginx

# CentOS
sudo yum install -y certbot python3-certbot-nginx
```

2. Stop nginx temporarily:
```bash
docker compose stop nginx
```

3. Get certificate:
```bash
sudo certbot certonly --standalone -d your-domain.com
```

4. Update nginx configuration to use certificates (see `services/nginx/nginx.conf`)

5. Restart services:
```bash
docker compose up -d
```

## Maintenance

### Viewing Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f landing-page

# Last 100 lines
docker compose logs --tail=100 landing-page
```

### Updating Application
```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose down
docker compose build
docker compose up -d
```

### Adding New Datasets
```bash
# 1. Copy h5ad and json files to data/datasets/
cp new_dataset.h5ad data/datasets/
cp new_dataset.json data/datasets/

# 2. Restart landing page to rescan
docker compose restart landing-page

# 3. Verify dataset appears
curl http://localhost/api/datasets | jq '.datasets[].id'
```

### Backup
```bash
# Backup datasets and logs
tar -czf cellxgene_backup_$(date +%Y%m%d).tar.gz data/

# Copy to remote location
scp cellxgene_backup_*.tar.gz backup-server:/backups/
```

### Monitoring
```bash
# Check resource usage
docker stats

# Check disk usage
du -sh data/datasets/*

# Check active containers
docker ps -a | grep cellxgene
```

## Troubleshooting

### Services Won't Start
```bash
# Check logs for errors
docker compose logs landing-page

# Common issues:
# 1. Port 80 already in use
#    Solution: Change NGINX_PORT in .env

# 2. Permission denied on data directory
#    Solution: sudo chmod 755 data/datasets

# 3. Out of memory
#    Solution: Reduce CELLXGENE_WORKERS in .env
```

### Can't Access from Browser
```bash
# 1. Check firewall
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-all  # CentOS

# 2. Check nginx is running
docker compose ps nginx

# 3. Check you're using correct IP/domain
curl http://localhost  # from VM
curl http://<vm-ip>    # from local machine
```

### Datasets Not Loading
```bash
# 1. Check dataset files exist
ls -lh data/datasets/

# 2. Check file permissions
ls -la data/datasets/*.h5ad

# 3. Check logs for validation errors
docker compose logs landing-page | grep ERROR

# 4. Validate h5ad file manually
docker compose exec landing-page python -c "import anndata; anndata.read_h5ad('/data/datasets/your_file.h5ad')"
```

### High Memory Usage
```bash
# Check container memory
docker stats --no-stream

# View active CellXGene containers
docker ps | grep cellxgene

# Stop old containers (auto-cleanup runs every 5 minutes)
docker stop $(docker ps -q --filter "name=cellxgene-")

# Or force cleanup now
docker compose exec landing-page python -c "
from src.services.container_manager import CellxgeneContainerManager
cm = CellxgeneContainerManager('/data/datasets', 'cellxgene_stack_cellxgene-network', '/data/datasets')
cm.cleanup_inactive(max_inactive_seconds=0)  # Remove all inactive
"
```

## Performance Tuning

### For Large Datasets (>10GB)
```bash
# Increase memory per worker
CELLXGENE_MEMORY_PER_WORKER_GB=4

# Increase timeout
CELLXGENE_TIMEOUT_SECONDS=600

# Increase nginx proxy timeout
NGINX_PROXY_READ_TIMEOUT=600s
```

### For Many Concurrent Users
```bash
# Production configuration (16 cores, 48GB RAM)
CELLXGENE_WORKERS=10
CELLXGENE_MEMORY_PER_WORKER_GB=4

# Each active dataset needs ~4GB RAM
# Plan for: (CELLXGENE_WORKERS × 4GB) + 8GB for system = 48GB total
```

## Security Best Practices

1. **Never expose Docker socket to containers in production** (only needed for dynamic spawning)
2. **Use read-only volume mounts** for dataset directories
3. **Keep Docker and packages updated**
4. **Use HTTPS in production** (Let's Encrypt is free)
5. **Restrict access with firewall rules** if needed
6. **Monitor logs regularly** for suspicious activity
7. **Set up log rotation** to prevent disk fill

## Support

For issues or questions:
1. Check logs: `docker compose logs`
2. Review troubleshooting guide above
3. Check GitHub issues
4. Contact system administrator

## Quick Reference Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart a service
docker compose restart landing-page

# View logs
docker compose logs -f

# Check status
docker compose ps

# Update and restart
git pull && docker compose down && docker compose build && docker compose up -d

# Clean up old containers
docker compose exec landing-page python -c "from src.services.container_manager import CellxgeneContainerManager; CellxgeneContainerManager('/data/datasets', 'cellxgene_stack_cellxgene-network', '/data/datasets').cleanup_inactive(3600)"
```
