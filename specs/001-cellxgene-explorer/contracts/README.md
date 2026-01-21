# Service Contracts: CellXGene Explorer

**Feature**: 001-cellxgene-explorer  
**Date**: 2026-01-14  
**Purpose**: Define service interfaces and contracts

## Overview

The CellXGene Explorer stack consists of three main services with defined contracts:
1. **Landing Page Service** - Dataset catalog and selection UI
2. **CellXGene Service** - Single-cell visualization (external dependency)
3. **Nginx** - Reverse proxy and routing

## Service Architecture

```
                            ┌─────────────┐
                            │   Nginx     │
                            │   (Port 80) │
                            └──────┬──────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
             (/ → )│     (/cellxgene/ →)│    (/api →)
                    │              │              │
           ┌────────▼────────┐  ┌─▼──────────┐ ┌─▼──────────┐
           │  Landing Page   │  │ CellXGene  │ │Landing Page│
           │  Static Files   │  │  Service   │ │ API Service│
           │   (HTML/CSS/JS) │  │ (Port 5005)│ │ (Port 8000)│
           └─────────────────┘  └─────┬──────┘ └─────┬──────┘
                                      │              │
                                      │              │
                                ┌─────▼──────────────▼─────┐
                                │  Volume-Mounted Datasets  │
                                │   /data/datasets/*.h5ad   │
                                └───────────────────────────┘
```

## Contract 1: Landing Page API

**Service**: Landing Page Service  
**Port**: 8000 (internal), exposed via Nginx at `/api`  
**Technology**: Flask or FastAPI  
**Format**: REST API, JSON responses

### Endpoints

See [landing-page-api.yaml](landing-page-api.yaml) for full OpenAPI specification.

**Summary**:
- `GET /api/health` - Health check
- `GET /api/datasets` - List all datasets (with filtering, sorting)
- `GET /api/datasets/{id}` - Get dataset details
- `POST /api/datasets/{id}/launch` - Launch CellXGene viewer
- `GET /api/datasets/{id}/metadata` - Get raw metadata JSON

### Contract Guarantees

**Service MUST**:
- Respond to health checks within 2 seconds
- Validate all datasets on startup (fail-fast if any invalid)
- Return valid JSON for all API responses
- Include CORS headers for browser access
- Log all dataset access events
- Return 404 for non-existent datasets
- Return 503 if CellXGene service unavailable

**Service MUST NOT**:
- Modify dataset files
- Allow unauthenticated uploads
- Return sensitive file system paths
- Execute user-provided code

### Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `dataset_not_found` | 404 | Dataset ID doesn't exist |
| `validation_failed` | 400 | Dataset failed validation |
| `service_unavailable` | 503 | CellXGene workers all busy |
| `internal_error` | 500 | Unexpected server error |

---

## Contract 2: CellXGene Service

**Service**: CellXGene v2.x  
**Port**: 5005 (internal), exposed via Nginx at `/cellxgene/`  
**Technology**: Python, Gunicorn + Uvicorn  
**Workers**: 10 × 20GB memory each  
**Format**: External service (CZI CellXGene)

### Interface

CellXGene service is proxied through Nginx. Landing page generates URLs like:
```
/cellxgene/?dataset=pbmc_10k
```

Which Nginx routes to:
```
http://cellxgene-service:5005/?dataset=pbmc_10k
```

### Contract Guarantees

**Service MUST**:
- Respond to requests within 30 seconds for dataset launch
- Support 10 concurrent users (via worker pool)
- Validate dataset parameter and return 404 if not found
- Serve CellXGene UI assets
- Support all standard CellXGene interactions (filtering, clustering, etc.)

**Service MUST NOT**:
- Write to dataset files (read-only access)
- Exceed per-worker memory limits (20GB)
- Expose file system paths to users

### Resource Limits

- **CPU**: Unlimited (bursts allowed)
- **Memory**: 20GB per worker, 200GB total
- **Disk**: Read-only access to /data/datasets
- **Network**: Internal Docker network only

---

## Contract 3: Nginx Reverse Proxy

**Service**: Nginx  
**Port**: 80 (external), 443 (optional SSL)  
**Technology**: Nginx  
**Format**: HTTP proxy

### Routing Rules

