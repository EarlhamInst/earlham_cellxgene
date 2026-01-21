# Dynamic CellXGene Container System

## Overview

The CellXGene Explorer supports **dynamic multi-dataset viewing** through on-demand container spawning. This allows multiple users to view different datasets simultaneously without conflicts. Containers automatically clean up after 48 hours of inactivity.

## Architecture

### Components

1. **Landing Page** (`services/landing-page/`)
   - Manages dataset catalog
   - Spawns CellXGene containers on demand via Docker SDK
   - Tracks active containers with last access timestamps
   - Background scheduler for automatic cleanup (48-hour inactivity)

2. **Container Manager** (`services/landing-page/src/services/container_manager.py`)
   - Allocates ports (5006-5100) for CellXGene instances
   - Launches containers with specific dataset files
   - Health checks ensure application readiness before user access
   - Tracks last access time for inactivity-based cleanup
   - Handles container lifecycle (start, stop, cleanup)

3. **CellXGene Service** (`services/cellxgene/`)
   - Base image for dynamic containers
   - Accepts `DATASET_FILE` environment variable
   - Launches specific h5ad file on port 5005 (internal)

4. **Nginx Proxy** (`services/nginx/`)
   - Routes requests to dynamic containers
   - Pattern: `/cellxgene-{dataset_id}/` → `cellxgene-{dataset_id}:5005`
   - Uses Docker internal DNS for discovery
   - Custom error pages when containers are unavailable

### How It Works

1. **User clicks "Launch in CellXGene" on landing page**
   ```
   POST /api/datasets/{dataset_id}/launch
   ```

2. **Frontend polls for container readiness**
   - Displays "Starting..." with elapsed time
   - Polls `/api/datasets/{dataset_id}/status` every second
   - Updates access time during polling to prevent premature cleanup

3. **Landing page spawns dedicated container**
   - Container name: `cellxgene-{dataset_id}`
   - Environment: `DATASET_FILE={filename}.h5ad`
   - Port: Auto-allocated from range 5006-5100
   - Network: `cellxgene_stack_cellxgene-network`
   - Health check: Waits for HTTP 200 response before marking ready

4. **Browser opens URL when ready**
   - Frontend receives ready status
   - Opens URL in new tab: `https://your-domain.com/cellxgene-{dataset_id}/`

5. **Nginx proxies requests**
   ```
   https://your-domain.com/cellxgene-{dataset_id}/
   → http://cellxgene-{dataset_id}:5005/
   ```

6. **User browses dataset in CellXGene**
   - Each dataset runs in isolation
   - Multiple users can view different datasets
   - No interference between instances

## Configuration

### Docker Socket Access

The landing page container requires access to the Docker socket:

```yaml
# docker-compose.yml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

**Security Note**: The landing page runs as `root` to access the Docker socket. In production, consider:
- Using Docker socket proxy (e.g., tecnativa/docker-socket-proxy)
- Running on a dedicated Docker daemon
- Implementing stricter access controls

### Port Range

Dynamic containers use ports 5006-5100 (internal to Docker network). Configure in `container_manager.py`:

```python
self.port_range = (5006, 5100)  # Supports up to 95 concurrent instances
```

### Network

All containers must be on the same Docker network for DNS resolution:

```yaml
networks:
  cellxgene-network:
    driver: bridge
```

## API Changes

### Launch Endpoint Response

**Before** (single static container):
```json
{
  "dataset_id": "scanpy-pbmc3k",
  "dataset_name": "Scanpy Pbmc3K",
  "cellxgene_url": "http://localhost/cellxgene/",
  "status": "ready"
}
```

**After** (dynamic containers):
```json
{
  "dataset_id": "scanpy-pbmc3k",
  "dataset_name": "Scanpy Pbmc3K",
  "cellxgene_url": "http://localhost/cellxgene-scanpy-pbmc3k/",
  "container_port": 5006,
  "status": "ready"
}
```

## Deployment Considerations

### Resource Limits

Each CellXGene container consumes memory based on dataset size. Configure limits:

```yaml
deploy:
  resources:
    limits:
      memory: 2GB  # Per dataset
    reservations:
      memory: 1GB
