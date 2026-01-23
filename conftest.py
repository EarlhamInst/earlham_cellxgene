"""
Pytest Configuration and Shared Fixtures

Provides common fixtures and configuration for all tests.

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive test infrastructure
- Principle III (Code Clarity): Reusable test fixtures
"""

import pytest
import tempfile
import json
import sys
from pathlib import Path
from typing import Dict, List
import shutil

# Add the landing page service directory to Python path for imports
# This allows tests to import from 'src' package
landing_page_dir = Path(__file__).parent / "services" / "landing-page"
if str(landing_page_dir) not in sys.path:
    sys.path.insert(0, str(landing_page_dir))


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """
    Create a temporary data directory for testing.
    
    Returns:
        Path to temporary directory that will be cleaned up after test
    """
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """
    Create a temporary log directory for testing.
    
    Returns:
        Path to temporary log directory
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def sample_metadata() -> Dict:
    """
    Provide sample valid metadata conforming to singlecellschemas.org.
    
    Returns:
        Dictionary with valid metadata
    """
    return {
        "name": "Test PBMC Dataset",
        "description": "3k PBMCs from a Healthy Donor for Testing",
        "organism": "Homo sapiens",
        "tissue": "peripheral blood",
        "assay": "10x 3' v2",
        "cell_count": 2700,
        "gene_count": 32738,
        "doi": "10.1234/test.dataset",
        "publication": "Test et al. (2024)"
    }


@pytest.fixture
def invalid_metadata() -> Dict:
    """
    Provide invalid metadata (missing required fields).
    
    Returns:
        Dictionary with invalid metadata
    """
    return {
        "name": "Incomplete Dataset",
        # Missing required fields: description, organism, tissue, assay
    }


@pytest.fixture
def mock_h5ad_file(temp_data_dir: Path) -> Path:
    """
    Create a mock h5ad file (with valid HDF5 header).
    
    Returns:
        Path to mock h5ad file
    """
    h5ad_file = temp_data_dir / "test_dataset.h5ad"
    
    # Write HDF5 magic number
    hdf5_signature = b'\x89HDF\r\n\x1a\n'
    with open(h5ad_file, 'wb') as f:
        f.write(hdf5_signature)
        # Write some dummy data to make it non-empty
        f.write(b'\x00' * 1024)
    
    return h5ad_file


@pytest.fixture
def mock_dataset_with_metadata(temp_data_dir: Path, sample_metadata: Dict) -> tuple:
    """
    Create a mock dataset with both h5ad file and metadata JSON.
    
    Returns:
        Tuple of (h5ad_path, metadata_path)
    """
    # Create h5ad file
    h5ad_file = temp_data_dir / "test_pbmc.h5ad"
    hdf5_signature = b'\x89HDF\r\n\x1a\n'
    with open(h5ad_file, 'wb') as f:
        f.write(hdf5_signature)
        f.write(b'\x00' * 1024)
    
    # Create metadata JSON
    metadata_file = temp_data_dir / "test_pbmc.json"
    with open(metadata_file, 'w') as f:
        json.dump(sample_metadata, f, indent=2)
    
    return h5ad_file, metadata_file


@pytest.fixture
def multiple_mock_datasets(temp_data_dir: Path, sample_metadata: Dict) -> List[tuple]:
    """
    Create multiple mock datasets for testing.
    
    Returns:
        List of tuples (h5ad_path, metadata_path)
    """
    datasets = []
    
    dataset_names = ["pbmc_3k", "pbmc_10k", "heart_cells"]
    
    for name in dataset_names:
        # Create h5ad file
        h5ad_file = temp_data_dir / f"{name}.h5ad"
        hdf5_signature = b'\x89HDF\r\n\x1a\n'
        with open(h5ad_file, 'wb') as f:
            f.write(hdf5_signature)
            f.write(b'\x00' * 1024)
        
        # Create metadata with unique name
        metadata = sample_metadata.copy()
        metadata['name'] = f"Test {name.upper()} Dataset"
        
        metadata_file = temp_data_dir / f"{name}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        datasets.append((h5ad_file, metadata_file))
    
    return datasets


@pytest.fixture
def mock_env_vars(temp_data_dir: Path, temp_log_dir: Path, monkeypatch):
    """
    Set up mock environment variables for testing.
    
    Args:
        monkeypatch: Pytest's monkeypatch fixture
    """
    env_vars = {
        'DATA_DIRECTORY': str(temp_data_dir),
        'LOG_DIRECTORY': str(temp_log_dir),
        'DEBUG': 'true',
        'LOG_LEVEL': 'DEBUG',
        'HOST': '127.0.0.1',
        'PORT': '8000',
        'CELLXGENE_URL': 'http://localhost:5005',
        'ENABLE_HOT_RELOAD': 'false'
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def corrupted_h5ad_file(temp_data_dir: Path) -> Path:
    """
    Create a corrupted h5ad file (wrong magic number).
    
    Returns:
        Path to corrupted h5ad file
    """
    h5ad_file = temp_data_dir / "corrupted.h5ad"
    
    # Write invalid header
    with open(h5ad_file, 'wb') as f:
        f.write(b'CORRUPTED_FILE')
    
    return h5ad_file


@pytest.fixture
def empty_h5ad_file(temp_data_dir: Path) -> Path:
    """
    Create an empty h5ad file.
    
    Returns:
        Path to empty h5ad file
    """
    h5ad_file = temp_data_dir / "empty.h5ad"
    h5ad_file.touch()
    return h5ad_file


# Markers for test categorization
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "contract: mark test as a contract test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
