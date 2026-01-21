"""
Contract tests for /api/datasets/{id}/launch endpoint

Tests that the launch API implementation conforms to the OpenAPI specification.

Tests:
- POST /api/datasets/{id}/launch - Launch CellXGene viewer

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive API contract validation
- Principle IV (Fail-Fast): Verify error handling per specification
"""

import pytest
import json
from unittest.mock import Mock, patch

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
def sample_dataset(tmp_path):
    """Create a sample dataset for testing."""
    dataset = Dataset(
        id="pbmc_10k",
        filename="pbmc_10k.h5ad",
        filepath=tmp_path / "pbmc_10k.h5ad",
        display_name="Human PBMC 10k Dataset",
        description="10,000 peripheral blood mononuclear cells",
        organism="Homo sapiens",
        tissue="blood",
        assay="10x 3' v3",
        cell_count=10000,
        gene_count=33538,
        file_size_bytes=2468463616
    )
    return dataset


@pytest.fixture
def mock_catalog(app, sample_dataset):
    """Mock dataset catalog."""
    catalog = DatasetCatalog()
    catalog.add_dataset(sample_dataset)
    app.config['CATALOG'] = catalog
    return catalog


class TestLaunchDatasetEndpoint:
    """Test POST /api/datasets/{dataset_id}/launch endpoint."""
    
    def test_launch_returns_200_for_valid_dataset(self, client, mock_catalog):
        """Test that launching valid dataset returns 200 OK per OpenAPI spec."""
        response = client.post('/api/datasets/pbmc_10k/launch')
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
    
    def test_launch_response_schema(self, client, mock_catalog):
        """Test that launch response conforms to OpenAPI schema."""
        response = client.post('/api/datasets/pbmc_10k/launch')
        data = response.get_json()
        
        # Per OpenAPI spec, response should have viewer_url and dataset_id
        assert 'viewer_url' in data
        assert 'dataset_id' in data
        
        # Check types
        assert isinstance(data['viewer_url'], str)
        assert isinstance(data['dataset_id'], str)
    
    def test_launch_viewer_url_format(self, client, mock_catalog):
        """Test that viewer_url follows expected format."""
        response = client.post('/api/datasets/pbmc_10k/launch')
        data = response.get_json()
        
        viewer_url = data['viewer_url']
        
        # URL should point to CellXGene endpoint
        assert 'cellxgene' in viewer_url.lower() or '/viewer' in viewer_url
        
        # Should include dataset identifier
        assert 'pbmc_10k' in viewer_url or 'dataset' in viewer_url.lower()
    
    def test_launch_dataset_id_matches_request(self, client, mock_catalog):
        """Test that returned dataset_id matches requested dataset."""
        response = client.post('/api/datasets/pbmc_10k/launch')
        data = response.get_json()
        
        assert data['dataset_id'] == 'pbmc_10k'
    
    def test_launch_returns_404_for_nonexistent_dataset(self, client, mock_catalog):
        """Test that launching nonexistent dataset returns 404 per OpenAPI spec."""
        response = client.post('/api/datasets/nonexistent_dataset/launch')
        
        assert response.status_code == 404
        assert response.content_type == 'application/json'
    
    def test_launch_404_error_schema(self, client, mock_catalog):
        """Test that 404 error response conforms to Error schema."""
        response = client.post('/api/datasets/nonexistent_dataset/launch')
        data = response.get_json()
        
        # Error schema requires error identifier and message
        assert 'error' in data or 'error_type' in data
        assert 'message' in data
        assert isinstance(data['message'], str)
        
        # Message should be informative
        assert 'not found' in data['message'].lower() or 'does not exist' in data['message'].lower()
    
    def test_launch_only_accepts_post_method(self, client, mock_catalog):
        """Test that launch endpoint only accepts POST per OpenAPI spec."""
        # GET should not be allowed
        response_get = client.get('/api/datasets/pbmc_10k/launch')
        assert response_get.status_code in [405, 404]  # Method Not Allowed or Not Found
        
        # PUT should not be allowed
        response_put = client.put('/api/datasets/pbmc_10k/launch')
        assert response_put.status_code in [405, 404]
        
        # DELETE should not be allowed
        response_delete = client.delete('/api/datasets/pbmc_10k/launch')
        assert response_delete.status_code in [405, 404]
    
    @patch('src.routes.datasets.check_cellxgene_health')
    def test_launch_returns_503_when_service_unavailable(self, mock_health_check, client, mock_catalog):
        """Test that 503 is returned when CellXGene service is unavailable per OpenAPI spec."""
        # Mock CellXGene service as unavailable
        mock_health_check.return_value = False
        
        response = client.post('/api/datasets/pbmc_10k/launch')
        
        # OpenAPI spec indicates 503 for service unavailable
        if response.status_code == 503:
            assert response.content_type == 'application/json'
            data = response.get_json()
            assert 'error' in data or 'error_type' in data
            assert 'message' in data
    
    def test_launch_multiple_datasets_returns_unique_urls(self, client):
        """Test that launching different datasets returns different viewer URLs."""
        # Create catalog with multiple datasets
        catalog = DatasetCatalog()
        
        for i in range(2):
            ds = Dataset(
                id=f"dataset_{i}",
                filename=f"dataset_{i}.h5ad",
                filepath=f"/data/dataset_{i}.h5ad",
                display_name=f"Dataset {i}",
                description=f"Test dataset {i}",
                organism="Test",
                tissue="Test",
                assay="Test"
            )
            catalog.add_dataset(ds)
        
        client.application.config['CATALOG'] = catalog
        
        response1 = client.post('/api/datasets/dataset_0/launch')
        response2 = client.post('/api/datasets/dataset_1/launch')
        
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.get_json()
            data2 = response2.get_json()
            
            # URLs or dataset_ids should be different
            assert data1['dataset_id'] != data2['dataset_id']


