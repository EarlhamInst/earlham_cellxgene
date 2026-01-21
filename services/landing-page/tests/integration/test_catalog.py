"""
Integration tests for dataset catalog generation

Tests the complete catalog workflow including:
- Scanning datasets from filesystem
- Loading and validating metadata
- Building catalog with multiple datasets
- Catalog filtering and sorting

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive integration test coverage
- Principle IV (Fail-Fast): Verify fail-fast validation behavior
"""

import pytest
import json
from pathlib import Path
import tempfile
import shutil

from src.services.scanner import DatasetScanner
from src.services.catalog import DatasetCatalog
from src.models.dataset import Dataset
from src.errors import ValidationError, FileAccessError


class TestCatalogGeneration:
    """Test end-to-end catalog generation from filesystem."""
    
    @pytest.fixture
    def test_data_dir(self):
        """Create temporary data directory with test datasets."""
        temp_dir = tempfile.mkdtemp()
        data_path = Path(temp_dir)
        
        yield data_path
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def _create_h5ad_file(self, path: Path):
        """Create a minimal valid h5ad file with HDF5 signature."""
        hdf5_sig = b'\x89HDF\r\n\x1a\n'
        path.write_bytes(hdf5_sig + b'x' * 1000)
    
    def _create_metadata_file(self, path: Path, metadata: dict):
        """Create metadata JSON file."""
        path.write_text(json.dumps(metadata, indent=2))
    
    def test_catalog_generation_with_single_dataset(self, test_data_dir):
        """Test catalog generation with one valid dataset."""
        # Create h5ad file
        h5ad_path = test_data_dir / "pbmc_3k.h5ad"
        self._create_h5ad_file(h5ad_path)
        
        # Create metadata
        metadata = {
            'name': 'PBMC 3k Dataset',
            'description': '3,000 peripheral blood cells',
            'organism': 'Homo sapiens',
            'tissue': 'blood',
            'assay': '10x 3\' v3',
            'cell_count': 3000,
            'gene_count': 32738
        }
        self._create_metadata_file(test_data_dir / "pbmc_3k.json", metadata)
        
        # Scan and build catalog
        scanner = DatasetScanner(test_data_dir)
        valid_datasets, invalid_datasets = scanner.scan()
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Verify catalog
        assert catalog.count() == 1
        assert len(invalid_datasets) == 0
        
        # Retrieve dataset
        dataset = catalog.get_by_id('pbmc_3k')
        assert dataset is not None
        assert dataset.display_name == 'PBMC 3k Dataset'
        assert dataset.cell_count == 3000
    
    def test_catalog_generation_with_multiple_datasets(self, test_data_dir):
        """Test catalog generation with multiple valid datasets."""
        datasets_to_create = [
            {
                'id': 'pbmc_10k',
                'name': 'PBMC 10k',
                'description': '10,000 cells',
                'organism': 'Homo sapiens',
                'tissue': 'blood',
                'assay': '10x 3\' v3',
                'cell_count': 10000
            },
            {
                'id': 'brain_5k',
                'name': 'Brain 5k',
                'description': '5,000 brain cells',
                'organism': 'Mus musculus',
                'tissue': 'brain',
                'assay': 'Smart-seq2',
                'cell_count': 5000
            },
            {
                'id': 'heart_2k',
                'name': 'Heart 2k',
                'description': '2,000 heart cells',
                'organism': 'Homo sapiens',
                'tissue': 'heart',
                'assay': '10x 5\' v2',
                'cell_count': 2000
            }
        ]
        
        # Create all datasets
        for ds_info in datasets_to_create:
            h5ad_path = test_data_dir / f"{ds_info['id']}.h5ad"
            self._create_h5ad_file(h5ad_path)
            
            metadata = {k: v for k, v in ds_info.items() if k != 'id'}
            self._create_metadata_file(test_data_dir / f"{ds_info['id']}.json", metadata)
        
        # Scan and build catalog
        scanner = DatasetScanner(test_data_dir)
        valid_datasets, invalid_datasets = scanner.scan()
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Verify catalog
        assert catalog.count() == 3
        assert len(invalid_datasets) == 0
        
        # Test retrieval
        all_datasets = catalog.get_all()
        assert len(all_datasets) == 3
        
        # Verify each dataset
        dataset_ids = [ds.id for ds in all_datasets]
        assert 'pbmc_10k' in dataset_ids
        assert 'brain_5k' in dataset_ids
        assert 'heart_2k' in dataset_ids
    
    def test_catalog_generation_filters_invalid_datasets(self, test_data_dir):
        """Test that invalid datasets are excluded from catalog."""
        # Create valid dataset
        h5ad_valid = test_data_dir / "valid.h5ad"
        self._create_h5ad_file(h5ad_valid)
        self._create_metadata_file(
            test_data_dir / "valid.json",
            {
                'name': 'Valid Dataset',
                'description': 'Valid',
                'organism': 'Test',
                'tissue': 'Test',
                'assay': 'Test'
            }
        )
        
        # Create invalid dataset (no metadata)
        h5ad_invalid = test_data_dir / "invalid.h5ad"
        self._create_h5ad_file(h5ad_invalid)
        # No metadata file for invalid dataset
        
        # Scan and build catalog
        scanner = DatasetScanner(test_data_dir)
        valid_datasets, invalid_datasets = scanner.scan()
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Only valid dataset should be in catalog
        assert catalog.count() == 1
        assert len(invalid_datasets) == 1
        assert invalid_datasets[0][0] == 'invalid'
        
        # Verify only valid dataset in catalog
        dataset = catalog.get_by_id('valid')
        assert dataset is not None
        
        invalid_dataset = catalog.get_by_id('invalid')
        assert invalid_dataset is None
    
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
        
        # Create invalid dataset
        h5ad_invalid = test_data_dir / "invalid.h5ad"
        self._create_h5ad_file(h5ad_invalid)
        # No metadata
        
        # Scan with fail_on_invalid=True should raise exception
        scanner = DatasetScanner(test_data_dir)
        
        with pytest.raises(ValidationError):
            scanner.scan(fail_on_invalid=True)
    
    def test_catalog_filtering_by_organism(self, test_data_dir):
        """Test catalog filtering by organism."""
        # Create datasets with different organisms
        datasets = [
            ('human1', 'Homo sapiens'),
            ('human2', 'Homo sapiens'),
            ('mouse1', 'Mus musculus'),
        ]
        
        for ds_id, organism in datasets:
            self._create_h5ad_file(test_data_dir / f"{ds_id}.h5ad")
            self._create_metadata_file(
                test_data_dir / f"{ds_id}.json",
                {
                    'name': ds_id,
                    'description': 'Test',
                    'organism': organism,
                    'tissue': 'Test',
                    'assay': 'Test'
                }
            )
        
        # Build catalog
        scanner = DatasetScanner(test_data_dir)
        valid_datasets, _ = scanner.scan()
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Filter by organism
        human_datasets = catalog.filter_by(organism='Homo sapiens')
        assert len(human_datasets) == 2
        
        mouse_datasets = catalog.filter_by(organism='Mus musculus')
        assert len(mouse_datasets) == 1
    
    def test_catalog_filtering_by_tissue(self, test_data_dir):
        """Test catalog filtering by tissue."""
        # Create datasets with different tissues
        datasets = [
            ('blood1', 'blood'),
            ('blood2', 'blood'),
            ('brain1', 'brain'),
        ]
        
        for ds_id, tissue in datasets:
            self._create_h5ad_file(test_data_dir / f"{ds_id}.h5ad")
            self._create_metadata_file(
                test_data_dir / f"{ds_id}.json",
                {
                    'name': ds_id,
                    'description': 'Test',
                    'organism': 'Test',
                    'tissue': tissue,
                    'assay': 'Test'
                }
            )
        
        # Build catalog
        scanner = DatasetScanner(test_data_dir)
        valid_datasets, _ = scanner.scan()
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Filter by tissue
        blood_datasets = catalog.filter_by(tissue='blood')
        assert len(blood_datasets) == 2
        
        brain_datasets = catalog.filter_by(tissue='brain')
        assert len(brain_datasets) == 1
    
    def test_catalog_sorting_by_name(self, test_data_dir):
        """Test catalog sorting by dataset name."""
        # Create datasets with different names
        names = ['Zebra Dataset', 'Alpha Dataset', 'Beta Dataset']
        
        for i, name in enumerate(names):
            ds_id = f"dataset_{i}"
            self._create_h5ad_file(test_data_dir / f"{ds_id}.h5ad")
            self._create_metadata_file(
                test_data_dir / f"{ds_id}.json",
                {
                    'name': name,
                    'description': 'Test',
                    'organism': 'Test',
                    'tissue': 'Test',
                    'assay': 'Test'
                }
            )
        
        # Build catalog
        scanner = DatasetScanner(test_data_dir)
        valid_datasets, _ = scanner.scan()
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Sort by name
        sorted_datasets = catalog.sort_by('name')
        sorted_names = [ds.display_name for ds in sorted_datasets]
        
        assert sorted_names == ['Alpha Dataset', 'Beta Dataset', 'Zebra Dataset']
    
    def test_catalog_sorting_by_cell_count(self, test_data_dir):
        """Test catalog sorting by cell count."""
        # Create datasets with different cell counts
        cell_counts = [10000, 5000, 8000]
        
        for i, count in enumerate(cell_counts):
            ds_id = f"dataset_{i}"
            self._create_h5ad_file(test_data_dir / f"{ds_id}.h5ad")
            self._create_metadata_file(
                test_data_dir / f"{ds_id}.json",
                {
                    'name': ds_id,
                    'description': 'Test',
                    'organism': 'Test',
                    'tissue': 'Test',
                    'assay': 'Test',
                    'cell_count': count
                }
            )
        
        # Build catalog
        scanner = DatasetScanner(test_data_dir)
        valid_datasets, _ = scanner.scan()
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Sort by cell count
        sorted_datasets = catalog.sort_by('cell_count', reverse=True)
        sorted_counts = [ds.cell_count for ds in sorted_datasets]
        
        assert sorted_counts == [10000, 8000, 5000]
    
    def test_catalog_persistence_and_reload(self, test_data_dir):
        """Test that catalog can be rebuilt from same data directory."""
        # Create dataset
        self._create_h5ad_file(test_data_dir / "test.h5ad")
        self._create_metadata_file(
            test_data_dir / "test.json",
            {
                'name': 'Test Dataset',
                'description': 'Test',
                'organism': 'Test',
                'tissue': 'Test',
                'assay': 'Test',
                'cell_count': 1000
            }
        )
        
        # Build catalog first time
        scanner1 = DatasetScanner(test_data_dir)
        valid1, _ = scanner1.scan()
        
        catalog1 = DatasetCatalog()
        for ds in valid1:
            catalog1.add_dataset(ds)
        
        # Build catalog second time
        scanner2 = DatasetScanner(test_data_dir)
        valid2, _ = scanner2.scan()
        
        catalog2 = DatasetCatalog()
        for ds in valid2:
            catalog2.add_dataset(ds)
        
        # Both catalogs should be identical
        assert catalog1.count() == catalog2.count()
        
        ds1 = catalog1.get_by_id('test')
        ds2 = catalog2.get_by_id('test')
        
        assert ds1.display_name == ds2.display_name
        assert ds1.cell_count == ds2.cell_count
    
    def test_catalog_handles_missing_optional_fields(self, test_data_dir):
        """Test catalog handles datasets with missing optional metadata fields."""
        # Create dataset with minimal metadata
        self._create_h5ad_file(test_data_dir / "minimal.h5ad")
        self._create_metadata_file(
            test_data_dir / "minimal.json",
            {
                'name': 'Minimal Dataset',
                'description': 'Minimal metadata',
                'organism': 'Test',
                'tissue': 'Test',
                'assay': 'Test'
                # No cell_count, gene_count, doi, etc.
            }
        )
        
        # Build catalog
        scanner = DatasetScanner(test_data_dir)
        valid_datasets, invalid_datasets = scanner.scan()
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Should successfully include dataset
        assert catalog.count() == 1
        assert len(invalid_datasets) == 0
        
        dataset = catalog.get_by_id('minimal')
        assert dataset.cell_count is None  # Optional field not present
        assert dataset.gene_count is None


