# Architecture Documentation

## System Overview

CellXGene Explorer is a multi-container web application that provides researchers with an intuitive interface to explore single-cell RNA sequencing datasets using CellXGene visualization tools. The system follows a microservices architecture with three main components orchestrated by Docker Compose.

### Key Architectural Principles

1. **Containerization**: Each service runs in its own Docker container for isolation and portability
2. **Fail-Fast Validation**: All datasets are validated on startup to ensure data integrity
3. **Stateless Services**: Services are designed to be stateless, with data stored in volume mounts
4. **Scalability**: Worker-based concurrency model supports multiple simultaneous users
5. **Simplicity**: File-based storage eliminates database complexity

## System Components

### 1. Landing Page Service

**Technology**: Python (Flask/FastAPI)  
**Port**: Internal 8000  
**Purpose**: Dataset catalog and API endpoints

**Responsibilities**:
- Scan data directory for h5ad files and metadata
- Validate datasets against singlecellschemas.org standards
- Provide REST API for dataset operations
- Serve web UI for dataset selection
- Generate CellXGene launch URLs

**Key Files**:
- `src/models/`: Dataset and metadata models
- `src/services/`: Dataset scanner and catalog services
- `src/routes/`: API endpoint handlers
- `src/templates/`: HTML templates
- `src/static/`: CSS and JavaScript assets

### 2. CellXGene Service

**Technology**: CellXGene v2.x + Gunicorn + Uvicorn  
**Port**: Internal 5005  
**Purpose**: Interactive single-cell data visualization

**Responsibilities**:
- Serve CellXGene web application
- Load and visualize h5ad datasets
- Handle 10 concurrent user sessions (via 10 Gunicorn workers)
- Provide interactive filtering, clustering, and gene expression views

**Configuration**:
- **Workers**: 10 Gunicorn workers with Uvicorn ASGI
- **Memory**: 20GB per worker (200GB total)
- **Timeout**: 300 seconds for large dataset loading
- **Worker Class**: Uvicorn for async support

**Key Files**:
- `gunicorn_conf.py`: Worker configuration
- `entrypoint.sh`: Startup validation script
- `Dockerfile`: Container build instructions

### 3. Nginx Reverse Proxy

**Technology**: Nginx  
**Port**: External 80, Internal 80  
**Purpose**: Unified entry point and routing

**Responsibilities**:
- Route `/` → Landing Page UI
- Route `/api/*` → Landing Page API
- Route `/cellxgene/*` → CellXGene service
- Serve static assets with gzip compression
- Add CORS headers for API endpoints
- Log all access requests

