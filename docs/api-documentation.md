# Landing Page API Documentation

**Version**: 1.0.0  
**Base URL**: `http://localhost/api` (or your configured domain)

## Overview

The Landing Page API provides endpoints for discovering and managing single-cell datasets. All endpoints return JSON responses following the OpenAPI 3.0 specification defined in `specs/001-cellxgene-explorer/contracts/landing-page-api.yaml`.

## Authentication

**Current Version**: No authentication required (open access per FAIR principles)

**Future**: May add OAuth2/OIDC for user tracking and quota management.

## Endpoints

### Health Check

#### `GET /api/health`

Returns service health status. Used by Docker healthchecks and monitoring systems.

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T10:30:00Z",
  "dataset_count": 12
}
```

**Response Fields**:
- `status`: Service health status (always "healthy" if responding)
- `timestamp`: Current server time in ISO 8601 format
- `dataset_count`: Number of valid datasets available

**Use Cases**:
- Docker Compose healthcheck
- Monitoring system probes
- Startup validation

---

### List Datasets

#### `GET /api/datasets`

Returns catalog of all validated datasets with metadata.

**Query Parameters**:

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `organism` | string | No | Filter by organism | `Homo sapiens` |
| `tissue` | string | No | Filter by tissue type | `blood` |
| `sort` | string | No | Sort field: `name`, `cell_count`, `upload_date`, `file_size` | `cell_count` |
| `order` | string | No | Sort order: `asc`, `desc` | `desc` |

**Response**: `200 OK`
```json
{
  "datasets": [
    {
      "id": "pbmc_10k",
      "display_name": "Human PBMC 10k Dataset",
      "description": "10,000 peripheral blood mononuclear cells from a healthy donor",
      "organism": "Homo sapiens",
      "tissue": "blood",
      "assay": "10x 3' v3",
      "cell_count": 10000,
      "gene_count": 33538,
      "file_size_human": "2.3 GB",
      "upload_date": "2026-01-10"
    }
  ],
  "total": 1
}
```

**Response Fields (per dataset)**:
- `id`: Unique identifier (derived from filename without extension)
- `display_name`: Human-readable dataset name
- `description`: Detailed dataset description
- `organism`: Species (e.g., "Homo sapiens", "Mus musculus")
- `tissue`: Tissue or organ type
- `assay`: Sequencing technology (e.g., "10x 3' v3", "Smart-seq2")
- `cell_count`: Number of cells in dataset
- `gene_count`: Number of genes/features
- `file_size_human`: Human-readable file size (e.g., "2.3 GB")
- `upload_date`: Date dataset was added (ISO 8601 date format)

**Example Requests**:

```bash
# List all datasets
curl http://localhost/api/datasets

# Filter by organism
curl "http://localhost/api/datasets?organism=Homo%20sapiens"

# Filter by tissue
curl "http://localhost/api/datasets?tissue=brain"

# Sort by cell count (descending)
curl "http://localhost/api/datasets?sort=cell_count&order=desc"

# Combined filters
curl "http://localhost/api/datasets?organism=Homo%20sapiens&tissue=blood&sort=name&order=asc"
```

**Use Cases**:
- Display dataset catalog in web UI
- Search and filter datasets
- Generate reports or statistics

---

### Get Dataset Details

#### `GET /api/datasets/{dataset_id}`

Returns detailed information about a specific dataset.

**URL Parameters**:
- `dataset_id`: Unique dataset identifier (filename without extension)

**Response**: `200 OK`
```json
{
  "id": "pbmc_10k",
  "display_name": "Human PBMC 10k Dataset",
  "description": "10,000 peripheral blood mononuclear cells from a healthy donor",
  "filename": "pbmc_10k.h5ad",
  "organism": "Homo sapiens",
  "tissue": "blood",
  "assay": "10x 3' v3",
  "cell_count": 10000,
  "gene_count": 33538,
  "file_size_human": "2.3 GB",
  "file_size_bytes": 2468463616,
  "validation_status": "valid",
  "metadata_schema_version": "5.0.0",
  "contributors": [
    {
      "name": "Jane Doe",
      "institution": "Example University"
    }
  ],
  "citation": "Doe et al. (2025). Nature."
}
```

**Additional Fields** (compared to list endpoint):
- `filename`: Actual h5ad filename
- `file_size_bytes`: Exact file size in bytes
- `validation_status`: "valid" or "invalid"
- `metadata_schema_version`: singlecellschemas.org schema version
- `contributors`: Array of dataset contributors
- `citation`: Publication citation

**Error Response**: `404 Not Found`
```json
{
  "error": "dataset_not_found",
  "message": "Dataset 'nonexistent_id' does not exist",
  "recovery_hint": "Check that the dataset ID is correct and that the dataset exists in the data directory. Use the /api/datasets endpoint to list available datasets."
}
```

**Example Requests**:

```bash
# Get dataset details
curl http://localhost/api/datasets/pbmc_10k

