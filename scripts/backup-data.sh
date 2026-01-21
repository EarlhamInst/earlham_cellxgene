#!/usr/bin/env bash
"""
Backup Utility for CellXGene Explorer Data

Creates timestamped backups of datasets and logs.

Constitutional Alignment:
- Principle V (Documentation): Clear usage instructions
- Principle III (Code Clarity): Simple, understandable backup process
"""

set -e  # Exit on any error
set -u  # Exit on undefined variable

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Configuration
DATA_DIR="${DATA_DIR:-$PROJECT_ROOT/data}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="cellxgene_backup_$TIMESTAMP"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  CellXGene Explorer - Backup Utility${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Creating backup: $BACKUP_NAME"
echo "Source: $DATA_DIR"
echo "Destination: $BACKUP_DIR/$BACKUP_NAME"
echo ""

# Create tar archive
if tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C "$DATA_DIR" .; then
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    
    # Show backup size
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)
    echo "Backup size: $BACKUP_SIZE"
    echo "Location: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
    
    # List all backups
    echo ""
    echo "All backups:"
    ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "No previous backups found"
    
else
    echo "✗ Backup failed"
    exit 1
fi

echo ""
echo "To restore this backup:"
echo "  tar -xzf $BACKUP_DIR/$BACKUP_NAME.tar.gz -C $DATA_DIR"
echo ""
