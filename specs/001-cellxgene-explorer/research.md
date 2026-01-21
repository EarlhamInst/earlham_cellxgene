# Research: CellXGene Explorer

**Feature**: 001-cellxgene-explorer  
**Date**: 2026-01-14  
**Purpose**: Document technology choices, design decisions, and alternatives considered

## Executive Summary

This document captures the research and decision-making process for the CellXGene Explorer implementation. All technical unknowns have been resolved through the clarification process and tech stack specification. Key decisions: Docker Compose for orchestration, CellXGene v2.x with Gunicorn/Uvicorn workers, Nginx reverse proxy, volume-mounted storage, and Flask/FastAPI for the landing page service.

## Technology Decisions

### 1. Containerization Platform

**Decision**: Docker with Docker Compose

**Rationale**:
- **Portability**: Works consistently across OpenNebula, CyVerse, and local development
- **Reproducibility**: Ensures identical environments for development, testing, and production
- **Isolation**: Each service runs in its own container with defined resource limits
- **Ease of deployment**: Single `docker-compose up` command to launch entire stack
- **Industry standard**: Well-documented, widely adopted, strong community support

**Alternatives Considered**:
- **Kubernetes**: Rejected - overly complex for single-node deployment; adds operational overhead; overkill for 10-50 datasets and 10 concurrent users
- **Podman**: Rejected - less widespread adoption; potential compatibility issues on OpenNebula/CyVerse; Docker more familiar to team
- **Virtual machines**: Rejected - higher resource overhead; slower deployment; less modular than containers

### 2. CellXGene Version and Concurrency Model

**Decision**: CellXGene v2.x with Gunicorn + Uvicorn (10 workers × 4GB)

**Rationale**:
- **Latest stable version**: CellXGene v2.x provides best performance and feature set
- **ASGI support**: Uvicorn handles async operations efficiently
- **Worker isolation**: Each Gunicorn worker is independent, providing fault isolation
- **Resource control**: Explicit memory limits (4GB/worker) prevent resource exhaustion
- **Proven pattern**: Gunicorn + Uvicorn is battle-tested for Python web applications

**Alternatives Considered**:
- **Single-threaded**: Rejected - cannot handle concurrent users; blocks on I/O
- **Instance per user**: Rejected - excessive resource usage (400GB for 10 users); complex session management
- **Dynamic scaling**: Rejected - adds complexity; overkill for known user count; harder to debug

### 3. Reverse Proxy

**Decision**: Nginx

**Rationale**:
- **Performance**: Excellent static file serving and proxy performance
- **URL routing**: Clean routing (/ → landing page, /cellxgene/ → CellXGene service)
- **SSL termination**: Optional HTTPS support for production deployments
- **Load balancing**: Can distribute across multiple CellXGene workers
- **Logging**: Built-in access logging for usage tracking
- **Lightweight**: Minimal resource footprint

**Alternatives Considered**:
- **Traefik**: Rejected - more complex configuration; not needed for simple routing
- **Apache httpd**: Rejected - heavier resource usage; less common in Docker stacks
- **HAProxy**: Rejected - overkill for our needs; primarily for load balancing
- **No proxy**: Rejected - exposes internal services directly; no unified entry point

### 4. Landing Page Technology

**Decision**: Flask or FastAPI (Python 3.11+)

**Rationale**:
- **Language consistency**: Same language as CellXGene (Python), simplifies development
- **Simplicity**: Lightweight frameworks, easy to understand and modify
- **API support**: Easy to create JSON API for dataset catalog
- **Template engine**: Built-in HTML templating (Jinja2) for dynamic pages
- **Testing**: pytest ecosystem for comprehensive testing
- **Documentation**: Excellent documentation and community support

**Flask vs FastAPI choice depends on**:
- Flask: Better for simple templating, more mature
- FastAPI: Better for API-first design, automatic OpenAPI docs, async support

**Alternatives Considered**:
- **Static HTML + JavaScript**: Rejected - need dynamic dataset list from filesystem; requires API anyway
- **React/Vue SPA**: Rejected - adds build complexity; overkill for simple dataset catalog
- **Django**: Rejected - too heavyweight; includes ORM and features we don't need

### 5. Data Storage Model

**Decision**: Volume-mounted directory from host filesystem

**Rationale**:
- **Simplicity**: Direct filesystem access, no abstraction layer
- **Performance**: No network overhead for local deployments
- **Hot-swap**: Add datasets without container rebuild
- **Compatibility**: Works with NFS/MinIO for multi-node deployments
- **Backup**: Standard filesystem backup tools work directly
- **No size limits**: Can handle datasets up to available disk space

**Alternatives Considered**:
- **Baked into image**: Rejected - requires rebuild for every dataset change; large image sizes
- **Object storage (S3/MinIO)**: Rejected - adds latency; requires network dependency; more complex for small deployments
- **Database BLOBs**: Rejected - inefficient for large binary files; adds database overhead

### 6. Metadata Format

**Decision**: JSON files conforming to http://singlecellschemas.org

