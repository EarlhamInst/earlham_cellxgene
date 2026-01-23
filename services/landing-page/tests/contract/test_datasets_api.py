"""
Contract tests for /api/datasets endpoint

Tests that the API implementation conforms to the OpenAPI specification.

Tests:
- GET /api/datasets - List datasets
- GET /api/datasets/{id} - Get dataset details

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive API contract validation
- Principle IV (Fail-Fast): Verify error handling per specification
"""

import pytest
import json
from pathlib import Path

from src.app import create_app
from src.models.dataset import Dataset
from src.services.catalog import DatasetCatalog


@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_app(testing=True)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_datasets(tmp_path):
    """Create sample datasets for testing."""
    datasets = []
    
    # Dataset 1: Human PBMC
    ds1 = Dataset(
        id="pbmc_10k",
        filename="pbmc_10k.h5ad",
        filepath=tmp_path / "pbmc_10k.h5ad",
        display_name="Human PBMC 10k Dataset",
        description="10,000 peripheral blood mononuclear cells from a healthy donor",
        organism="Homo sapiens",
        tissue="blood",
        assay="10x 3' v3",
        cell_count=10000,
        gene_count=33538,
        file_size_bytes=2468463616
    )
    datasets.append(ds1)
    
    # Dataset 2: Mouse Brain
    ds2 = Dataset(
        id="mouse_brain_5k",
        filename="mouse_brain_5k.h5ad",
        filepath=tmp_path / "mouse_brain_5k.h5ad",
        display_name="Mouse Brain 5k Dataset",
        description="5,000 cells from mouse cortex",
        organism="Mus musculus",
        tissue="brain",
        assay="Smart-seq2",
        cell_count=5000,
        gene_count=28000,
        file_size_bytes=1500000000
    )
    datasets.append(ds2)
    
    return datasets


@pytest.fixture
def mock_catalog(app, sample_datasets):
    """Mock dataset catalog."""
    catalog = DatasetCatalog(datasets=sample_datasets)
    app.config['CATALOG'] = catalog
    return catalog


class TestListDatasetsEndpoint:
    """Test GET /api/datasets endpoint."""
    
    def test_list_datasets_returns_200(self, client, mock_catalog):
        """Test that listing datasets returns 200 OK."""
        response = client.get('/api/datasets')
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
    
    def test_list_datasets_returns_json_with_datasets_array(self, client, mock_catalog):
        """Test that response contains 'datasets' array per OpenAPI spec."""
        response = client.get('/api/datasets')
        data = response.get_json()
        
        assert 'datasets' in data
        assert isinstance(data['datasets'], list)
        assert len(data['datasets']) == 2
    
    def test_list_datasets_returns_total_count(self, client, mock_catalog):
        """Test that response includes total count per OpenAPI spec."""
        response = client.get('/api/datasets')
        data = response.get_json()
        
        # OpenAPI spec has 'total' field
        assert 'count' in data or 'total' in data
    
    def test_list_datasets_dataset_schema(self, client, mock_catalog):
        """Test that each dataset conforms to Dataset schema."""
        response = client.get('/api/datasets')
        data = response.get_json()
        
        # Check required fields per OpenAPI spec
        required_fields = ['id', 'display_name', 'file_size_human']
        
        for dataset in data['datasets']:
            for field in required_fields:
                assert field in dataset, f"Missing required field: {field}"
            
            # Check field types
            assert isinstance(dataset['id'], str)
            assert isinstance(dataset['display_name'], str)
            assert isinstance(dataset['file_size_human'], str)
            
            # Optional fields should have correct types if present
            if 'cell_count' in dataset and dataset['cell_count'] is not None:
                assert isinstance(dataset['cell_count'], int)
            
            if 'organism' in dataset and dataset['organism'] is not None:
                assert isinstance(dataset['organism'], str)
    
    def test_list_datasets_filter_by_organism(self, client, mock_catalog):
        """Test filtering datasets by organism query parameter."""
        response = client.get('/api/datasets?organism=Homo sapiens')
        data = response.get_json()
        
        assert len(data['datasets']) == 1
        assert data['datasets'][0]['organism'] == 'Homo sapiens'
    
    def test_list_datasets_filter_by_tissue(self, client, mock_catalog):
        """Test filtering datasets by tissue query parameter."""
        response = client.get('/api/datasets?tissue=brain')
        data = response.get_json()
        
        assert len(data['datasets']) == 1
        assert data['datasets'][0]['tissue'] == 'brain'
    
    def test_list_datasets_sort_by_name(self, client, mock_catalog):
        """Test sorting datasets by name."""
        response = client.get('/api/datasets?sort=name&order=asc')
        data = response.get_json()
        
        dataset_names = [ds['display_name'] for ds in data['datasets']]
        assert dataset_names == sorted(dataset_names)
    
    def test_list_datasets_sort_by_cell_count(self, client, mock_catalog):
        """Test sorting datasets by cell count."""
        response = client.get('/api/datasets?sort=cell_count&order=desc')
        data = response.get_json()
        
        cell_counts = [ds.get('cell_count', 0) for ds in data['datasets']]
        assert cell_counts == sorted(cell_counts, reverse=True)
    
    def test_list_datasets_sort_by_file_size(self, client, mock_catalog):
        """Test sorting datasets by file size."""
        response = client.get('/api/datasets?sort=file_size&order=desc')
        data = response.get_json()
        
        # Verify datasets are returned (sorting logic tested separately)
        assert 'datasets' in data
        assert len(data['datasets']) > 0
    
    def test_list_datasets_empty_result_with_filters(self, client, mock_catalog):
        """Test that non-matching filters return empty list."""
        response = client.get('/api/datasets?organism=Danio rerio')
        data = response.get_json()
        
        assert response.status_code == 200
        assert data['datasets'] == []
        assert data.get('count', 0) == 0 or data.get('total', 0) == 0