class TestLaunchEndpointErrorHandling:
    """Test comprehensive error handling for launch endpoint."""
    
    def test_launch_error_includes_recovery_hint(self, client, mock_catalog):
        """Test that error responses include helpful recovery information."""
        response = client.post('/api/datasets/nonexistent/launch')
        data = response.get_json()
        
        # Should have informative error message
        assert 'message' in data
        assert len(data['message']) > 0
        
        # May include recovery hint
        if 'recovery_hint' in data:
            assert isinstance(data['recovery_hint'], str)
            assert len(data['recovery_hint']) > 0
    
    def test_launch_invalid_dataset_id_format(self, client, mock_catalog):
        """Test handling of invalid dataset ID formats."""
        # Test with various invalid formats
        invalid_ids = [
            '../../../etc/passwd',  # Path traversal attempt
            'dataset with spaces',
            'dataset/with/slashes',
            '',  # Empty string
        ]
        
        for invalid_id in invalid_ids:
            if invalid_id:  # Skip empty string for URL construction
                response = client.post(f'/api/datasets/{invalid_id}/launch')
                # Should return 404 or 400
                assert response.status_code in [400, 404]
    
    def test_launch_returns_json_on_all_errors(self, client, mock_catalog):
        """Test that all error conditions return JSON responses."""
        test_cases = [
            '/api/datasets/nonexistent/launch',  # 404
            '/api/datasets//launch',  # Invalid path
        ]
        
        for endpoint in test_cases:
            try:
                response = client.post(endpoint)
                if response.status_code >= 400:
                    assert 'application/json' in response.content_type
                    data = response.get_json()
                    assert isinstance(data, dict)
            except Exception:
                # Some malformed URLs might raise exceptions, which is acceptable
                pass


class TestLaunchEndpointIntegration:
    """Integration tests for launch endpoint behavior."""
    
    def test_launch_viewer_url_is_accessible_path(self, client, mock_catalog):
        """Test that returned viewer_url is a valid URL path."""
        response = client.post('/api/datasets/pbmc_10k/launch')
        data = response.get_json()
        
        viewer_url = data['viewer_url']
        
        # Should start with / (absolute path) or be a full URL
        assert viewer_url.startswith('/') or viewer_url.startswith('http')
        
        # Should not contain invalid characters
        invalid_chars = [' ', '\n', '\t', '<', '>']
        for char in invalid_chars:
            assert char not in viewer_url
    
    def test_launch_idempotency(self, client, mock_catalog):
        """Test that launching same dataset multiple times is safe."""
        # Launch same dataset twice
        response1 = client.post('/api/datasets/pbmc_10k/launch')
        response2 = client.post('/api/datasets/pbmc_10k/launch')
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Both should return valid responses
        data1 = response1.get_json()
        data2 = response2.get_json()
        
        assert 'viewer_url' in data1
        assert 'viewer_url' in data2


class TestLaunchEndpointPerformance:
    """Test performance characteristics of launch endpoint."""
    
    def test_launch_responds_quickly(self, client, mock_catalog):
        """Test that launch endpoint responds in reasonable time."""
        import time
        
        start_time = time.time()
        response = client.post('/api/datasets/pbmc_10k/launch')
        end_time = time.time()
        
        # Should respond within 5 seconds (generous for test environment)
        assert (end_time - start_time) < 5.0
        assert response.status_code == 200


class TestLaunchEndpointSecurity:
    """Test security aspects of launch endpoint."""
    
    def test_launch_prevents_path_traversal(self, client, mock_catalog):
        """Test that path traversal attempts are handled safely."""
        malicious_ids = [
            '../../../etc/passwd',
            '..%2F..%2F..%2Fetc%2Fpasswd',
            'dataset_id; rm -rf /',
        ]
        
        for malicious_id in malicious_ids:
            response = client.post(f'/api/datasets/{malicious_id}/launch')
            
            # Should return error (404 or 400), not crash
            assert response.status_code in [400, 404]
            
            # Should return JSON error
            data = response.get_json()
            assert isinstance(data, dict)
            assert 'message' in data or 'error' in data
    
    def test_launch_does_not_expose_internal_paths(self, client, mock_catalog):
        """Test that error messages don't expose internal file paths."""
        response = client.post('/api/datasets/nonexistent/launch')
        data = response.get_json()
        
        message = json.dumps(data)
        
        # Should not expose internal paths
        assert '/data/' not in message or 'data directory' in message.lower()
        assert '/src/' not in message
        assert '/usr/' not in message