**Rationale**:
- **Standard compliance**: Aligns with single-cell community standards
- **Interoperability**: Compatible with other single-cell tools
- **Human-readable**: Easy to create and modify manually
- **Validation**: Can be validated against JSON schema
- **One-to-one mapping**: Each dataset has its own metadata file (simple management)

**Alternatives Considered**:
- **YAML**: Rejected - less strict than JSON; no schema standard in singlecellschemas.org
- **Embedded in filename**: Rejected - limited metadata; fragile parsing; not extensible
- **Central config file**: Rejected - harder to manage; single point of failure; merge conflicts
- **Auto-extraction from h5ad**: Rejected - slow; not all needed metadata in h5ad files

### 7. Error Handling Strategy

**Decision**: Fail-fast validation on startup

**Rationale**:
- **Constitutional alignment**: Principle IV (Fail-Fast Error Handling) mandates this
- **Data integrity**: Ensures all datasets are valid before users access system
- **Early detection**: Finds problems during deployment, not user interaction
- **Clear feedback**: Admin gets explicit error messages during startup
- **No silent failures**: Aligns with constitution prohibition on silent breakages

**Alternatives Considered**:
- **Graceful degradation**: Rejected - violates constitution; risks serving corrupt data
- **Lazy validation**: Rejected - poor user experience; users encounter errors
- **No validation**: Rejected - violates constitution; risks data corruption

### 8. Testing Strategy

**Decision**: Multi-layer testing (unit, integration, contract, end-to-end)

**Rationale**:
- **Constitutional requirement**: Principle I mandates comprehensive testing (80%+ coverage)
- **Unit tests**: Validate individual modules (pytest)
- **Integration tests**: Validate service interactions (pytest with Docker)
- **Contract tests**: Verify API boundaries (OpenAPI validation)
- **End-to-end tests**: Validate full user workflows (Playwright/Selenium)
- **Docker healthchecks**: Continuous validation of service health

**Alternatives Considered**:
- **Manual testing only**: Rejected - violates constitution; error-prone; not repeatable
- **Unit tests only**: Rejected - insufficient; doesn't catch integration issues

## Best Practices

### CellXGene Deployment
- Use Gunicorn with Uvicorn workers for ASGI support
- Set explicit memory limits per worker
- Configure graceful shutdown timeouts
- Enable access logging for usage tracking
- Use read-only volume mounts for dataset directory (prevents accidental modification)

### Docker Compose
- Use `.env` files for environment configuration
- Pin image versions for reproducibility
- Define resource limits for each service
- Use healthchecks for each container
- Separate networks for service isolation
- Use named volumes for persistent data

### Nginx Configuration
- Enable gzip compression for static files
- Set appropriate proxy timeouts for CellXGene (may process large datasets)
- Configure access logging for usage analytics
- Use `proxy_pass` with trailing slash for clean URL routing
- Enable buffering for large responses

### Security Considerations
- Run containers as non-root users
- Use read-only filesystems where possible
- Limit container capabilities
- Scan images for vulnerabilities (Trivy, Clair)
- Keep base images updated
- Although no authentication required (FAIR principles), consider rate limiting for abuse prevention

### Deployment on OpenNebula/CyVerse
- Ensure Docker and Docker Compose are installed
- Use attached block storage or NFS for dataset storage
- Configure firewall rules for port access
- Set up monitoring (optional: Prometheus + Grafana)
- Document resource requirements (CPU, RAM, disk)
- Provide deployment scripts for one-command setup

## Performance Considerations

### Memory Allocation
- **Total**: 40GB (10 workers × 4GB)
- **Additional**: 2-4GB for Nginx, landing page service, OS overhead
- **Recommended instance**: 48GB RAM minimum

### Disk Space
- **Datasets**: Variable (assume 1-5GB per dataset × 50 datasets = 50-250GB)
- **Logs**: 1-5GB (with rotation)
- **Images**: 5-10GB
- **Recommended**: 300GB+ disk space

### Network
- **Internal**: Container-to-container via Docker network (fast)
- **External**: Depends on CyVerse/OpenNebula network (typically <10ms latency)
- **Bandwidth**: Minimal (mostly static file serving, dataset loading happens once)

## Open Questions for Future Iterations

1. **Monitoring**: Should we include Prometheus + Grafana in MVP? (Current: Optional, can add later)
2. **Multi-node**: Should we optimize for multi-node deployment in MVP? (Current: Single-node focus, NFS/MinIO hooks for later)
3. **Authentication**: Will open access model need revision for sensitive data? (Current: No auth per FAIR principles)
4. **Rate limiting**: Do we need abuse prevention? (Current: Defer to Phase 3 if needed)
5. **Auto-scaling**: Should workers scale dynamically? (Current: Fixed 10 workers, simpler to manage)

## References

- CellXGene Documentation: https://chanzuckerberg.github.io/cellxgene/
- Single Cell Schemas: http://singlecellschemas.org
- Gunicorn Documentation: https://docs.gunicorn.org/
- Docker Compose Documentation: https://docs.docker.com/compose/
- Nginx Reverse Proxy Guide: https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/
- OpenNebula Documentation: https://docs.opennebula.io/
- CyVerse Documentation: https://cyverse.org/documentation

---

**Status**: All unknowns resolved. Ready for Phase 1 (Design).