| Path | Proxy Target | Purpose |
|------|--------------|---------|
| `/` | Static files or landing-page:8000 | Landing page UI |
| `/api/*` | landing-page:8000/api/* | API endpoints |
| `/cellxgene/*` | cellxgene:5005/* | CellXGene viewer |
| `/static/*` | Static files | CSS, JS, images |

### Contract Guarantees

**Service MUST**:
- Route requests to correct backend service
- Add appropriate CORS headers
- Log all access in standard format
- Set appropriate timeouts (5min for CellXGene)
- Serve static files with gzip compression
- Handle SSL termination (if configured)

**Service MUST NOT**:
- Modify request/response bodies
- Cache dynamic API responses
- Expose internal service names in errors

### Configuration

```nginx
upstream landing_page {
    server landing-page:8000;
}

upstream cellxgene {
    server cellxgene:5005;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://landing_page;
    }
    
    location /api/ {
        proxy_pass http://landing_page/api/;
    }
    
    location /cellxgene/ {
        proxy_pass http://cellxgene/;
        proxy_read_timeout 300s;
    }
}
```

---

## Contract 4: Docker Compose Orchestration

**File**: docker-compose.yml  
**Purpose**: Define multi-container application

### Service Definitions

```yaml
version: '3.8'

services:
  landing-page:
    build: ./services/landing-page
    ports:
      - "8000"
    volumes:
      - ${DATA_DIRECTORY}:/data/datasets:ro
      - ${LOG_DIRECTORY}:/data/logs
    environment:
      - DATA_DIRECTORY=/data/datasets
      - CELLXGENE_URL=http://cellxgene:5005
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  cellxgene:
    build: ./services/cellxgene
    ports:
      - "5005"
    volumes:
      - ${DATA_DIRECTORY}:/data/datasets:ro
    environment:
      - WORKER_COUNT=10
      - WORKER_MEMORY_MB=4096
    deploy:
      resources:
        limits:
          memory: 42G  # 10 workers × 4GB + overhead
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5005/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  nginx:
    build: ./services/nginx
    ports:
      - "80:80"
    depends_on:
      - landing-page
      - cellxgene
    volumes:
      - ./services/landing-page/static:/usr/share/nginx/html/static:ro
```

### Contract Guarantees

**Compose MUST**:
- Start services in dependency order (landing-page, cellxgene, then nginx)
- Restart services on failure
- Enforce resource limits
- Create necessary networks
- Mount volumes as specified

---

## Contract 5: Data Directory Structure

**Path**: Configured via `DATA_DIRECTORY` environment variable  
**Default**: `/data/datasets`

### Structure

```
${DATA_DIRECTORY}/
├── *.h5ad          # H5AD dataset files
├── *.json          # Corresponding metadata files
└── README.txt      # Optional instructions for admins
```

### Contract Guarantees

**Landing Page Service MUST**:
- Scan this directory on startup
- Pair each `.h5ad` with corresponding `.json`
- Fail if any dataset lacks metadata
- Fail if any dataset fails validation
- Treat directory as read-only

**CellXGene Service MUST**:
- Read datasets from this directory
- Not write or modify files
- Handle missing files gracefully

---

## Inter-Service Communication

### Landing Page → CellXGene

**Protocol**: HTTP (via Nginx proxy)  
**Authentication**: None (internal network)

Landing page constructs URLs like `/cellxgene/?dataset={id}` which Nginx routes to CellXGene.

### Landing Page → Nginx

**Protocol**: HTTP  
**Relationship**: Nginx proxies requests to Landing Page

Landing page doesn't directly communicate with Nginx; Nginx initiates connections to Landing Page.

### Health Checks

All services MUST implement health check endpoints:
- Return 200 OK when healthy
- Return 503 Service Unavailable when unhealthy
- Respond within 5 seconds
- Validate critical dependencies (e.g., data directory accessible)

---

## Validation Contracts

### Startup Validation Contract

**Performed by**: Landing Page Service  
**Timing**: On service startup, before accepting requests

**Steps**:
1. Check `DATA_DIRECTORY` exists and is readable
2. Scan for all `*.h5ad` files
3. For each h5ad file:
   a. Verify corresponding `.json` exists
   b. Validate JSON is valid and conforms to schema
   c. Validate h5ad is valid AnnData format
   d. Extract cell/feature counts
4. If ANY validation fails → Exit with error (fail-fast)
5. If all pass → Start accepting requests

**Exit Codes**:
- `0`: All datasets valid, service started
- `1`: Validation failed, see logs for details

### Runtime Validation Contract

**Performed by**: Landing Page Service  
**Timing**: On dataset launch request

**Steps**:
1. Verify dataset ID exists in catalog
2. Verify dataset passed startup validation
3. Return 404 if not found
4. Return 200 with viewer URL if found

No additional validation at runtime (startup validation is comprehensive).

---

## Logging Contracts

### Access Logging

**Format**: JSON Lines  
**Location**: `${LOG_DIRECTORY}/access.log`

**Schema**:
```json
{
  "timestamp": "ISO 8601 datetime",
  "dataset_id": "string",
  "action": "view_catalog | launch_dataset | error",
  "client_ip": "string",
  "user_agent": "string",
  "duration_seconds": "float (optional)",
  "error_message": "string (optional)"
}
```

### Error Logging

**Format**: Structured logs (JSON)  
**Location**: `${LOG_DIRECTORY}/{service}.log`

**All errors MUST include**:
- Timestamp
- Service name
- Error severity (ERROR, CRITICAL)
- Error message
- Stack trace
- Request context (if applicable)

---

## Testing Contracts

### Unit Testing

**Framework**: pytest  
**Coverage**: 80%+ of code paths  
**Scope**: Individual functions and classes

**Contracts**:
- All services MUST have unit tests
- Tests MUST be runnable via `pytest tests/unit/`
- Tests MUST not depend on external services
- Tests MUST use mocks/stubs for I/O

### Integration Testing

**Framework**: pytest with Docker  
**Scope**: Service-to-service interactions

**Contracts**:
- Landing Page ↔ CellXGene integration tested
- Dataset validation tested with real files
- Health checks tested
- Error handling tested

### Contract Testing

**Framework**: OpenAPI validator  
**Scope**: API contract conformance

**Contracts**:
- All API responses MUST match OpenAPI schema
- All required fields MUST be present
- All data types MUST be correct

### End-to-End Testing

**Framework**: Playwright or Selenium  
**Scope**: Full user workflows

**Contracts**:
- User can view dataset catalog
- User can click dataset and launch CellXGene
- CellXGene loads and displays dataset

---

**Status**: All contracts defined and aligned with requirements.
