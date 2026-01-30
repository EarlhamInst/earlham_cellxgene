"""
Dataset Model

Represents a single-cell dataset with its h5ad file and metadata.

Constitutional Alignment:
- Principle II (Modular Architecture): Clear data model boundaries
- Principle III (Code Clarity): Well-documented attributes
- Principle I (Unit Testing): Designed for testability
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib


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
    additional_metadata: Optional[Dict[str, Any]] = None  # For storing extra obs metadata

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
