"""
Dataset Metadata Model

Represents metadata conforming to singlecellschemas.org standards.

Constitutional Alignment:
- Principle IV (Fail-Fast): Validates metadata on load
- Principle III (Code Clarity): Clear schema definition
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class DatasetMetadata:
    """
    Dataset metadata conforming to singlecellschemas.org standards.

    Required fields per singlecellschemas.org:
    - name: Human-readable dataset name
    - description: Detailed dataset description
    - organism: Scientific name of organism
    - tissue: Tissue or organ type
    - assay: Sequencing/assay technology

    Optional but recommended fields:
    - cell_count: Number of cells
    - gene_count: Number of genes
    - doi: Digital Object Identifier for publication
    - publication: Full citation
    - contributors: List of contributor names
    - version: Dataset version
    - date_created: Creation date
    - license: Data license
    - tags: Searchable tags
    """

    # Required fields
    name: str
    description: str
    organism: str
    tissue: str
    assay: str

    # Optional fields
    cell_count: Optional[int] = None
    gene_count: Optional[int] = None
    doi: Optional[str] = None
    publication: Optional[str] = None
    contributors: Optional[List[str]] = None
    version: Optional[str] = None
    date_created: Optional[str] = None
    license: Optional[str] = None
    tags: Optional[List[str]] = None

    # Additional custom fields
    custom_fields: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate after initialization."""
        if self.custom_fields is None:
            self.custom_fields = {}

        if self.contributors is None:
            self.contributors = []

        if self.tags is None:
            self.tags = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetMetadata":
        """
        Create metadata instance from dictionary.

        Args:
            data: Dictionary with metadata fields

        Returns:
            DatasetMetadata instance

        Raises:
            ValueError: If required fields are missing
        """
        # Check required fields - name and description must be present
        # organism, tissue, assay can be 'Unknown'
        required_fields = ["name", "description"]
        missing_fields = [f for f in required_fields if f not in data or not data[f]]

        if missing_fields:
            raise ValueError(
                f"Missing required metadata fields: {', '.join(missing_fields)}"
            )

        # Ensure organism, tissue, assay exist (with defaults)
        for field in ["organism", "tissue", "assay"]:
            if field not in data or not data[field]:
                data[field] = "Unknown"

        # Extract known fields
        known_fields = {
            "name",
            "description",
            "organism",
            "tissue",
            "assay",
            "cell_count",
            "gene_count",
            "doi",
            "publication",
            "contributors",
            "version",
            "date_created",
            "license",
            "tags",
        }

        # Separate known fields from custom fields
        metadata_kwargs = {}
        custom_fields = {}

        for key, value in data.items():
            if key in known_fields:
                metadata_kwargs[key] = value
            else:
                custom_fields[key] = value

        metadata_kwargs["custom_fields"] = custom_fields

        return cls(**metadata_kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to dictionary.

        Returns:
            Dictionary with all metadata fields
        """
        result = asdict(self)

        # Remove None values for cleaner output
        result = {k: v for k, v in result.items() if v is not None}

        # Merge custom fields into main dict
        if "custom_fields" in result:
            custom = result.pop("custom_fields")
            result.update(custom)

        return result

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate metadata.

        Only name and description are strictly required to be non-empty.
        organism, tissue, assay must exist but can be 'Unknown'.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check strictly required fields (must be non-empty)
        if not self.name or not str(self.name).strip():
            errors.append("Required field 'name' is empty or missing")

        if not self.description or not str(self.description).strip():
            errors.append("Required field 'description' is empty or missing")

        # Check that organism, tissue, assay exist (can be "Unknown")
        if not self.organism:
            errors.append(
                "Field 'organism' is missing (should be present, can be 'Unknown')"
            )

        if not self.tissue:
            errors.append(
                "Field 'tissue' is missing (should be present, can be 'Unknown')"
            )

        if not self.assay:
            errors.append(
                "Field 'assay' is missing (should be present, can be 'Unknown')"
            )

        # Validate numeric fields if present
        if self.cell_count is not None:
            if not isinstance(self.cell_count, int) or self.cell_count < 0:
                errors.append("cell_count must be a non-negative integer")

        if self.gene_count is not None:
            if not isinstance(self.gene_count, int) or self.gene_count < 0:
                errors.append("gene_count must be a non-negative integer")

        # Validate date format if present
        if self.date_created:
            try:
                datetime.fromisoformat(self.date_created.replace("Z", "+00:00"))
            except ValueError:
                errors.append(
                    f"date_created must be in ISO format (e.g., 2024-01-15T10:30:00Z), "
                    f"got: {self.date_created}"
                )

        # Validate DOI format if present
        if self.doi and not (self.doi.startswith("10.") or self.doi.startswith("http")):
            errors.append(f"DOI should start with '10.' or be a URL, got: {self.doi}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"DatasetMetadata(name='{self.name}', organism='{self.organism}')"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.name
