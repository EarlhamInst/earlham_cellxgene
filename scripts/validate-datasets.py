#!/usr/bin/env python3
"""
Dataset Validation Module

Validates h5ad files and their embedded metadata against project requirements.
Provides fail-fast validation to catch issues before deployment.

Constitutional Alignment:
- Principle IV (Fail-Fast): Validates all datasets on startup
- Principle III (Code Clarity): Clear error messages with recovery steps
- Principle I (Unit Testing): Designed for testability
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

try:
    import anndata
    import pandas as pd
except ImportError:
    anndata = None
    pd = None


class ValidationError(Exception):
    """Raised when dataset validation fails."""

    pass


class DatasetNotFoundError(Exception):
    """Raised when a referenced dataset file cannot be found."""

    pass


class MetadataValidationError(Exception):
    """Raised when metadata JSON validation fails."""

    pass


def validate_h5ad_file(filepath: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate that a file is a valid h5ad format.

    Args:
        filepath: Path to the h5ad file

    Returns:
        Tuple of (is_valid, error_message)

    Note: This is a basic validation. Full validation requires anndata library.
    """
    if not filepath.exists():
        return False, f"File not found: {filepath}"

    if not filepath.suffix == ".h5ad":
        return False, f"File must have .h5ad extension: {filepath}"

    if filepath.stat().st_size == 0:
        return False, f"File is empty: {filepath}"

    # Basic HDF5 signature check (first 8 bytes should be HDF5 magic number)
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
            if len(header) < 8:
                return False, f"File too small to be valid h5ad: {filepath}"

            # HDF5 files start with these magic bytes
            hdf5_signature = b"\x89HDF\r\n\x1a\n"
            if header != hdf5_signature:
                return (
                    False,
                    f"File does not appear to be valid HDF5/h5ad format: {filepath}",
                )
    except Exception as e:
        return False, f"Error reading file {filepath}: {str(e)}"

    return True, None


