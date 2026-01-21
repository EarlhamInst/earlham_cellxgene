# Data Model: CellXGene Explorer

**Feature**: 001-cellxgene-explorer  
**Date**: 2026-01-14  
**Purpose**: Define entities, relationships, and data structures

## Overview

The CellXGene Explorer data model is intentionally simple, focusing on datasets and their metadata. There is no persistent database - all data is file-based for simplicity and alignment with FAIR principles.

## Entities

### 1. Dataset

Represents a single-cell analysis dataset stored as an h5ad file.

**Attributes**:
- `id` (string, required): Unique identifier, derived from filename (e.g., "pbmc_10k")
- `filename` (string, required): Name of the h5ad file (e.g., "pbmc_10k.h5ad")
- `filepath` (string, required): Absolute path to h5ad file
- `display_name` (string, required): Human-readable name for UI display
- `description` (string, optional): Detailed description of the dataset
- `organism` (string, optional): Species (e.g., "Homo sapiens", "Mus musculus")
- `tissue` (string, optional): Tissue type (e.g., "peripheral blood", "brain")
- `cell_count` (integer, optional): Total number of cells
- `feature_count` (integer, optional): Total number of genes/features
- `upload_date` (ISO 8601 date, required): When dataset was added
- `file_size_bytes` (integer, required): Size of h5ad file in bytes
- `file_size_human` (string, computed): Human-readable size (e.g., "2.3 GB")
- `metadata_path` (string, required): Path to JSON metadata file
- `is_valid` (boolean, computed): Whether dataset passes validation
- `validation_errors` (list of strings, computed): Error messages if invalid

**Lifecycle**:
1. Created when h5ad file and metadata JSON are placed in data directory
2. Validated on service startup (fail-fast if invalid)
3. Served to users via landing page catalog
4. Removed when files are deleted from data directory

**Validation Rules**:
- h5ad file MUST exist and be readable
- h5ad file MUST be valid AnnData format
- Metadata JSON MUST exist
- Metadata JSON MUST conform to http://singlecellschemas.org schema
- `filename` MUST match pattern `*.h5ad`
- `file_size_bytes` MUST be > 0

**State Transitions**:
```
[File Added] → [Pending Validation] → [Valid] → [Available to Users]
                                    ↓
                                [Invalid] → [Service Fails to Start]
```

---

### 2. DatasetMetadata

Configuration and descriptive information for a dataset, stored as JSON conforming to http://singlecellschemas.org.

**File Structure** (per singlecellschemas.org):
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
  "cell_count": 10000,
  "feature_count": 33538,
  "suspension_type": "cell",
  "citation": "Doe et al. (2025). Example single-cell study. Nature.",
  "dataset_id": "pbmc_10k"
}
```

**Required Fields** (per schema):
- `title`
- `schema_version`
- `organism`
- `cell_count`

**Optional Fields**:
- `description`
- `version`
- `contributors`
- `tissue`
- `assay`
- `disease`
- `suspension_type`
- `citation`
- `dataset_id`

**Validation**:
- MUST be valid JSON
- MUST conform to singlecellschemas.org JSON schema
- MUST have all required fields
- Ontology IDs SHOULD be valid (warning if invalid, not failure)

---

### 3. ServiceConfiguration

System-level configuration for the CellXGene Explorer stack.

**Attributes** (defined in docker-compose.yml and .env):
- `data_directory` (string): Path to volume-mounted dataset directory
- `cellxgene_port` (integer): Internal port for CellXGene service (default: 5005)
- `landing_page_port` (integer): Internal port for landing page (default: 8000)
- `nginx_port` (integer): External port for Nginx (default: 80)
- `worker_count` (integer): Number of Gunicorn workers (fixed: 10)
- `worker_memory_mb` (integer): Memory limit per worker (fixed: 4096)
- `log_directory` (string): Path to log output
- `validation_mode` (enum): "strict" (fail-fast) or "permissive" (log warnings)

**Example .env File**:
```bash
DATA_DIRECTORY=/data/datasets
LOG_DIRECTORY=/data/logs
NGINX_PORT=80
CELLXGENE_PORT=5005
LANDING_PAGE_PORT=8000
WORKER_COUNT=10
WORKER_MEMORY_MB=4096
VALIDATION_MODE=strict
```

---

### 4. AccessLog

Usage tracking for dataset access. Stored as structured logs (JSON lines).

**Attributes**:
- `timestamp` (ISO 8601 datetime): When dataset was accessed
- `dataset_id` (string): Which dataset was opened
- `client_ip` (string): User's IP address (anonymized if needed)
- `user_agent` (string): Browser/client identifier
- `action` (enum): "view_catalog", "launch_dataset", "error"
- `duration_seconds` (float, optional): Time spent (for launch actions)
- `error_message` (string, optional): If action resulted in error

**Storage**: Append-only log file (JSON lines)

**Example Log Entry**:
```json
{"timestamp": "2026-01-14T10:30:00Z", "dataset_id": "pbmc_10k", "client_ip": "192.168.1.100", "action": "launch_dataset", "user_agent": "Mozilla/5.0..."}
```

---

## Relationships

```
ServiceConfiguration
        |
        | configures
        ↓
