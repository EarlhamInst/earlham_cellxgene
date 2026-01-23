# CellXGene Container Inactivity Timeout

## Overview
CellXGene containers are now automatically closed after **48 hours of inactivity** to optimize resource usage while providing ample time for extended analysis sessions.

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
- **Timeout**: 48 hours (172,800 seconds) of inactivity
- **Graceful shutdown**: Scheduler properly shuts down when application terminates

### 3. API Routes (`services/landing-page/src/routes/datasets.py`)
- **Enhanced launch response**: Now includes "Container will be closed after 48 hours of inactivity"
- **Status endpoint**: `/api/datasets/<dataset_id>/status` (GET) - polls until container ready, updates access time
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
   - Updated when frontend polls status endpoint during startup
   - Can be manually updated via the `/keepalive` endpoint
3. **Background Cleanup**: Every 5 minutes, a background job:
   - Checks all active containers
   - Calculates time since last access
   - Stops containers inactive for more than 48 hours
4. **Container Removal**: Stopped containers are automatically removed (Docker `auto_remove=True`)
5. **Error Handling**: Nginx shows a friendly error page if users try to access closed containers

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
        max_inactive_seconds=172800  # 48 hours in seconds - change this value
    ),
    trigger='interval',
    minutes=5,  # Change cleanup frequency here
    ...
)
```

**Note**: Also update the timeout message in:
- `services/landing-page/src/routes/datasets.py` (launch endpoint response)
- `services/nginx/nginx.conf` (error page message)

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
INFO - Container pbmc3k inactive for 172805s (max: 172800s), marking for removal
INFO - Stopping container for pbmc3k on port 5006
INFO - Cleaned up 1 inactive container(s)
```

## Benefits

- **Resource Efficiency**: Automatically frees up memory and CPU from unused containers
- **User-Friendly**: 48-hour window allows for multi-day analysis sessions without interruption
- **Cost Optimization**: Reduces resource consumption in cloud deployments
- **Seamless Experience**: Containers start quickly on-demand, status polling prevents bad gateway errors
- **Scalability**: Allows more concurrent users by recycling resources
- **Error Handling**: Custom nginx error page guides users back to relaunch closed containers