**Configuration**:
- Proxy timeouts: 5 minutes (CellXGene), 30 seconds (API)
- Gzip compression for CSS, JS, HTML
- Access logging in standard format

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Nginx (Port 80)                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Routes:                                              │  │
│  │  - / → Landing Page UI                                │  │
│  │  - /api/* → Landing Page API                          │  │
│  │  - /cellxgene/* → CellXGene Service                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
           │                                  │
           ▼                                  ▼
┌─────────────────────────┐      ┌─────────────────────────┐
│  Landing Page Service   │      │   CellXGene Service     │
│  (Flask/FastAPI:8000)   │      │   (Gunicorn:5005)       │
│  ┌───────────────────┐  │      │  ┌──────────────────┐   │
│  │ Dataset Scanner   │  │      │  │ 10 Workers       │   │
│  │ Catalog Manager   │  │      │  │ (Uvicorn/ASGI)   │   │
│  │ REST API          │  │      │  │ 20GB each        │   │
│  │ Web UI            │  │      │  └──────────────────┘   │
│  └───────────────────┘  │      │                         │
└─────────────────────────┘      └─────────────────────────┘
           │                                  │
           └────────────┬─────────────────────┘
                        ▼
           ┌────────────────────────┐
           │   Data Volume Mount    │
           │   /data/datasets/      │
           │  ┌──────────────────┐  │
           │  │ *.h5ad files     │  │
           │  │ *.json metadata  │  │
           │  └──────────────────┘  │
           └────────────────────────┘
```

## Data Flow

### User Journey: View Catalog and Launch CellXGene

1. **User accesses landing page** (`http://localhost/`)
   - Browser → Nginx → Landing Page Service
   - Landing Page serves HTML/CSS/JS

2. **Browser requests dataset list** (`GET /api/datasets`)
   - JavaScript → Nginx → Landing Page API
   - Landing Page scans `/data/datasets/`
   - Returns JSON array of datasets with metadata

3. **User clicks "Launch" button** (`POST /api/datasets/{id}/launch`)
   - JavaScript → Nginx → Landing Page API
   - Landing Page generates CellXGene URL
   - Returns `{"viewer_url": "/cellxgene/?dataset=pbmc_10k"}`

4. **Browser navigates to viewer URL** (`/cellxgene/?dataset=pbmc_10k`)
   - Browser → Nginx → CellXGene Service
   - CellXGene loads h5ad file from `/data/datasets/`
   - Returns interactive visualization

### Startup Validation Flow

1. **Docker Compose starts services**
2. **Landing Page Service**:
   - Scans `/data/datasets/` for `*.h5ad` files
   - For each h5ad, validates paired `*.json` metadata
   - Validates h5ad has HDF5 signature
   - Validates metadata conforms to singlecellschemas.org
   - If any dataset invalid: **service fails to start** (fail-fast)
   - If all valid: service marks as healthy

3. **CellXGene Service**:
   - Validates `/data/datasets/` is accessible
   - Starts Gunicorn with 10 Uvicorn workers
   - Each worker validates it can import CellXGene
   - Service marks as healthy

4. **Nginx**:
   - Validates config file syntax
   - Starts routing traffic

## Service Boundaries

### Landing Page Service

**Owns**:
- Dataset catalog management
- Metadata validation
- API endpoints for dataset operations
- Web UI for dataset selection

**Does NOT**:
- Visualize datasets (delegated to CellXGene)
- Store persistent state (file-based only)
- Handle authentication (open access per FAIR principles)

### CellXGene Service

**Owns**:
- Interactive data visualization
- Dataset rendering and filtering
- User session management (via Gunicorn workers)

**Does NOT**:
- Manage dataset catalog
- Validate metadata
- Provide dataset discovery API

### Nginx

**Owns**:
- HTTP routing and proxying
- Static file serving
- CORS header management
- Access logging

**Does NOT**:
- Application logic
- Dataset processing

## Container Orchestration (Docker Compose)

### Service Dependencies

```yaml
# Startup order:
1. Landing Page Service (no dependencies)
2. CellXGene Service (no dependencies)
3. Nginx (depends_on: landing-page, cellxgene)
```

### Volume Mounts

- **Data Directory**: `/data/datasets/` mounted read-only to services
- **Log Directory**: `/data/logs/` mounted read-write for application logs
- **Nginx Config**: `./services/nginx/nginx.conf` mounted to container

### Health Checks

All services implement health checks:

- **Landing Page**: `GET /api/health` (every 30s)
- **CellXGene**: `GET /health` (every 30s)
- **Nginx**: HTTP connection test (every 30s)

### Resource Limits

```yaml
cellxgene:
  deploy:
    resources:
      limits:
        memory: 210GB  # 10 workers × 20GB + 10GB overhead
      reservations:
        memory: 200GB
```

## Scaling Considerations

### Horizontal Scaling

**Current Setup**: Single-node deployment

**Multi-Node Options**:
1. **Shared Storage**: Use NFS or MinIO for shared `/data/datasets/`
2. **Load Balancer**: Add HAProxy/Nginx in front of multiple CellXGene instances
3. **Docker Swarm**: Orchestrate across multiple nodes
4. **Kubernetes**: For large-scale deployments (overkill for 10 users)

### Vertical Scaling

**Increase Worker Count**:
```python
# gunicorn_conf.py
workers = 20  # Support 20 concurrent users
```

**Increase Worker Memory**:
```yaml
# docker-compose.yml
memory: 420GB  # 20 workers × 20GB + 20GB overhead
```

### Performance Optimization

1. **Caching**: Add Redis for dataset metadata caching
2. **CDN**: Serve static assets via CDN
3. **Pre-warming**: Preload popular datasets into memory
4. **Compression**: Enable Brotli compression for better compression ratios

## Security Considerations

### Current Security Posture

- **No Authentication**: Open access per FAIR principles
- **No HTTPS**: HTTP only (HTTPS stub provided in `ssl/README.md`)
- **Read-Only Data**: Datasets mounted read-only to prevent tampering

### Future Security Enhancements

1. **HTTPS**: Add SSL/TLS certificates (see `services/nginx/ssl/README.md`)
2. **Authentication**: Add OAuth2/OIDC for user tracking
3. **Rate Limiting**: Nginx rate limiting to prevent abuse
4. **Input Validation**: Strict validation of dataset IDs and API inputs
5. **Security Headers**: Add CSP, X-Frame-Options, etc.

## Monitoring and Observability

### Logging

- **Access Logs**: Nginx logs all requests to `/data/logs/access.log`
- **Error Logs**: Application errors to `/data/logs/error.log`
- **Structured Logging**: JSON format for easy parsing

### Metrics (Future)

- Prometheus + Grafana for metrics collection
- Track: active users, dataset launches, response times, error rates

### Alerting (Future)

- PagerDuty/Slack integration for critical errors
- Threshold alerts for memory usage, disk space, response time

## Technology Stack Summary

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Landing Page | Python | 3.11+ | API and UI |
| Web Framework | Flask/FastAPI | Latest | HTTP server |
| CellXGene | CellXGene | v2.x | Visualization |
| ASGI Server | Uvicorn | Latest | Async HTTP |
| Process Manager | Gunicorn | Latest | Worker management |
| Reverse Proxy | Nginx | Latest | Routing |
| Orchestration | Docker Compose | v2.0+ | Container management |
| Data Format | h5ad (HDF5) | N/A | Dataset storage |
| Metadata | JSON | N/A | Dataset metadata |

## References

- [CellXGene Documentation](https://chanzuckerberg.github.io/cellxgene/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)
- [Nginx Reverse Proxy Guide](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [singlecellschemas.org Metadata Standards](http://singlecellschemas.org/)