# Handle errors
curl http://localhost/api/datasets/nonexistent_id
# Returns 404 with error message
```

**Use Cases**:
- Show detailed dataset information before launching
- Dataset metadata export
- Validation and debugging

---

### Launch CellXGene Viewer

#### `POST /api/datasets/{dataset_id}/launch`

Spawns a dedicated CellXGene container for the specified dataset. Returns URL to access the viewer and container status.

**URL Parameters**:
- `dataset_id`: Unique dataset identifier

**Response**: `200 OK`
```json
{
  "dataset_id": "pbmc_10k",
  "dataset_name": "Human PBMC 10k Dataset",
  "cellxgene_url": "http://localhost/cellxgene-pbmc_10k/",
  "container_port": 5006,
  "status": "ready",
  "timeout_info": "Container will be closed after 48 hours of inactivity"
}
```

**Response Fields**:
- `dataset_id`: Echo of requested dataset ID
- `dataset_name`: Human-readable dataset name
- `cellxgene_url`: Full URL to access CellXGene viewer
- `container_port`: Internal port allocated to container
- `status`: Container status (typically "ready")
- `timeout_info`: Information about automatic cleanup

**Error Responses**:

**404 Not Found** - Dataset does not exist:
```json
{
  "error_type": "DatasetNotFoundError",
  "message": "Dataset 'nonexistent_id' not found in catalog",
  "recovery_hint": "Check the dataset ID and try again"
}
```

**500 Internal Server Error** - Container launch failed:
```json
{
  "error_type": "RuntimeError",
  "message": "Failed to launch CellXGene container: No free ports available",
  "recovery_hint": "Please contact support if this persists"
}
```

**Example Requests**:

```bash
# Launch dataset
curl -X POST http://localhost/api/datasets/pbmc_10k/launch

# Response
{
  "dataset_id": "pbmc_10k",
  "dataset_name": "Human PBMC 10k Dataset",
  "cellxgene_url": "http://localhost/cellxgene-pbmc_10k/",
  "container_port": 5006,
  "status": "ready",
  "timeout_info": "Container will be closed after 48 hours of inactivity"
}
```

**Use Cases**:
- User clicks "Launch" button in web UI
- Programmatic dataset launching
- Automated workflows

**Notes**:
- Each dataset gets its own isolated container
- Container persists for 48 hours of inactivity
- If container already exists, returns existing container information
- Frontend should poll `/api/datasets/{dataset_id}/status` until ready

---

### Check Container Status

#### `GET /api/datasets/{dataset_id}/status`

Checks if a CellXGene container is running and ready for the specified dataset. Used by frontend to poll during startup.

**URL Parameters**:
- `dataset_id`: Unique dataset identifier

**Response**: `200 OK` (Container Ready)
```json
{
  "dataset_id": "pbmc_10k",
  "status": "running",
  "ready": true,
  "cellxgene_url": "http://localhost/cellxgene-pbmc_10k/",
  "container_port": 5006,
  "message": "Container is ready"
}
```

**Response**: `200 OK` (Container Starting)
```json
{
  "dataset_id": "pbmc_10k",
  "status": "starting",
  "ready": false,
  "cellxgene_url": null,
  "container_port": 5006,
  "message": "Container is starting..."
}
```

**Response**: `200 OK` (Container Not Running)
```json
{
  "dataset_id": "pbmc_10k",
  "status": "not_running",
  "ready": false,
  "message": "Container is not running"
}
```

**Response Fields**:
- `dataset_id`: Dataset identifier
- `status`: Container status ("running", "starting", or "not_running")
- `ready`: Boolean indicating if container is ready for access
- `cellxgene_url`: URL when ready, null otherwise
- `container_port`: Internal port (if container exists)
- `message`: Human-readable status message

**Example Requests**:

```bash
# Check status
curl http://localhost/api/datasets/pbmc_10k/status

