"""
Dataset Scanner Service

Scans data directory for h5ad files and extracts embedded metadata.

Constitutional Alignment:
- Principle IV (Fail-Fast): Validates all datasets on scan
- Principle II (Modular Architecture): Isolated scanning logic
- Principle I (Unit Testing): Designed for testability
"""

import json
import gc
from pathlib import Path
from typing import List, Tuple, Dict, Any
import logging

try:
    import anndata
    import pandas as pd
except ImportError:
    anndata = None
    pd = None

from ..models.dataset import Dataset
from ..models.metadata import DatasetMetadata
from ..errors import ValidationError, FileAccessError


class DatasetScanner:
    """
    Scans a directory for h5ad datasets and their metadata.

    Validates each dataset pair (h5ad + JSON metadata) and returns
    Dataset objects for valid datasets.
    """

    def __init__(self, data_directory: Path, logger: logging.Logger = None):
        """
        Initialize scanner with data directory.

        Args:
            data_directory: Path to directory containing h5ad files
            logger: Optional logger instance
        """
        self.data_directory = Path(data_directory)
        self.logger = logger or logging.getLogger(__name__)

    def scan(
        self, fail_on_invalid: bool = False
    ) -> Tuple[List[Dataset], List[Tuple[str, List[str]]]]:
        """
        Scan directory for datasets.

        Args:
            fail_on_invalid: If True, raise exception on any invalid dataset

        Returns:
            Tuple of (valid_datasets, invalid_datasets_with_errors)

        Raises:
            ValidationError: If fail_on_invalid=True and any dataset is invalid
            FileAccessError: If data directory cannot be accessed
        """
        if not self.data_directory.exists():
            raise FileAccessError(
                str(self.data_directory), "read", "Directory does not exist"
            )

        if not self.data_directory.is_dir():
            raise FileAccessError(
                str(self.data_directory), "read", "Path is not a directory"
            )

        # Find all h5ad files
        h5ad_files = list(self.data_directory.glob("*.h5ad"))

        if len(h5ad_files) == 0:
            self.logger.warning(f"No h5ad files found in {self.data_directory}")
            return [], []

        self.logger.info(f"Found {len(h5ad_files)} h5ad files to scan")

        valid_datasets = []
        invalid_datasets = []

        for h5ad_file in sorted(h5ad_files):
            try:
                dataset = self._load_dataset(h5ad_file)

                if dataset.validate():
                    valid_datasets.append(dataset)
                    self.logger.info(f"✓ Valid dataset: {dataset.id}")
                else:
                    invalid_datasets.append((dataset.id, dataset.validation_errors))
                    self.logger.warning(
                        f"✗ Invalid dataset: {dataset.id} - {', '.join(dataset.validation_errors)}"
                    )
            except Exception as e:
                error_msg = f"Failed to load dataset {h5ad_file.name}: {str(e)}"
                invalid_datasets.append((h5ad_file.stem, [error_msg]))
                self.logger.error(error_msg)
            finally:
                # Force garbage collection after each dataset to free memory
                gc.collect()

        self.logger.info(
            f"Scan complete: {len(valid_datasets)} valid, {len(invalid_datasets)} invalid"
        )

        # Fail fast if requested
        if fail_on_invalid and invalid_datasets:
            raise ValidationError(
                "dataset scan",
                [f"{ds_id}: {'; '.join(errors)}" for ds_id, errors in invalid_datasets],
            )

        return valid_datasets, invalid_datasets

    def _load_dataset(self, h5ad_path: Path) -> Dataset:
        """
        Load a single dataset from h5ad file with embedded metadata.

        Args:
            h5ad_path: Path to h5ad file

        Returns:
            Dataset instance

        Raises:
            FileAccessError: If h5ad file cannot be read
            ValidationError: If metadata is invalid or anndata is not installed
        """
        if anndata is None:
            raise ValidationError(
                str(h5ad_path),
                ["anndata library not installed. Install with: pip install anndata"],
            )

        # Extract metadata from h5ad file
        try:
            metadata_dict = self._extract_metadata_from_h5ad(h5ad_path)
        except Exception as e:
            raise FileAccessError(
                str(h5ad_path), "read", f"Failed to read h5ad file: {str(e)}"
            )

        # Validate metadata
        try:
            metadata = DatasetMetadata.from_dict(metadata_dict)
            is_valid, errors = metadata.validate()

            if not is_valid:
                raise ValidationError(str(h5ad_path), errors)
        except ValueError as e:
            raise ValidationError(str(h5ad_path), [str(e)])

        # Create dataset
        dataset = Dataset.from_files(h5ad_path, metadata.to_dict())

        return dataset

    def _extract_metadata_from_h5ad(self, h5ad_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from h5ad file with minimal structure validation.

        Validates minimal AnnData requirements:
        - X matrix exists
        - obs dataframe exists with obs_names (cell barcodes)
        - var dataframe exists with var_names (feature IDs)

        Args:
            h5ad_path: Path to h5ad file

        Returns:
            Dictionary containing metadata

        Raises:
            ValueError: If minimal AnnData structure is invalid
        """
        # Read h5ad file in backed mode to avoid loading entire matrix into memory
        adata = anndata.read_h5ad(h5ad_path, backed="r")

        # Validate minimal AnnData structure
        if adata.X is None:
            raise ValueError("Invalid AnnData: missing expression matrix (X)")

        if adata.obs is None or len(adata.obs) == 0:
            raise ValueError("Invalid AnnData: missing or empty obs dataframe")

        if adata.var is None or len(adata.var) == 0:
            raise ValueError("Invalid AnnData: missing or empty var dataframe")

        # Check that obs_names and var_names exist
        if adata.obs_names is None or len(adata.obs_names) == 0:
            raise ValueError("Invalid AnnData: obs must have row names (cell barcodes)")

        if adata.var_names is None or len(adata.var_names) == 0:
            raise ValueError("Invalid AnnData: var must have row names (feature IDs)")

        # Initialize metadata dictionary
        metadata = {}

        # Try to get metadata from .uns if it exists
        if "metadata" in adata.uns:
            metadata = dict(adata.uns["metadata"])

        # Generate sensible defaults from filename and data structure
        metadata["name"] = metadata.get(
            "name",
            metadata.get(
                "title", h5ad_path.stem.replace("_", " ").replace("-", " ").title()
            ),
        )
        metadata["description"] = metadata.get(
            "description",
            metadata.get(
                "summary",
                f"Dataset with {adata.n_obs:,} cells and {adata.n_vars:,} features",
            ),
        )

        # Try to extract organism, tissue, assay from various locations
        # Priority: explicit metadata > .uns > obs columns > default
        if "organism" not in metadata:
            if "organism" in adata.uns:
                metadata["organism"] = str(adata.uns["organism"])
            elif (
                "organism" in adata.obs.columns
                and len(adata.obs["organism"].unique()) == 1
            ):
                metadata["organism"] = str(adata.obs["organism"].iloc[0])
            else:
                metadata["organism"] = "Unknown"

        if "tissue" not in metadata:
            if "tissue" in adata.uns:
                metadata["tissue"] = str(adata.uns["tissue"])
            elif (
                "tissue" in adata.obs.columns and len(adata.obs["tissue"].unique()) == 1
            ):
                metadata["tissue"] = str(adata.obs["tissue"].iloc[0])
            else:
                metadata["tissue"] = "Unknown"

        if "assay" not in metadata:
            if "assay" in adata.uns:
                metadata["assay"] = str(adata.uns["assay"])
            elif "assay" in adata.obs.columns and len(adata.obs["assay"].unique()) == 1:
                metadata["assay"] = str(adata.obs["assay"].iloc[0])
            else:
                metadata["assay"] = "Unknown"

        # Get counts from data dimensions (always accurate)
        metadata["cell_count"] = adata.n_obs
        metadata["gene_count"] = adata.n_vars

        # Extract optional fields from .uns if available
        optional_fields = [
            "doi",
            "publication",
            "contributors",
            "version",
            "date_created",
            "license",
            "tags",
        ]
        for field in optional_fields:
            if field in adata.uns and field not in metadata:
                metadata[field] = adata.uns[field]

        # Close the file explicitly to free memory
        if hasattr(adata, "file") and adata.file is not None:
            adata.file.close()

        return metadata

    def get_dataset_by_id(self, dataset_id: str) -> Dataset:
        """
        Load a specific dataset by ID.

        Args:
            dataset_id: Dataset identifier (filename without extension)

        Returns:
            Dataset instance

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
        """
        from ..errors import DatasetNotFoundError

        h5ad_path = self.data_directory / f"{dataset_id}.h5ad"

        if not h5ad_path.exists():
            raise DatasetNotFoundError(dataset_id)

        return self._load_dataset(h5ad_path)

    def validate_h5ad_format(self, h5ad_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate that a file is in valid h5ad (HDF5) format.

        Args:
            h5ad_path: Path to h5ad file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not h5ad_path.exists():
            return False, [f"File not found: {h5ad_path}"]

        if h5ad_path.stat().st_size == 0:
            return False, [f"File is empty: {h5ad_path}"]

        # Check HDF5 magic number
        try:
            with open(h5ad_path, "rb") as f:
                header = f.read(8)
                hdf5_signature = b"\x89HDF\r\n\x1a\n"

                if header != hdf5_signature:
                    return False, [
                        f"File does not have valid HDF5/h5ad header: {h5ad_path}"
                    ]
        except Exception as e:
            return False, [f"Error reading file: {str(e)}"]

        return True, []
