#!/bin/bash
# CellXGene Service Entrypoint
#
# Validates environment and starts CellXGene with Gunicorn.
#
# Constitutional Alignment:
# - Principle IV (Fail-Fast): Validates before starting

set -e

echo "=========================================="
echo "CellXGene Service Starting"
echo "=========================================="

# Get configuration from environment
DATA_DIR="${DATA_DIRECTORY:-/data/datasets}"
echo "Using data directory: $DATA_DIR"
WORKERS="${WORKERS:-10}"
TIMEOUT="${TIMEOUT:-300}"

echo "Configuration:"
echo "  Data directory: $DATA_DIR"
echo "  Workers: $WORKERS"
echo "  Timeout: $TIMEOUT seconds"

# Validate data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "ERROR: Data directory not found: $DATA_DIR"
    echo "Fix: Ensure volume mount is configured in docker-compose.yml"
    exit 1
fi

# Check if data directory is readable
if [ ! -r "$DATA_DIR" ]; then
    echo "ERROR: Data directory is not readable: $DATA_DIR"
    echo "Fix: Check volume mount permissions"
    exit 1
fi

# Count h5ad files
H5AD_COUNT=$(find "$DATA_DIR" -name "*.h5ad" -type f 2>/dev/null | wc -l)
echo "Found $H5AD_COUNT h5ad files in data directory"

if [ "$H5AD_COUNT" -eq 0 ]; then
    echo "WARNING: No h5ad files found in $DATA_DIR"
    echo "CellXGene will start but no datasets will be available"
fi

echo "=========================================="
echo "Starting CellXGene"
echo "=========================================="

# Determine which dataset file to launch
if [ -n "$DATASET_FILE" ]; then
    # Dynamic container mode: launch specific dataset
    TARGET_H5AD="$DATA_DIR/$DATASET_FILE"
    
    if [ ! -f "$TARGET_H5AD" ]; then
        echo "ERROR: Specified dataset file not found: $TARGET_H5AD"
        exit 1
    fi
    
    echo "Launching CellXGene for dataset: $DATASET_FILE"
else
    # Legacy mode: launch first h5ad file (for backward compatibility)
    TARGET_H5AD=$(find "$DATA_DIR" -name "*.h5ad" -type f 2>/dev/null | sort | head -n 1)
    
    if [ -z "$TARGET_H5AD" ]; then
        echo "ERROR: No h5ad files found in $DATA_DIR"
        echo "CellXGene requires at least one dataset file to start"
        exit 1
    fi
    
    echo "Launching CellXGene with first available dataset: $(basename "$TARGET_H5AD")"
    echo ""
    echo "NOTE: To launch a specific dataset, set DATASET_FILE environment variable"
    echo "Available datasets:"
    find "$DATA_DIR" -name "*.h5ad" -type f 2>/dev/null | sort | while read file; do
        echo "  - $(basename "$file")"
    done
    echo ""
fi

exec cellxgene launch "$TARGET_H5AD" \
  --host 0.0.0.0 \
  --port 5005 \
  --disable-annotations \
  --disable-gene-sets-save \
  --backed