```

### Auto-Cleanup

Containers are set to `auto_remove=True` and will be cleaned up when stopped. Implement cleanup strategies:

1. **Idle timeout**: Stop containers after 30-60 minutes of inactivity
2. **Max age**: Stop containers running longer than threshold
3. **Manual cleanup**: Admin endpoint to stop all containers

Implement in `container_manager.py`:

```python
def cleanup_inactive(self, max_age_seconds: int = 3600):
    """Stop containers older than threshold."""
    # Implementation provided in container_manager.py
```

### Monitoring

Monitor active containers:

```bash
# List all CellXGene containers
docker ps --filter "name=cellxgene-"

# Check container manager state
curl http://localhost:8000/api/containers/active
```

## Testing

### Manual Test

1. **Access landing page**: http://localhost
2. **Click "Launch in CellXGene"** for any dataset
3. **Verify container spawned**:
   ```bash
   docker ps --filter "name=cellxgene-"
   ```
4. **Access CellXGene**: URL from launch response
5. **Launch second dataset** (different from first)
6. **Verify both containers running**:
   ```bash
   docker ps --filter "name=cellxgene-" --format "table {{.Names}}\t{{.Status}}"
   ```

### Automated Tests

Update e2e tests to account for dynamic URLs:

```python
# tests/e2e/test_dataset_exploration.py
def test_multiple_datasets_simultaneously():
    """Test that multiple datasets can be launched concurrently."""
    # Launch dataset 1
    response1 = launch_dataset(dataset_id_1)
    url1 = response1['cellxgene_url']
    
    # Launch dataset 2
    response2 = launch_dataset(dataset_id_2)
    url2 = response2['cellxgene_url']
    
    # Both should be accessible
    assert browser.get(url1).status_code == 200
    assert browser.get(url2).status_code == 200
```

## Troubleshooting

### Container Won't Start

**Symptoms**: Launch endpoint returns error
**Causes**:
- Docker socket permission denied
- Port range exhausted
- Dataset file not found

**Solutions**:
```bash
# Check Docker socket permissions
ls -l /var/run/docker.sock

# Check available ports
docker ps --format "{{.Ports}}" | grep 5006-5100

# Verify dataset file
docker exec cellxgene-landing-page ls -la /data/datasets/
```

### Nginx 502 Bad Gateway

**Symptoms**: CellXGene URL returns 502
**Causes**:
- Container not fully started
- DNS resolution failure
- Container crashed

**Solutions**:
```bash
# Check container status
docker logs cellxgene-{dataset_id}

# Verify network connectivity
docker exec cellxgene-nginx ping cellxgene-{dataset_id}

# Test CellXGene directly
docker exec cellxgene-{dataset_id} curl http://localhost:5005/
```

### Memory Exhaustion

**Symptoms**: System becomes unresponsive
**Causes**: Too many concurrent containers

**Solutions**:
- Implement container limits (max 10-20 concurrent)
- Add aggressive cleanup policy
- Monitor memory usage:
  ```bash
  docker stats --format "table {{.Name}}\t{{.MemUsage}}"
  ```

## Future Enhancements

1. **Session Management**: Track user sessions and cleanup containers
2. **Load Balancing**: Distribute containers across multiple Docker hosts
3. **Kubernetes**: Migrate to k8s for production-grade orchestration
4. **Caching**: Keep popular datasets warm in pre-started containers
5. **Admin Dashboard**: Web UI for container management

## Migration from Static Container

If migrating from the old single-container setup:

1. Update docker-compose.yml (add Docker socket mount)
2. Rebuild landing-page service
3. Update nginx configuration
4. Test with one dataset first
5. Monitor resource usage
6. Implement cleanup policies

The legacy `cellxgene` service container can remain running for backward compatibility, but new launches will use dynamic containers.