# Poll until ready
while true; do
  STATUS=$(curl -s http://localhost/api/datasets/pbmc_10k/status | jq -r '.ready')
  [ "$STATUS" = "true" ] && break
  sleep 1
done
```

**Use Cases**:
- Frontend polling during container startup
- Monitoring container availability
- Health checking before redirect

**Notes**:
- Updates container access time (prevents premature cleanup)
- Safe to call repeatedly during polling

---

### Keep Container Alive

#### `POST /api/datasets/{dataset_id}/keepalive`

Updates the last access time for a container to prevent automatic cleanup. Useful for long-running analysis sessions.

**URL Parameters**:
- `dataset_id`: Unique dataset identifier

**Response**: `200 OK`
```json
{
  "dataset_id": "pbmc_10k",
  "status": "active",
  "message": "Container activity updated"
}
```

**Error Responses**:

**404 Not Found** - Container not running:
```json
{
  "dataset_id": "pbmc_10k",
  "status": "not_running",
  "message": "Container is not currently running"
}
```

**Example Requests**:

```bash
# Keep container alive
curl -X POST http://localhost/api/datasets/pbmc_10k/keepalive
```

**Use Cases**:
- Periodic heartbeat from frontend
- Long analysis sessions (>48 hours)
- Preventing timeout during active use

**Notes**:
- This endpoint is idempotent - launching same dataset multiple times is safe
- CellXGene viewer is shared among users (10 concurrent sessions max)
- Large datasets may take 10-30 seconds to fully load

---

### Get Dataset Metadata

#### `GET /api/datasets/{dataset_id}/metadata`

Returns the raw metadata JSON file for a dataset (singlecellschemas.org format).

**URL Parameters**:
- `dataset_id`: Unique dataset identifier

**Response**: `200 OK`
```json
{
  "title": "Human PBMC 10k Dataset",
  "description": "10,000 peripheral blood mononuclear cells from a healthy donor",
  "version": "1.0.0",
  "schema_version": "5.0.0",
  "contributors": [
    {
      "name": "Jane Doe",
      "institution": "Example University"
    }
  ],
  "organism": {
    "ontology": "NCBITaxon",
    "ontology_id": "NCBITaxon:9606",
    "text": "Homo sapiens"
  },
  "tissue": [
    {
      "ontology": "UBERON",
      "ontology_id": "UBERON:0000178",
      "text": "blood"
    }
  ],
  "assay": [
    {
      "ontology": "EFO",
      "ontology_id": "EFO:0009922",
      "text": "10x 3' v3"
    }
  ],
  "disease": [
    {
      "ontology": "MONDO",
      "ontology_id": "MONDO:0000001",
      "text": "normal"
    }
  ],
  "cell_count": 10000
}
```

**Error Response**: `404 Not Found`
```json
{
  "error": "dataset_not_found",
  "message": "Dataset 'nonexistent_id' does not exist"
}
```

**Example Requests**:

```bash
# Get raw metadata
curl http://localhost/api/datasets/pbmc_10k/metadata

# Save to file
curl http://localhost/api/datasets/pbmc_10k/metadata > pbmc_10k_metadata.json
```

**Use Cases**:
- Metadata export and analysis
- Schema validation
- Dataset provenance tracking
- Integration with other tools

---

## Error Handling

All error responses follow a consistent format:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "recovery_hint": "Suggestion for how to fix the error"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `dataset_not_found` | 404 | Requested dataset does not exist |
| `validation_error` | 400 | Invalid request parameters |
| `service_unavailable` | 503 | CellXGene service is unavailable |
| `internal_error` | 500 | Unexpected server error |

### Best Practices for Error Handling

1. **Check HTTP status code first**: Use standard HTTP status codes for flow control
2. **Parse error field**: Use `error` field for programmatic error handling
3. **Display message to user**: `message` field is human-readable
4. **Show recovery hint**: Display `recovery_hint` to help users fix the issue

---

## Rate Limiting

**Current Version**: No rate limiting

**Future**: May add rate limiting to prevent abuse:
- 100 requests per minute per IP address
- 10 concurrent CellXGene sessions per IP address

---

## CORS (Cross-Origin Resource Sharing)

API endpoints include CORS headers to allow web access from different origins:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

**Note**: In production deployments, consider restricting `Access-Control-Allow-Origin` to specific domains.

---

## Pagination

**Current Version**: No pagination - all datasets returned in single response

**Future**: For catalogs with 100+ datasets, pagination will be added:

```
GET /api/datasets?page=1&per_page=20
```

---

## Versioning

**Current Version**: 1.0.0

API follows semantic versioning. Breaking changes will increment major version (e.g., 2.0.0).

Future versions may be accessed via URL path:
```
/api/v2/datasets
```

---

## SDK and Client Libraries

**Current Version**: No official SDKs

**Future**: Client libraries may be provided for:
- Python
- JavaScript/TypeScript
- R

Example Python usage:
```python
import cellxgene_client

client = cellxgene_client.Client("http://localhost/api")
datasets = client.list_datasets(organism="Homo sapiens")
viewer_url = client.launch_dataset("pbmc_10k")
```

---

## Performance

- **Health Check**: < 100ms response time
- **List Datasets**: < 500ms for 50 datasets
- **Get Dataset**: < 200ms
- **Launch Dataset**: < 1 second (excluding CellXGene load time)

---

## OpenAPI Specification

Full OpenAPI 3.0 specification available at:
`specs/001-cellxgene-explorer/contracts/landing-page-api.yaml`

Interactive API documentation can be generated using tools like:
- Swagger UI
- ReDoc
- Postman

---

## Support

For issues or questions:
- Check [troubleshooting guide](troubleshooting.md)
- Review [architecture documentation](architecture.md)
- Open an issue on the project repository