class TestCatalogErrorHandling:
    """Test error handling in catalog generation."""
    
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
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Should succeed with empty catalog
        assert catalog.count() == 0
        assert len(valid_datasets) == 0
        assert len(invalid_datasets) == 0


class TestCatalogConcurrency:
    """Test catalog behavior with concurrent access."""
    
    def test_catalog_thread_safe_reads(self, tmp_path):
        """Test that catalog supports concurrent reads."""
        # Create dataset
        h5ad_file = tmp_path / "test.h5ad"
        hdf5_sig = b'\x89HDF\r\n\x1a\n'
        h5ad_file.write_bytes(hdf5_sig + b'x' * 1000)
        
        metadata = {
            'name': 'Test',
            'description': 'Test',
            'organism': 'Test',
            'tissue': 'Test',
            'assay': 'Test'
        }
        (tmp_path / "test.json").write_text(json.dumps(metadata))
        
        # Build catalog
        scanner = DatasetScanner(tmp_path)
        valid_datasets, _ = scanner.scan()
        
        catalog = DatasetCatalog()
        for dataset in valid_datasets:
            catalog.add_dataset(dataset)
        
        # Multiple concurrent reads should work
        import threading
        
        results = []
        
        def read_catalog():
            dataset = catalog.get_by_id('test')
            results.append(dataset is not None)
        
        threads = [threading.Thread(target=read_catalog) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All reads should succeed
        assert all(results)
        assert len(results) == 5
