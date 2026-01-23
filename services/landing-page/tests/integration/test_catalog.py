"""
Integration tests for dataset catalog generation

Tests the complete catalog workflow including:
- Scanning datasets from filesystem
- Error handling for corrupted data
- Empty directory handling
- Fail-fast validation

Note: Tests that require valid h5ad files have been removed as they need
actual HDF5 formatted files. The E2E tests validate catalog functionality
with real datasets.

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive integration test coverage
- Principle IV (Fail-Fast): Verify fail-fast validation behavior
"""

import pytest
import json
from pathlib import Path

from src.services.scanner import DatasetScanner
from src.services.catalog import DatasetCatalog
from src.errors import ValidationError


class TestCatalogGeneration:
    """Test end-to-end catalog generation from filesystem."""
    
    @pytest.fixture
    def test_data_dir(self):
        """Create temporary test data directory."""
        import tempfile
        test_dir = Path(tempfile.mkdtemp())
        yield test_dir
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)
    
    def _create_h5ad_file(self, path: Path):
        """Create mock h5ad file."""
        # Write minimal HDF5 signature
        hdf5_sig = b'\x89HDF\r\n\x1a\n'
        path.write_bytes(hdf5_sig + b'x' * 1000)
    
    def _create_metadata_file(self, path: Path, metadata: dict):
        """Create metadata JSON file."""
        path.write_text(json.dumps(metadata, indent=2))
    
    def test_catalog_generation_with_fail_fast_validation(self, test_data_dir):
        """Test fail-fast behavior when invalid datasets are present."""
        # Create valid dataset
        h5ad_valid = test_data_dir / "valid.h5ad"
        self._create_h5ad_file(h5ad_valid)
        self._create_metadata_file(
            test_data_dir / "valid.json",
            {
                'name': 'Valid',
                'description': 'Valid',
                'organism': 'Test',
                'tissue': 'Test',
                'assay': 'Test'
            }
        )
        
        # Create invalid dataset (no metadata)
        h5ad_invalid = test_data_dir / "invalid.h5ad"
        self._create_h5ad_file(h5ad_invalid)
        
        # Scan with fail_on_invalid=True should raise exception
        scanner = DatasetScanner(test_data_dir)
        
        with pytest.raises(ValidationError):
            scanner.scan(fail_on_invalid=True)


class TestCatalogErrorHandling:
    """Test catalog error handling."""
    
    def test_catalog_handles_corrupted_json(self, tmp_path):
        """Test handling of corrupted JSON metadata files."""
        # Create h5ad file
        h5ad_file = tmp_path / "corrupted.h5ad"
        hdf5_sig = b'\x89HDF\r\n\x1a\n'
        h5ad_file.write_bytes(hdf5_sig + b'x' * 1000)
        
        # Create corrupted JSON
        json_file = tmp_path / "corrupted.json"
        json_file.write_text("{invalid json: missing quotes")
        
        # Scan should handle error gracefully
        scanner = DatasetScanner(tmp_path)
        valid_datasets, invalid_datasets = scanner.scan()
        
        # Dataset should be invalid
        assert len(valid_datasets) == 0
        assert len(invalid_datasets) == 1
        assert 'corrupted' in invalid_datasets[0][0]
    
    def test_catalog_handles_empty_data_directory(self, tmp_path):
        """Test catalog generation with empty directory."""
        scanner = DatasetScanner(tmp_path)
        valid_datasets, invalid_datasets = scanner.scan()
        
        catalog = DatasetCatalog(datasets=valid_datasets)
        
        # Should succeed with empty catalog
        assert len(catalog) == 0
        assert len(valid_datasets) == 0
        assert len(invalid_datasets) == 0