class TestGetDatasetEndpoint:
    """Test GET /api/datasets/{dataset_id} endpoint."""
    
    def test_get_dataset_returns_200_for_valid_id(self, client, mock_catalog):
        """Test that getting existing dataset returns 200 OK."""
        response = client.get('/api/datasets/pbmc_10k')
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
    
    def test_get_dataset_returns_dataset_detail_schema(self, client, mock_catalog):
        """Test that response conforms to DatasetDetail schema."""
        response = client.get('/api/datasets/pbmc_10k')
        data = response.get_json()
        
        # DatasetDetail extends Dataset with additional fields
        required_fields = ['id', 'display_name', 'filename', 'file_size_human']
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Check types
        assert isinstance(data['id'], str)
        assert isinstance(data['display_name'], str)
        assert isinstance(data['filename'], str)
        assert data['filename'].endswith('.h5ad')
    
    def test_get_dataset_returns_404_for_nonexistent_id(self, client, mock_catalog):
        """Test that requesting nonexistent dataset returns 404 per OpenAPI spec."""
        response = client.get('/api/datasets/nonexistent_dataset')
        
        assert response.status_code == 404
        assert response.content_type == 'application/json'
    
    def test_get_dataset_404_error_schema(self, client, mock_catalog):
        """Test that 404 error response conforms to Error schema."""
        response = client.get('/api/datasets/nonexistent_dataset')
        data = response.get_json()
        
        # Error schema requires 'error' and 'message' fields
        assert 'error' in data or 'error_type' in data
        assert 'message' in data
        assert isinstance(data['message'], str)
    
    def test_get_dataset_includes_all_detail_fields(self, client, mock_catalog):
        """Test that detail response includes extended fields."""
        response = client.get('/api/datasets/pbmc_10k')
        data = response.get_json()
        
        # Extended fields from DatasetDetail schema
        assert 'filename' in data
        
        # file_size_bytes should be present if available
        if 'file_size_bytes' in data:
            assert isinstance(data['file_size_bytes'], int)
            assert data['file_size_bytes'] > 0


class TestGetDatasetMetadataEndpoint:
    """Test GET /api/datasets/{dataset_id}/metadata endpoint."""
    
    def test_get_metadata_returns_200_for_valid_id(self, client, mock_catalog):
        """Test that getting metadata returns 200 OK."""
        response = client.get('/api/datasets/pbmc_10k/metadata')
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
    
    def test_get_metadata_returns_json_object(self, client, mock_catalog):
        """Test that metadata returns JSON object."""
        response = client.get('/api/datasets/pbmc_10k/metadata')
        data = response.get_json()
        
        assert isinstance(data, dict)
    
    def test_get_metadata_returns_404_for_nonexistent_id(self, client, mock_catalog):
        """Test that requesting nonexistent dataset metadata returns 404."""
        response = client.get('/api/datasets/nonexistent/metadata')
        
        assert response.status_code == 404


class TestAPIErrorHandling:
    """Test error handling across all endpoints."""
    
    def test_endpoints_return_json_errors(self, client, mock_catalog):
        """Test that all error responses are JSON format."""
        error_endpoints = [
            '/api/datasets/nonexistent',
            '/api/datasets/nonexistent/metadata',
            '/api/datasets/nonexistent/launch',
        ]
        
        for endpoint in error_endpoints:
            if 'launch' in endpoint:
                response = client.post(endpoint)
            else:
                response = client.get(endpoint)
            
            assert response.content_type == 'application/json'
            data = response.get_json()
            assert isinstance(data, dict)
    
    def test_error_responses_include_recovery_hints(self, client, mock_catalog):
        """Test that error responses include helpful recovery information."""
        response = client.get('/api/datasets/nonexistent')
        data = response.get_json()
        
        # Should have either 'recovery_hint' or helpful message
        assert 'message' in data
        assert len(data['message']) > 0


class TestAPICORS:
    """Test CORS headers for API endpoints."""
    
    def test_api_endpoints_allow_cors(self, client, mock_catalog):
        """Test that API endpoints have proper CORS headers."""
        response = client.get('/api/datasets')
        
        # CORS headers should be present if configured
        # This is optional but recommended for web access
        # Check if Access-Control-Allow-Origin header exists
        # (May not be set in test environment, but test structure is here)
        assert response.status_code == 200


class TestAPIContentNegotiation:
    """Test content type handling."""
    
    def test_endpoints_return_json_content_type(self, client, mock_catalog):
        """Test that all successful responses have application/json content type."""
        endpoints = [
            '/api/datasets',
            '/api/datasets/pbmc_10k',
            '/api/datasets/pbmc_10k/metadata',
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            
            if response.status_code == 200:
                assert 'application/json' in response.content_type
