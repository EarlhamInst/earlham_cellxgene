"""
Unit tests for DatasetScanner service

Tests dataset scanning logic including:
- Directory scanning for h5ad files
- Metadata loading and validation
- Error handling for invalid datasets
- Fail-fast behavior

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive test coverage
- Principle IV (Fail-Fast): Test validation and error handling
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import anndata
import numpy as np
import pandas as pd

from src.services.scanner import DatasetScanner
from src.models.dataset import Dataset
from src.models.metadata import DatasetMetadata
from src.errors import ValidationError, FileAccessError, DatasetNotFoundError


class TestDatasetScannerInit:
    """Test DatasetScanner initialization."""
    
    def test_scanner_init_with_path_string(self):
        """Test scanner initialization with string path."""
        scanner = DatasetScanner("/data/datasets")
        
        assert scanner.data_directory == Path("/data/datasets")
        assert scanner.logger is not None
    
    def test_scanner_init_with_path_object(self):
        """Test scanner initialization with Path object."""
        data_dir = Path("/data/datasets")
        scanner = DatasetScanner(data_dir)
        
        assert scanner.data_directory == data_dir
    
    def test_scanner_init_with_custom_logger(self):
        """Test scanner initialization with custom logger."""
        import logging
        custom_logger = logging.getLogger("test_logger")
        scanner = DatasetScanner("/data/datasets", logger=custom_logger)
        
        assert scanner.logger == custom_logger


class TestDatasetScannerScan:
    """Test DatasetScanner scan functionality."""
    
    def test_scan_nonexistent_directory_raises_error(self):
        """Test that scanning nonexistent directory raises FileAccessError."""
        scanner = DatasetScanner("/nonexistent/directory")
        
        with pytest.raises(FileAccessError) as exc_info:
            scanner.scan()
        
        assert "does not exist" in str(exc_info.value)
    
    def test_scan_file_instead_of_directory_raises_error(self, tmp_path):
        """Test that scanning a file (not directory) raises FileAccessError."""
        test_file = tmp_path / "not_a_directory.txt"
        test_file.write_text("test")
        
        scanner = DatasetScanner(test_file)
        
        with pytest.raises(FileAccessError) as exc_info:
            scanner.scan()
        
        assert "not a directory" in str(exc_info.value).lower()
    
    def test_scan_empty_directory_returns_empty_list(self, tmp_path):
        """Test scanning directory with no h5ad files."""
        scanner = DatasetScanner(tmp_path)
        
        valid, invalid = scanner.scan()
        
        assert valid == []
        assert invalid == []
    
    def test_scan_directory_with_no_h5ad_files(self, tmp_path):
        """Test scanning directory with files but no h5ad files."""
        # Create non-h5ad files
        (tmp_path / "readme.txt").write_text("test")
        (tmp_path / "data.csv").write_text("test")
        
        scanner = DatasetScanner(tmp_path)
        valid, invalid = scanner.scan()
        
        assert valid == []
        assert invalid == []
    
    def test_scan_finds_h5ad_files(self, tmp_path):
        """Test that scan finds h5ad files in directory."""
        # Create real AnnData h5ad files with embedded metadata
        h5ad_file1 = tmp_path / "dataset1.h5ad"
        h5ad_file2 = tmp_path / "dataset2.h5ad"
        
        # Create minimal AnnData objects
        X1 = np.random.rand(10, 5)
        obs1 = pd.DataFrame(index=[f"cell_{i}" for i in range(10)])
        var1 = pd.DataFrame(index=[f"gene_{i}" for i in range(5)])
        adata1 = anndata.AnnData(X=X1, obs=obs1, var=var1)
        adata1.uns['metadata'] = {
            'name': 'Dataset 1',
            'description': 'Test dataset 1',
            'organism': 'Homo sapiens',
            'tissue': 'blood',
            'assay': '10x 3\' v3'
        }
        adata1.write_h5ad(h5ad_file1)
        
        X2 = np.random.rand(8, 6)
        obs2 = pd.DataFrame(index=[f"cell_{i}" for i in range(8)])
        var2 = pd.DataFrame(index=[f"gene_{i}" for i in range(6)])
        adata2 = anndata.AnnData(X=X2, obs=obs2, var=var2)
        adata2.uns['metadata'] = {
            'name': 'Dataset 2',
            'description': 'Test dataset 2',
            'organism': 'Mus musculus',
            'tissue': 'brain',
            'assay': 'Smart-seq2'
        }
        adata2.write_h5ad(h5ad_file2)
        
        scanner = DatasetScanner(tmp_path)
        valid, invalid = scanner.scan()
        
        assert len(valid) == 2
        assert len(invalid) == 0
        assert all(isinstance(ds, Dataset) for ds in valid)
    
    def test_scan_h5ad_without_metadata_json(self, tmp_path):
        """Test that h5ad without embedded metadata uses defaults."""
        # Create h5ad file without embedded metadata
        h5ad_file = tmp_path / "dataset_no_metadata.h5ad"
        
        # Create minimal AnnData without .uns metadata
        X = np.random.rand(5, 3)
        obs = pd.DataFrame(index=[f"cell_{i}" for i in range(5)])
        var = pd.DataFrame(index=[f"gene_{i}" for i in range(3)])
        adata = anndata.AnnData(X=X, obs=obs, var=var)
        # Don't add .uns['metadata'] - should use defaults
        adata.write_h5ad(h5ad_file)
        
        scanner = DatasetScanner(tmp_path)
        valid, invalid = scanner.scan()
        
        # Should be valid with auto-generated metadata
        assert len(valid) == 1
        assert len(invalid) == 0
        assert valid[0].display_name == "Dataset No Metadata"  # Generated from filename
        assert valid[0].organism == "Unknown"
        assert valid[0].tissue == "Unknown"
        assert valid[0].assay == "Unknown"
    
    def test_scan_with_invalid_metadata_json(self, tmp_path):
        """Test handling of h5ad with invalid structure."""
        # Create h5ad file that's not a real h5ad (corrupted file)
        h5ad_file = tmp_path / "dataset_bad_structure.h5ad"
        # Write a text file with .h5ad extension (invalid)
        h5ad_file.write_text("This is not a valid h5ad file")
        
        scanner = DatasetScanner(tmp_path)
        valid, invalid = scanner.scan()
        
        assert len(valid) == 0
        assert len(invalid) == 1
        assert "dataset_bad_structure" in invalid[0][0]
    
    def test_scan_with_incomplete_metadata(self, tmp_path):
        """Test handling of metadata with missing name/description (now uses defaults)."""
        # Create h5ad file with minimal embedded metadata
        h5ad_file = tmp_path / "dataset_minimal.h5ad"
        
        # Create AnnData with only partial metadata in .uns
        X = np.random.rand(5, 3)
        obs = pd.DataFrame(index=[f"cell_{i}" for i in range(5)])
        var = pd.DataFrame(index=[f"gene_{i}" for i in range(3)])
        adata = anndata.AnnData(X=X, obs=obs, var=var)
        # Add minimal metadata - should still work with defaults
        adata.uns['metadata'] = {
            'name': 'Minimal Dataset'
            # Missing description - should use default
        }
        adata.write_h5ad(h5ad_file)
        
        scanner = DatasetScanner(tmp_path)
        valid, invalid = scanner.scan()
        
        # Should be valid - defaults are generated
        assert len(valid) == 1
        assert len(invalid) == 0
        assert valid[0].display_name == "Minimal Dataset"
    
    def test_scan_fail_on_invalid_raises_exception(self, tmp_path):
        """Test that fail_on_invalid=True raises exception for invalid datasets."""
        # Create invalid h5ad file (write a text file with .h5ad extension)
        h5ad_file = tmp_path / "invalid.h5ad"
        h5ad_file.write_text("This is not a valid h5ad file")
        
        scanner = DatasetScanner(tmp_path)
        
        with pytest.raises(ValidationError):
            scanner.scan(fail_on_invalid=True)
    
    def test_scan_sorts_datasets_by_filename(self, tmp_path):
        """Test that datasets are returned in sorted order."""
        # Create multiple h5ad files in random order
        filenames = ["zebra.h5ad", "alpha.h5ad", "beta.h5ad"]
        
        for filename in filenames:
            h5ad_file = tmp_path / filename
            
            # Create minimal AnnData object
            X = np.random.rand(5, 3)
            obs = pd.DataFrame(index=[f"cell_{i}" for i in range(5)])
            var = pd.DataFrame(index=[f"gene_{i}" for i in range(3)])
            adata = anndata.AnnData(X=X, obs=obs, var=var)
            adata.uns['metadata'] = {
                'name': filename.replace('.h5ad', ''),
                'description': 'Test',
                'organism': 'Test',
                'tissue': 'Test',
                'assay': 'Test'
            }
            adata.write_h5ad(h5ad_file)
        
        scanner = DatasetScanner(tmp_path)
        valid, invalid = scanner.scan()
        
        # Should be sorted: alpha, beta, zebra
        assert valid[0].id == "alpha"
        assert valid[1].id == "beta"
        assert valid[2].id == "zebra"
    
    def test_scan_separates_valid_and_invalid_datasets(self, tmp_path):
        """Test that scan correctly separates valid and invalid datasets."""
        # Create valid dataset with real AnnData
        valid_h5ad = tmp_path / "valid.h5ad"
        X = np.random.rand(5, 3)
        obs = pd.DataFrame(index=[f"cell_{i}" for i in range(5)])
        var = pd.DataFrame(index=[f"gene_{i}" for i in range(3)])
        adata = anndata.AnnData(X=X, obs=obs, var=var)
        adata.uns['metadata'] = {
            'name': 'Valid Dataset',
            'description': 'Valid',
            'organism': 'Test',
            'tissue': 'Test',
            'assay': 'Test'
        }
        adata.write_h5ad(valid_h5ad)
        
        # Create invalid dataset (not a real h5ad file)
        invalid_h5ad = tmp_path / "invalid.h5ad"
        invalid_h5ad.write_text("Not a valid h5ad file")
        
        scanner = DatasetScanner(tmp_path)
        valid, invalid = scanner.scan()
        
        assert len(valid) == 1
        assert len(invalid) == 1
        assert valid[0].id == "valid"
        assert invalid[0][0] == "invalid"


class TestDatasetScannerGetDatasetById:
    """Test get_dataset_by_id method."""
    
    def test_get_dataset_by_id_success(self, tmp_path):
        """Test retrieving dataset by ID."""
        # Create real AnnData dataset
        h5ad_file = tmp_path / "test_dataset.h5ad"
        
        X = np.random.rand(10, 5)
        obs = pd.DataFrame(index=[f"cell_{i}" for i in range(10)])
        var = pd.DataFrame(index=[f"gene_{i}" for i in range(5)])
        adata = anndata.AnnData(X=X, obs=obs, var=var)
        adata.uns['metadata'] = {
            'name': 'Test Dataset',
            'description': 'Test',
            'organism': 'Test',
            'tissue': 'Test',
            'assay': 'Test'
        }
        adata.write_h5ad(h5ad_file)
        
        scanner = DatasetScanner(tmp_path)
        dataset = scanner.get_dataset_by_id("test_dataset")
        
        assert dataset.id == "test_dataset"
        assert dataset.display_name == "Test Dataset"
    
    def test_get_dataset_by_id_not_found(self, tmp_path):
        """Test that nonexistent dataset ID raises DatasetNotFoundError."""
        scanner = DatasetScanner(tmp_path)
        
        with pytest.raises(DatasetNotFoundError) as exc_info:
            scanner.get_dataset_by_id("nonexistent")
        
        assert "nonexistent" in str(exc_info.value)


class TestDatasetScannerValidateH5adFormat:
    """Test h5ad format validation."""
    
    def test_validate_h5ad_nonexistent_file(self, tmp_path):
        """Test validation of nonexistent file."""
        scanner = DatasetScanner(tmp_path)
        nonexistent = tmp_path / "nonexistent.h5ad"
        
        is_valid, errors = scanner.validate_h5ad_format(nonexistent)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "not found" in errors[0].lower()
    
    def test_validate_h5ad_empty_file(self, tmp_path):
        """Test validation of empty file."""
        scanner = DatasetScanner(tmp_path)
        empty_file = tmp_path / "empty.h5ad"
        empty_file.write_bytes(b"")
        
        is_valid, errors = scanner.validate_h5ad_format(empty_file)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "empty" in errors[0].lower()
    
    def test_validate_h5ad_invalid_header(self, tmp_path):
        """Test validation of file without HDF5 signature."""
        scanner = DatasetScanner(tmp_path)
        invalid_file = tmp_path / "invalid.h5ad"
        invalid_file.write_bytes(b"not an hdf5 file")
        
        is_valid, errors = scanner.validate_h5ad_format(invalid_file)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "hdf5" in errors[0].lower() or "header" in errors[0].lower()
    
    def test_validate_h5ad_valid_file(self, tmp_path):
        """Test validation of file with valid HDF5 signature."""
        scanner = DatasetScanner(tmp_path)
        valid_file = tmp_path / "valid.h5ad"
        
        # Write HDF5 signature
        hdf5_sig = b'\x89HDF\r\n\x1a\n'
        valid_file.write_bytes(hdf5_sig + b"x" * 100)
        
        is_valid, errors = scanner.validate_h5ad_format(valid_file)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_h5ad_file_access_error(self, tmp_path):
        """Test handling of file access errors during validation."""
        scanner = DatasetScanner(tmp_path)
        
        # Create a file that will cause read error (mock)
        test_file = tmp_path / "error.h5ad"
        test_file.write_bytes(b"test")
        
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            is_valid, errors = scanner.validate_h5ad_format(test_file)
        
        assert is_valid is False
        assert len(errors) > 0


class TestDatasetScannerLogging:
    """Test logging behavior."""
    
    def test_scan_logs_found_files(self, tmp_path):
        """Test that scan logs number of files found."""
        # Create h5ad file
        h5ad_file = tmp_path / "test.h5ad"
        hdf5_sig = b'\x89HDF\r\n\x1a\n'
        h5ad_file.write_bytes(hdf5_sig + b"x" * 100)
        
        metadata = {
            'name': 'Test',
            'description': 'Test',
            'organism': 'Test',
            'tissue': 'Test',
            'assay': 'Test'
        }
        (tmp_path / "test.json").write_text(json.dumps(metadata))
        
        # Create mock logger
        mock_logger = Mock()
        scanner = DatasetScanner(tmp_path, logger=mock_logger)
        
        with patch.object(Dataset, 'validate', return_value=True):
            scanner.scan()
        
        # Check that info was logged
        mock_logger.info.assert_called()
    
    def test_scan_logs_validation_results(self, tmp_path):
        """Test that scan logs validation success/failure."""
        # Create valid dataset
        h5ad_file = tmp_path / "valid.h5ad"
        hdf5_sig = b'\x89HDF\r\n\x1a\n'
        h5ad_file.write_bytes(hdf5_sig + b"x" * 100)
        
        metadata = {
            'name': 'Valid',
            'description': 'Test',
            'organism': 'Test',
            'tissue': 'Test',
            'assay': 'Test'
        }
        (tmp_path / "valid.json").write_text(json.dumps(metadata))
        
        # Create invalid dataset
        invalid_h5ad = tmp_path / "invalid.h5ad"
        invalid_h5ad.write_bytes(hdf5_sig + b"x" * 100)
        
        mock_logger = Mock()
        scanner = DatasetScanner(tmp_path, logger=mock_logger)
        
        with patch.object(Dataset, 'validate', return_value=True):
            scanner.scan()
        
        # Check that both info and warning/error were logged
        assert mock_logger.info.called
        assert mock_logger.error.called or mock_logger.warning.called