def validate_metadata_schema(metadata: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate metadata extracted from h5ad file.

    Only requires name and description.
    organism, tissue, assay can be 'Unknown'.

    Args:
        metadata: Metadata dictionary extracted from h5ad

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Only name and description are strictly required
    required_fields = ["name", "description"]

    for field in required_fields:
        if field not in metadata:
            return False, f"Missing required field: {field}"

        if not isinstance(metadata[field], str) or not metadata[field].strip():
            return False, f"Field '{field}' must be a non-empty string"

    # organism, tissue, assay should exist but can be 'Unknown'
    for field in ["organism", "tissue", "assay"]:
        if field not in metadata:
            return (
                False,
                f"Missing field: {field} (should be present, can be 'Unknown')",
            )

    # Optional but recommended numeric fields
    numeric_fields = ["cell_count", "gene_count"]
    for field in numeric_fields:
        if field in metadata:
            if not isinstance(metadata[field], (int, float)):
                return False, f"Field '{field}' must be a number"
            if metadata[field] < 0:
                return False, f"Field '{field}' must be non-negative"

    return True, None


def extract_metadata_from_h5ad(h5ad_path: Path) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Extract metadata from h5ad file with minimal structure validation.

    Validates minimal AnnData requirements:
    - X matrix exists
    - obs dataframe exists with obs_names (cell barcodes)
    - var dataframe exists with var_names (feature IDs)

    Args:
        h5ad_path: Path to h5ad file

    Returns:
        Tuple of (metadata_dict, error_message)
    """
    if anndata is None:
        return None, "anndata library not installed. Install with: pip install anndata"

    try:
        # Read h5ad file
        adata = anndata.read_h5ad(h5ad_path)

        # Validate minimal AnnData structure
        if adata.X is None:
            return None, "Invalid AnnData: missing expression matrix (X)"

        if adata.obs is None or len(adata.obs) == 0:
            return None, "Invalid AnnData: missing or empty obs dataframe"

        if adata.var is None or len(adata.var) == 0:
            return None, "Invalid AnnData: missing or empty var dataframe"

        # Check that obs_names and var_names exist
        if adata.obs_names is None or len(adata.obs_names) == 0:
            return None, "Invalid AnnData: obs must have row names (cell barcodes)"

        if adata.var_names is None or len(adata.var_names) == 0:
            return None, "Invalid AnnData: var must have row names (feature IDs)"

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

        return metadata, None

    except Exception as e:
        return None, f"Failed to extract metadata: {str(e)}"


def validate_dataset_pair(h5ad_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate an h5ad file and extract its embedded metadata.

    Args:
        h5ad_path: Path to the h5ad file

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Validate h5ad file
    h5ad_valid, h5ad_error = validate_h5ad_file(h5ad_path)
    if not h5ad_valid:
        errors.append(h5ad_error)
        return False, errors

    # Extract metadata from h5ad file
    metadata, extract_error = extract_metadata_from_h5ad(h5ad_path)
    if extract_error:
        errors.append(extract_error)
        return False, errors

    # Validate metadata schema
    schema_valid, schema_error = validate_metadata_schema(metadata)
    if not schema_valid:
        errors.append(f"Metadata validation failed: {schema_error}")

    is_valid = len(errors) == 0
    return is_valid, errors


def scan_and_validate_datasets(data_directory: Path) -> Tuple[int, int, List[str]]:
    """
    Scan data directory and validate all h5ad datasets.

    Args:
        data_directory: Path to directory containing h5ad files

    Returns:
        Tuple of (valid_count, invalid_count, list_of_all_errors)
    """
    if not data_directory.exists():
        raise DatasetNotFoundError(f"Data directory not found: {data_directory}")

    if not data_directory.is_dir():
        raise ValidationError(f"Path is not a directory: {data_directory}")

    h5ad_files = list(data_directory.glob("*.h5ad"))

    if len(h5ad_files) == 0:
        print(f"⚠️  Warning: No h5ad files found in {data_directory}", file=sys.stderr)
        return 0, 0, []

    valid_count = 0
    invalid_count = 0
    all_errors = []

    for h5ad_file in sorted(h5ad_files):
        is_valid, errors = validate_dataset_pair(h5ad_file)

        if is_valid:
            valid_count += 1
            print(f"✓ {h5ad_file.name}: VALID")
        else:
            invalid_count += 1
            print(f"✗ {h5ad_file.name}: INVALID", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
                all_errors.append(f"{h5ad_file.name}: {error}")

    return valid_count, invalid_count, all_errors


def main():
    """Main CLI entry point for dataset validation."""
    parser = argparse.ArgumentParser(
        description="Validate h5ad datasets and metadata for CellXGene Explorer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate all datasets in default directory
  %(prog)s
  
  # Validate datasets in custom directory
  %(prog)s --data-dir /path/to/datasets
  
  # Fail fast on any error (useful for CI/CD)
  %(prog)s --fail-fast
        """,
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data/datasets"),
        help="Path to datasets directory (default: ./data/datasets)",
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit with error code on first validation failure",
    )

    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    args = parser.parse_args()

    try:
        valid_count, invalid_count, errors = scan_and_validate_datasets(args.data_dir)

        if args.json:
            result = {
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "total_count": valid_count + invalid_count,
                "errors": errors,
                "success": invalid_count == 0,
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"Validation Summary:")
            print(f"  Valid datasets:   {valid_count}")
            print(f"  Invalid datasets: {invalid_count}")
            print(f"  Total datasets:   {valid_count + invalid_count}")
            print(f"{'='*60}")

        if invalid_count > 0:
            if args.fail_fast:
                print(
                    "\n❌ Validation failed. Fix errors above before deploying.",
                    file=sys.stderr,
                )
                sys.exit(1)
            else:
                print(
                    "\n⚠️  Some datasets are invalid. They will be skipped at runtime.",
                    file=sys.stderr,
                )
                sys.exit(0)
        else:
            if valid_count == 0:
                print("\n⚠️  No datasets found to validate.", file=sys.stderr)
                sys.exit(0)
            else:
                print("\n✅ All datasets are valid!")
                sys.exit(0)

    except DatasetNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        print(
            f"\nCreate the data directory with: mkdir -p {args.data_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
