# CellXGene Container Inactivity Timeout

## Overview
CellXGene containers are now automatically closed after **60 minutes of inactivity** to optimize resource usage.

## Changes Made

### 1. Container Manager (`services/landing-page/src/services/container_manager.py`)
- **Added activity tracking**: Each container now tracks its last access timestamp
- **Updated data structure**: `active_containers` now stores `(container, port, last_accessed)` tuples
- **Enhanced cleanup logic**: `cleanup_inactive()` method now checks for inactivity based on timestamps rather than container age
- **New method**: `update_access_time()` allows manual activity tracking
- **Timeout**: Containers inactive for more than 3600 seconds (60 minutes) are automatically stopped

### 2. Flask Application (`services/landing-page/src/app.py`)
- **Added APScheduler**: Background scheduler for automated cleanup tasks
- **Cleanup job**: Runs every 5 minutes to check for and remove inactive containers
- **Graceful shutdown**: Scheduler properly shuts down when application terminates

### 3. API Routes (`services/landing-page/src/routes/datasets.py`)
- **Enhanced launch response**: Now includes timeout information in the response
- **New endpoint**: `/api/datasets/<dataset_id>/keepalive` (POST)
  - Allows clients to extend container lifetime by updating access time
  - Useful for long-running analysis sessions
  - Returns 404 if container is not running

### 4. Dependencies (`services/landing-page/requirements.txt`)
- **Added**: APScheduler==3.10.4 for background job scheduling

## How It Works

1. **Container Launch**: When a dataset is launched, the current timestamp is recorded
2. **Activity Updates**: 
   - Automatically updated when launching an already-running container
   - Can be manually updated via the `/keepalive` endpoint
3. **Background Cleanup**: Every 5 minutes, a background job:
   - Checks all active containers
   - Calculates time since last access
   - Stops containers inactive for more than 60 minutes
4. **Container Removal**: Stopped containers are automatically removed (Docker `auto_remove=True`)

## Usage

### Basic Usage
Containers are automatically tracked - no changes needed to existing workflows.

### Extended Sessions (Optional)
For analysis sessions longer than 60 minutes, clients can call the keep-alive endpoint:

```bash
curl -X POST http://localhost/api/datasets/<dataset_id>/keepalive
```

Response when active:
```json
{
  "dataset_id": "example_dataset",
  "status": "active",
  "message": "Container activity updated"
}
```

Response when not running:
```json
{
  "dataset_id": "example_dataset",
  "status": "not_running",
  "message": "Container is not currently running"
}
```

## Configuration

To adjust the timeout settings, modify these values in `services/landing-page/src/app.py`:

```python
scheduler.add_job(
    func=lambda: container_manager.cleanup_inactive(
        max_inactive_seconds=3600  # Change this value (in seconds)
    ),
    trigger='interval',
    minutes=5,  # Change cleanup frequency here
    ...
)
```

## Deployment

To apply these changes:

1. Rebuild the landing-page service:
   ```bash
   docker-compose build landing-page
   ```

2. Restart the services:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Monitoring

Check logs for cleanup activity:
```bash
docker-compose logs -f landing-page | grep -i "cleanup\|inactive"
```

Example log output:
```
INFO - Container pbmc3k inactive for 3605s (max: 3600s), marking for removal
INFO - Stopping container for pbmc3k on port 5006
INFO - Cleaned up 1 inactive container(s)
```

## Benefits

- **Resource Efficiency**: Automatically frees up memory and CPU from unused containers
- **Cost Optimization**: Reduces resource consumption in cloud deployments
- **User Experience**: Containers start quickly on-demand, users don't notice the cleanup
- **Scalability**: Allows more concurrent users by recycling resources
