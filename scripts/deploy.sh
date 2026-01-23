#!/usr/bin/env bash
#
# Deployment Script for CellXGene Explorer
#
# One-command deployment with validation and health checks.
#
# Constitutional Alignment:
# - Principle IV (Fail-Fast): Validates before deploying
# - Principle III (Code Clarity): Clear progress messages
# - Principle VI (Accessibility): Simple deployment for all skill levels
#
# For detailed deployment instructions, see docs/deployment.md
#

set -e  # Exit on any error
set -u  # Exit on undefined variable
set -o pipefail  # Exit if any command in pipeline fails

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Configuration
DATA_DIR="${DATA_DIR:-$PROJECT_ROOT/data/datasets}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  CellXGene Explorer - Deployment Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Function to print colored messages
print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
print_step "Checking prerequisites..."

# Check for Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker first."
    exit 1
fi
print_success "Docker found: $(docker --version)"

# Check for Docker Compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
    print_success "Docker Compose found: $(docker compose version --short 2>/dev/null || echo 'v2+')"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    print_success "Docker Compose found (legacy): $(docker-compose --version)"
else
    print_error "Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
        print_success "Created $ENV_FILE"
    else
        print_error ".env.example not found. Cannot create .env file."
        exit 1
    fi
else
    print_success ".env file exists"
fi

# Check Docker socket access (required for dynamic container spawning)
print_step "Checking Docker socket access..."
if [ -S /var/run/docker.sock ]; then
    if [ -r /var/run/docker.sock ] && [ -w /var/run/docker.sock ]; then
        print_success "Docker socket is accessible"
    else
        print_warning "Docker socket exists but may not be accessible"
        print_warning "Dynamic container spawning may not work. Run: sudo chmod 666 /var/run/docker.sock"
    fi
else
    print_warning "Docker socket not found at /var/run/docker.sock"
    print_warning "Dynamic container spawning may not work"
fi

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    print_warning "Data directory not found. Creating $DATA_DIR..."
    mkdir -p "$DATA_DIR"
    print_success "Created data directory"
fi

# Validate datasets
print_step "Validating datasets..."
cd "$PROJECT_ROOT"

if [ -f "$SCRIPT_DIR/validate-datasets.py" ]; then
    if python3 "$SCRIPT_DIR/validate-datasets.py" --data-dir "$DATA_DIR"; then
        print_success "Dataset validation passed"
    else
        print_error "Dataset validation failed"
        echo ""
        print_warning "You can continue deployment, but invalid datasets will be skipped."
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Deployment cancelled"
            exit 1
        fi
    fi
else
    print_warning "Validation script not found, skipping validation"
fi

# Build Docker images
print_step "Building Docker images..."
if $DOCKER_COMPOSE build; then
    print_success "Docker images built successfully"
else
    print_error "Docker build failed"
    exit 1
fi

# Stop existing containers
print_step "Stopping existing containers (if any)..."
$DOCKER_COMPOSE down || true
print_success "Stopped existing containers"

# Start services
print_step "Starting services..."
if $DOCKER_COMPOSE up -d; then
    print_success "Services started"
else
    print_error "Failed to start services"
    exit 1
fi

# Wait for services to be healthy
print_step "Waiting for services to be healthy..."
sleep 5

MAX_WAIT=60
WAIT_TIME=0
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if $DOCKER_COMPOSE ps | grep -q "unhealthy"; then
        print_warning "Some services are unhealthy, waiting... ($WAIT_TIME/$MAX_WAIT seconds)"
        sleep 5
        WAIT_TIME=$((WAIT_TIME + 5))
    elif $DOCKER_COMPOSE ps | grep -q "starting"; then
        print_warning "Services are starting, waiting... ($WAIT_TIME/$MAX_WAIT seconds)"
        sleep 5
        WAIT_TIME=$((WAIT_TIME + 5))
    else
        break
    fi
done

# Check service status
print_step "Checking service status..."
$DOCKER_COMPOSE ps

# Test health endpoints
print_step "Testing health endpoints..."
NGINX_PORT=$(grep NGINX_PORT "$ENV_FILE" | cut -d '=' -f2 || echo "80")

if curl -sf "http://localhost:$NGINX_PORT/api/health" > /dev/null; then
    print_success "Landing page service is healthy"
else
    print_error "Landing page service health check failed"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Access the application at: ${BLUE}http://localhost:$NGINX_PORT${NC}"
echo -e "Admin panel: ${BLUE}http://localhost:$NGINX_PORT/admin${NC}"
echo ""
echo "Features:"
echo "  • Browse dataset catalog"
echo "  • Launch CellXGene on-demand (dynamic containers)"
echo "  • Automatic cleanup after 48 hours of inactivity"
echo "  • Monitor active containers in admin panel"
echo ""
echo "Useful commands:"
echo "  View logs:           $DOCKER_COMPOSE logs -f"
echo "  Stop services:       $DOCKER_COMPOSE down"
echo "  Restart:             $DOCKER_COMPOSE restart"
echo "  Add datasets:        See docs/adding-datasets.md"
echo "  Troubleshooting:     See docs/troubleshooting.md"
echo "  Remote deployment:   See docs/deployment.md"
echo ""
