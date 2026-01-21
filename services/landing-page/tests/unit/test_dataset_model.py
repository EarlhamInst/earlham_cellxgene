"""
Unit tests for Dataset model

Tests the Dataset data model class including:
- Creation from files
- Validation logic
- Dictionary conversion
- File size formatting
- Checksum calculation

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive test coverage
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import os
import anndata
import numpy as np
import pandas as pd
import hashlib

from src.models.dataset import Dataset


class TestDatasetModel:
    """Test suite for Dataset model."""
    
    def test_dataset_creation_basic(self):
        """Test basic dataset creation with required fields."""
        dataset = Dataset(
            id="test_dataset",
            filename="test_dataset.h5ad",
            filepath=Path("/data/test_dataset.h5ad"),
            display_name="Test Dataset",
            description="Test description",
            organism="Homo sapiens",
            tissue="blood",
            assay="10x 3' v3"
        )
        
        assert dataset.id == "test_dataset"
        assert dataset.filename == "test_dataset.h5ad"
        assert dataset.display_name == "Test Dataset"
        assert dataset.is_valid is True
        assert dataset.validation_errors == []
    
    def test_dataset_creation_with_optional_fields(self):
        """Test dataset creation with all optional fields."""
        dataset = Dataset(
            id="test_dataset",
            filename="test_dataset.h5ad",
            filepath=Path("/data/test_dataset.h5ad"),
            display_name="Test Dataset",
            description="Test description",
            organism="Homo sapiens",
            tissue="blood",
            assay="10x 3' v3",
            cell_count=10000,
            gene_count=2000,
            doi="10.1234/test",
            publication="Test et al. 2024"
        )
        
        assert dataset.cell_count == 10000
        assert dataset.gene_count == 2000
        assert dataset.doi == "10.1234/test"
        assert dataset.publication == "Test et al. 2024"
    
    def test_dataset_post_init_creates_empty_validation_errors(self):
        """Test that __post_init__ creates empty validation_errors list."""
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=Path("/data/test.h5ad"),
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        assert isinstance(dataset.validation_errors, list)
        assert len(dataset.validation_errors) == 0
    
    def test_dataset_filepath_conversion_to_path(self):
        """Test that string filepath is converted to Path object."""
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath="/data/test.h5ad",  # String, not Path
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        assert isinstance(dataset.filepath, Path)
        assert str(dataset.filepath) == "/data/test.h5ad"
    
    def test_dataset_file_size_calculation(self, tmp_path):
        """Test automatic file size calculation for existing files."""
        # Create a temporary file with known size
        test_file = tmp_path / "test.h5ad"
        test_content = b"x" * 1024  # 1 KB
        test_file.write_bytes(test_content)
        
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=test_file,
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        assert dataset.file_size_bytes == 1024
    
    def test_dataset_from_files(self):
        """Test creating dataset from h5ad path and metadata dict."""
        h5ad_path = Path("/data/pbmc_10k.h5ad")
        metadata = {
            'name': 'PBMC 10k Dataset',
            'description': '10,000 peripheral blood cells',
            'organism': 'Homo sapiens',
            'tissue': 'blood',
            'assay': '10x 3\' v3',
            'cell_count': 10000,
            'gene_count': 20000,
            'doi': '10.1234/test',
            'publication': 'Doe et al. 2024'
        }
        
        dataset = Dataset.from_files(h5ad_path, metadata)
        
        assert dataset.id == "pbmc_10k"
        assert dataset.filename == "pbmc_10k.h5ad"
        assert dataset.filepath == h5ad_path
        assert dataset.display_name == "PBMC 10k Dataset"
        assert dataset.description == "10,000 peripheral blood cells"
        assert dataset.organism == "Homo sapiens"
        assert dataset.tissue == "blood"
        assert dataset.assay == "10x 3' v3"
        assert dataset.cell_count == 10000
        assert dataset.gene_count == 20000
        assert dataset.doi == "10.1234/test"
        assert dataset.publication == "Doe et al. 2024"
        assert dataset.is_valid is True
    
    def test_dataset_from_files_uses_defaults_for_missing_fields(self):
        """Test that from_files uses default values when metadata fields are missing."""
        h5ad_path = Path("/data/test.h5ad")
        metadata = {
            'name': 'Test Dataset',
            'description': 'Test'
        }
        
        dataset = Dataset.from_files(h5ad_path, metadata)
        
        assert dataset.display_name == "Test Dataset"
        assert dataset.organism == "Unknown"
        assert dataset.tissue == "Unknown"
        assert dataset.assay == "Unknown"
        assert dataset.cell_count is None
        assert dataset.gene_count is None
    
    def test_dataset_to_dict_excludes_filepath_by_default(self):
        """Test that to_dict excludes filepath for security by default."""
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=Path("/data/test.h5ad"),
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test",
            file_size_bytes=1024000
        )
        
        result = dataset.to_dict()
        
        assert 'id' in result
        assert 'filename' in result
        assert 'filepath' not in result
        assert 'file_size_human' in result
    
    def test_dataset_to_dict_includes_filepath_when_requested(self):
        """Test that to_dict includes filepath when explicitly requested."""
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=Path("/data/test.h5ad"),
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        result = dataset.to_dict(include_filepath=True)
        
        assert 'filepath' in result
        assert result['filepath'] == "/data/test.h5ad"
    
    def test_format_file_size_bytes(self):
        """Test file size formatting for bytes."""
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=Path("/data/test.h5ad"),
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        assert dataset._format_file_size(100) == "100.0 B"
    
    def test_format_file_size_kilobytes(self):
        """Test file size formatting for kilobytes."""
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=Path("/data/test.h5ad"),
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        assert dataset._format_file_size(2048) == "2.0 KB"
    
    def test_format_file_size_megabytes(self):
        """Test file size formatting for megabytes."""
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=Path("/data/test.h5ad"),
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        assert dataset._format_file_size(2 * 1024 * 1024) == "2.0 MB"
    
    def test_format_file_size_gigabytes(self):
        """Test file size formatting for gigabytes."""
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=Path("/data/test.h5ad"),
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        assert dataset._format_file_size(3 * 1024 * 1024 * 1024) == "3.0 GB"
    
    def test_get_checksum(self, tmp_path):
        """Test MD5 checksum calculation."""
        # Create a real AnnData file
        test_file = tmp_path / "test.h5ad"
        X = np.array([[1, 2], [3, 4]])
        obs = pd.DataFrame(index=["cell_0", "cell_1"])
        var = pd.DataFrame(index=["gene_0", "gene_1"])
        adata = anndata.AnnData(X=X, obs=obs, var=var)
        adata.write_h5ad(test_file)
        
        # Calculate actual checksum of the file
        with open(test_file, 'rb') as f:
            expected_checksum = hashlib.md5(f.read()).hexdigest()
        
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=test_file,
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        checksum = dataset.get_checksum()
        assert checksum == expected_checksum
    
    def test_validation_errors_tracked(self):
        """Test that validation errors are properly tracked."""
        dataset = Dataset(
            id="test",
            filename="test.h5ad",
            filepath=Path("/data/test.h5ad"),
            display_name="Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test",
            is_valid=False,
            validation_errors=["Error 1", "Error 2"]
        )
        
        assert dataset.is_valid is False
        assert len(dataset.validation_errors) == 2
        assert "Error 1" in dataset.validation_errors
        assert "Error 2" in dataset.validation_errors


class TestDatasetIntegration:
    """Integration tests for Dataset with real files."""
    
    def test_dataset_with_real_file_calculates_size(self, tmp_path):
        """Test that Dataset correctly calculates file size for real files."""
        # Create actual test file
        test_file = tmp_path / "integration_test.h5ad"
        test_data = b"x" * 5000
        test_file.write_bytes(test_data)
        
        dataset = Dataset(
            id="integration_test",
            filename="integration_test.h5ad",
            filepath=test_file,
            display_name="Integration Test",
            description="Test",
            organism="Test",
            tissue="Test",
            assay="Test"
        )
        
        assert dataset.file_size_bytes == 5000
        
        result_dict = dataset.to_dict()
        assert result_dict['file_size_human'] == "4.9 KB"