LandingPageService --[scans]--> DataDirectory --[contains]--> Dataset (*.h5ad)
                                                                    |
                                                                    | has metadata
                                                                    ↓
                                                            DatasetMetadata (*.json)
                                                                    |
                                                                    | conforms to
                                                                    ↓
                                                          singlecellschemas.org
                                
CellXGeneService --[loads]--> Dataset (*.h5ad)
        |
        | generates
        ↓
AccessLog
```

**Key Relationships**:
1. **One-to-One**: Each Dataset has exactly one DatasetMetadata file
2. **One-to-Many**: One DataDirectory contains many Datasets
3. **One-to-Many**: One CellXGeneService can serve many Datasets (via workers)
4. **Many-to-Many**: Multiple users can access multiple Datasets (tracked in AccessLog)

---

## Data Flow

### Startup Flow
```
1. ServiceConfiguration loaded from .env
2. Dataset Validator scans DATA_DIRECTORY
3. For each *.h5ad file:
   a. Check corresponding *.json exists
   b. Validate h5ad format
   c. Validate JSON against schema
   d. Create Dataset object
4. If ANY validation fails → Fail-fast (service won't start)
5. If all valid → Serve dataset catalog via Landing Page
```

### User Access Flow
```
1. User visits landing page (/)
2. Landing Page queries Dataset catalog
3. User clicks dataset → Request to CellXGene service
4. Nginx routes /cellxgene/* to CellXGene
5. CellXGene loads dataset from volume mount
6. Access logged to AccessLog
7. CellXGene serves interactive visualization
```

---

## File System Layout

```
/data/
├── datasets/                      # Volume mount point
│   ├── pbmc_10k.h5ad             # Dataset file
│   ├── pbmc_10k.json             # Metadata (singlecellschemas.org)
│   ├── brain_cortex.h5ad         # Another dataset
│   ├── brain_cortex.json         # Its metadata
│   └── ...
│
└── logs/                          # Volume mount point
    ├── access.log                # AccessLog entries
    ├── cellxgene.log             # CellXGene service logs
    └── landing-page.log          # Landing page service logs
```

---

## Data Validation Rules

### H5AD File Validation
- File extension MUST be `.h5ad`
- File MUST be readable by AnnData library
- File MUST contain `obs`, `var`, and `X` attributes (minimum AnnData structure)
- File size MUST be < configured limit (default: 10GB, configurable)

### Metadata JSON Validation
- File extension MUST be `.json`
- Filename MUST match h5ad filename (e.g., `dataset.h5ad` → `dataset.json`)
- Content MUST be valid JSON
- JSON MUST validate against singlecellschemas.org JSON schema
- `cell_count` in JSON SHOULD match actual cell count in h5ad (warning if mismatch)

### Startup Validation
- ALL datasets MUST pass validation before service starts
- Validation errors MUST be logged with:
  - Dataset filename
  - Specific error message
  - Suggested fix
- If validation fails → Service exits with non-zero status code

---

## Security Considerations

### Data Privacy
- No authentication required (open access per FAIR principles)
- Consider IP anonymization in AccessLog for privacy compliance
- Datasets assumed to be non-sensitive or pre-approved for public access

### Input Validation
- Metadata JSON parsed safely (no `eval()` or code execution)
- File paths validated to prevent directory traversal
- Dataset IDs sanitized to prevent injection attacks

### Resource Limits
- Per-worker memory limits prevent single dataset from consuming all RAM
- File size limits prevent disk exhaustion
- No user-uploaded datasets (admin-curated only)

---

## Extensibility

### Adding New Metadata Fields
1. Extend singlecellschemas.org schema (upstream)
2. Update validation logic to support new fields
3. Update Landing Page UI to display new fields

### Supporting Additional File Formats
1. Add format detection logic
2. Extend validation to support new format
3. Ensure CellXGene supports format (or add converter)

### Multi-User Sessions
Current design supports concurrent users through worker pool. For true multi-session support:
1. Add session management to CellXGene service
2. Track active sessions in shared state (Redis)
3. Route users to available workers

---

**Status**: Data model complete and aligned with spec requirements.
