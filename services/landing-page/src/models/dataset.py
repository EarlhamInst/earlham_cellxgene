"""
Dataset Model

Represents a single-cell dataset with its h5ad file and metadata.

Constitutional Alignment:
- Principle II (Modular Architecture): Clear data model boundaries
- Principle III (Code Clarity): Well-documented attributes
- Principle I (Unit Testing): Designed for testability
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import hashlib
import json

if TYPE_CHECKING:
    from ..services.database import Database


# Visibility levels for datasets
VISIBILITY_PUBLIC = "public"
VISIBILITY_UNLISTED = "unlisted"
VISIBILITY_PRIVATE = "private"

# Source types for datasets
SOURCE_CURATED = "curated"
SOURCE_USER_UPLOAD = "user_upload"


@dataclass
class Dataset:
    """
    Represents a single-cell dataset.

    Attributes:
        id: Unique identifier (derived from filename)
        filename: Name of the h5ad file
        filepath: Full path to the h5ad file
        display_name: Human-readable name from metadata
        description: Dataset description from metadata
        organism: Organism name
        tissue: Tissue type
        assay: Assay type
        cell_count: Number of cells in dataset
        gene_count: Number of genes in dataset
        doi: Optional DOI for publication
        publication: Optional publication reference
        file_size_bytes: Size of h5ad file in bytes
        is_valid: Whether dataset passed validation
        validation_errors: List of validation errors (if any)
        owner_orcid: ORCID iD of owner (None = curated)
        visibility: public | unlisted | private
        source: curated | user_upload
        view_count: Number of times dataset has been viewed
        created_at: When dataset was added
        updated_at: When dataset was last updated
    """

    id: str
    filename: str
    filepath: Path
    display_name: str
    description: str
    organism: str
    tissue: str
    assay: str
    cell_count: Optional[int] = None
    gene_count: Optional[int] = None
    doi: Optional[str] = None
    publication: Optional[str] = None
    file_size_bytes: Optional[int] = None
    is_valid: bool = True
    validation_errors: list = None
    additional_metadata: Optional[Dict[str, Any]] = None
    # New fields for user uploads
    owner_orcid: Optional[str] = None
    visibility: str = VISIBILITY_PUBLIC
    source: str = SOURCE_CURATED
    view_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """Initialize after dataclass creation."""
        if self.validation_errors is None:
            self.validation_errors = []
        
        if self.additional_metadata is None:
            self.additional_metadata = {}

        # Ensure filepath is a Path object
        if not isinstance(self.filepath, Path):
            self.filepath = Path(self.filepath)

        # Calculate file size if not provided
        if self.file_size_bytes is None and self.filepath.exists():
            self.file_size_bytes = self.filepath.stat().st_size
        
        # Set timestamps if not provided
        now = datetime.utcnow().isoformat()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    @classmethod
    def from_files(cls, h5ad_path: Path, metadata: Dict[str, Any]) -> "Dataset":
        """
        Create a Dataset instance from h5ad file and metadata.

        Args:
            h5ad_path: Path to the h5ad file
            metadata: Metadata dictionary (extracted from h5ad file)

        Returns:
            Dataset instance
        """
        # Generate unique ID from filename
        dataset_id = h5ad_path.stem  # filename without extension

        return cls(
            id=dataset_id,
            filename=h5ad_path.name,
            filepath=h5ad_path,
            display_name=metadata.get("name", dataset_id),
            description=metadata.get("description", ""),
            organism=metadata.get("organism", "Unknown"),
            tissue=metadata.get("tissue", "Unknown"),
            assay=metadata.get("assay", "Unknown"),
            cell_count=metadata.get("cell_count"),
            gene_count=metadata.get("gene_count"),
            doi=metadata.get("doi"),
            publication=metadata.get("publication"),
            is_valid=True,
            validation_errors=[],
            additional_metadata=metadata.get("additional_metadata", {}),
        )

    def to_dict(self, include_filepath: bool = False) -> Dict[str, Any]:
        """
        Convert dataset to dictionary for API responses.

        Args:
            include_filepath: Whether to include full filepath (default: False for security)

        Returns:
            Dictionary representation of dataset
        """
        result = asdict(self)

        # Convert Path to string
        if include_filepath:
            result["filepath"] = str(self.filepath)
        else:
            del result["filepath"]  # Don't expose full path in API

        # Format file size as human-readable
        if self.file_size_bytes:
            result["file_size_human"] = self._format_file_size(self.file_size_bytes)

        return result

    @staticmethod
    def _format_file_size(bytes_size: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            bytes_size: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 GB")
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"

    def get_checksum(self) -> str:
        """
        Calculate MD5 checksum of h5ad file.

        Returns:
            MD5 checksum hex string
        """
        md5 = hashlib.md5()

        with open(self.filepath, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)

        return md5.hexdigest()

    def validate(self) -> bool:
        """
        Validate dataset (check file exists, is readable, etc.).

        Returns:
            True if valid, False otherwise (updates is_valid and validation_errors)
        """
        self.validation_errors = []

        # Check file exists
        if not self.filepath.exists():
            self.validation_errors.append(f"File does not exist: {self.filepath}")
            self.is_valid = False
            return False

        # Check file is readable
        if not self.filepath.is_file():
            self.validation_errors.append(f"Path is not a file: {self.filepath}")
            self.is_valid = False
            return False

        # Check file is not empty
        if self.filepath.stat().st_size == 0:
            self.validation_errors.append(f"File is empty: {self.filepath}")
            self.is_valid = False
            return False

        # Check required metadata fields
        # Only display_name and description are strictly required
        # organism, tissue, assay can be 'Unknown'
        required_fields = {
            "display_name": self.display_name,
            "description": self.description,
        }

        for field, value in required_fields.items():
            if not value or not str(value).strip():
                self.validation_errors.append(
                    f"Missing or invalid required field: {field}"
                )

        # Check that organism, tissue, assay exist (can be 'Unknown')
        if not self.organism:
            self.validation_errors.append("Missing field: organism")
        if not self.tissue:
            self.validation_errors.append("Missing field: tissue")
        if not self.assay:
            self.validation_errors.append("Missing field: assay")

        self.is_valid = len(self.validation_errors) == 0
        return self.is_valid

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Dataset(id='{self.id}', name='{self.display_name}', valid={self.is_valid})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.display_name} ({self.filename})"
    
    def is_public(self) -> bool:
        """Check if dataset is publicly visible."""
        return self.visibility == VISIBILITY_PUBLIC
    
    def is_unlisted(self) -> bool:
        """Check if dataset is unlisted (accessible via link)."""
        return self.visibility == VISIBILITY_UNLISTED
    
    def is_private(self) -> bool:
        """Check if dataset is private."""
        return self.visibility == VISIBILITY_PRIVATE
    
    def is_user_uploaded(self) -> bool:
        """Check if dataset was uploaded by a user."""
        return self.source == SOURCE_USER_UPLOAD
    
    def is_curated(self) -> bool:
        """Check if dataset is a curated dataset."""
        return self.source == SOURCE_CURATED
    
    def is_owned_by(self, orcid_id: Optional[str]) -> bool:
        """Check if dataset is owned by a specific user."""
        if self.owner_orcid is None:
            return False  # Curated datasets have no owner
        return self.owner_orcid == orcid_id


class DatasetStoreSQLite:
    """
    SQLite-backed storage for datasets.
    
    Provides CRUD operations for datasets stored in SQLite.
    """
    
    def __init__(self, database: "Database"):
        """
        Initialize the store.
        
        Args:
            database: Database instance from services.database
        """
        self.db = database
    
    def _row_to_dataset(self, row) -> Dataset:
        """Convert a database row to Dataset."""
        # Parse validation_errors and additional_metadata from JSON
        validation_errors = []
        if row['validation_errors']:
            try:
                validation_errors = json.loads(row['validation_errors'])
            except json.JSONDecodeError:
                validation_errors = [row['validation_errors']]
        
        additional_metadata = {}
        if row['additional_metadata']:
            try:
                additional_metadata = json.loads(row['additional_metadata'])
            except json.JSONDecodeError:
                pass
        
        return Dataset(
            id=row['id'],
            filename=row['filename'],
            filepath=Path(row['filepath']),
            display_name=row['display_name'],
            description=row['description'] or '',
            organism=row['organism'] or 'Unknown',
            tissue=row['tissue'] or 'Unknown',
            assay=row['assay'] or 'Unknown',
            cell_count=row['cell_count'],
            gene_count=row['gene_count'],
            doi=row['doi'],
            publication=row['publication'],
            file_size_bytes=row['file_size_bytes'],
            is_valid=bool(row['is_valid']),
            validation_errors=validation_errors,
            additional_metadata=additional_metadata,
            owner_orcid=row['owner_orcid'],
            visibility=row['visibility'] or VISIBILITY_PUBLIC,
            source=row['source'] or SOURCE_CURATED,
            view_count=row['view_count'] or 0,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )
    
    def save(self, dataset: Dataset) -> None:
        """Save or update a dataset."""
        now = datetime.utcnow().isoformat()
        
        # Serialize validation_errors and additional_metadata to JSON
        validation_errors_json = json.dumps(dataset.validation_errors) if dataset.validation_errors else None
        additional_metadata_json = json.dumps(dataset.additional_metadata) if dataset.additional_metadata else None
        
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO datasets 
                (id, filename, filepath, display_name, description, organism, tissue, assay,
                 cell_count, gene_count, file_size_bytes, doi, publication, owner_orcid,
                 visibility, source, is_valid, validation_errors, additional_metadata,
                 created_at, updated_at, view_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset.id,
                dataset.filename,
                str(dataset.filepath),
                dataset.display_name,
                dataset.description,
                dataset.organism,
                dataset.tissue,
                dataset.assay,
                dataset.cell_count,
                dataset.gene_count,
                dataset.file_size_bytes,
                dataset.doi,
                dataset.publication,
                dataset.owner_orcid,
                dataset.visibility,
                dataset.source,
                1 if dataset.is_valid else 0,
                validation_errors_json,
                additional_metadata_json,
                dataset.created_at or now,
                now,
                dataset.view_count,
            ))
    
    def get_by_id(self, dataset_id: str) -> Optional[Dataset]:
        """Get a dataset by ID."""
        row = self.db.execute_one(
            "SELECT * FROM datasets WHERE id = ?",
            (dataset_id,)
        )
        if row:
            return self._row_to_dataset(row)
        return None
    
    def get_all(self) -> List[Dataset]:
        """Get all datasets."""
        rows = self.db.execute("SELECT * FROM datasets ORDER BY display_name")
        return [self._row_to_dataset(row) for row in rows]
    
    def get_public(self) -> List[Dataset]:
        """Get all public datasets (for main catalog)."""
        rows = self.db.execute(
            "SELECT * FROM datasets WHERE visibility = ? AND is_valid = 1 ORDER BY display_name",
            (VISIBILITY_PUBLIC,)
        )
        return [self._row_to_dataset(row) for row in rows]
    
    def get_by_owner(self, orcid_id: str) -> List[Dataset]:
        """Get all datasets owned by a user."""
        rows = self.db.execute(
            "SELECT * FROM datasets WHERE owner_orcid = ? ORDER BY created_at DESC",
            (orcid_id,)
        )
        return [self._row_to_dataset(row) for row in rows]
    
    def get_curated(self) -> List[Dataset]:
        """Get all curated datasets."""
        rows = self.db.execute(
            "SELECT * FROM datasets WHERE source = ? AND is_valid = 1 ORDER BY display_name",
            (SOURCE_CURATED,)
        )
        return [self._row_to_dataset(row) for row in rows]
    
    def delete(self, dataset_id: str) -> bool:
        """Delete a dataset by ID."""
        affected = self.db.execute_write(
            "DELETE FROM datasets WHERE id = ?",
            (dataset_id,)
        )
        return affected > 0
    
    def update_visibility(self, dataset_id: str, visibility: str) -> bool:
        """Update dataset visibility."""
        if visibility not in (VISIBILITY_PUBLIC, VISIBILITY_UNLISTED, VISIBILITY_PRIVATE):
            raise ValueError(f"Invalid visibility: {visibility}")
        
        affected = self.db.execute_write(
            "UPDATE datasets SET visibility = ?, updated_at = ? WHERE id = ?",
            (visibility, datetime.utcnow().isoformat(), dataset_id)
        )
        return affected > 0
    
    def increment_view_count(self, dataset_id: str) -> None:
        """Increment view count for a dataset."""
        self.db.execute_write(
            "UPDATE datasets SET view_count = view_count + 1 WHERE id = ?",
            (dataset_id,)
        )
    
    def sync_curated_datasets(self, datasets: List[Dataset]) -> Dict[str, int]:
        """
        Sync curated datasets from filesystem scan.
        
        Inserts new datasets, updates existing ones, removes deleted ones.
        
        Args:
            datasets: List of datasets from filesystem scan
            
        Returns:
            Dict with counts: added, updated, removed
        """
        stats = {"added": 0, "updated": 0, "removed": 0}
        
        # Get existing curated dataset IDs
        rows = self.db.execute(
            "SELECT id FROM datasets WHERE source = ?",
            (SOURCE_CURATED,)
        )
        existing_ids = {row['id'] for row in rows}
        new_ids = {ds.id for ds in datasets}
        
        # Insert/update datasets
        for dataset in datasets:
            dataset.source = SOURCE_CURATED
            dataset.visibility = VISIBILITY_PUBLIC
            
            if dataset.id in existing_ids:
                stats["updated"] += 1
            else:
                stats["added"] += 1
            
            self.save(dataset)
        
        # Remove datasets no longer on filesystem
        removed_ids = existing_ids - new_ids
        for dataset_id in removed_ids:
            self.delete(dataset_id)
            stats["removed"] += 1
        
        return stats
