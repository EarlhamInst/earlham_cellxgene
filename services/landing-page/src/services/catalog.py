"""
Dataset Catalog Service

Manages the collection of available datasets with filtering and sorting.

Constitutional Alignment:
- Principle II (Modular Architecture): Isolated catalog management
- Principle III (Code Clarity): Clear API for dataset operations
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..models.dataset import Dataset


class DatasetCatalog:
    """
    Manages the catalog of available datasets.
    
    Provides filtering, sorting, and search capabilities over the dataset collection.
    """
    
    def __init__(self, datasets: List[Dataset], logger: logging.Logger = None):
        """
        Initialize catalog with dataset list.
        
        Args:
            datasets: List of Dataset instances
            logger: Optional logger instance
        """
        self.datasets = datasets
        self.logger = logger or logging.getLogger(__name__)
        self._index = {ds.id: ds for ds in datasets}
        self.last_updated = datetime.utcnow()
    
    def get_all(self) -> List[Dataset]:
        """
        Get all datasets in catalog.
        
        Returns:
            List of all Dataset instances
        """
        return self.datasets
    
    def get_by_id(self, dataset_id: str) -> Optional[Dataset]:
        """
        Get a specific dataset by ID.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Dataset instance or None if not found
        """
        return self._index.get(dataset_id)
    
    def filter_by_organism(self, organism: str) -> List[Dataset]:
        """
        Filter datasets by organism.
        
        Args:
            organism: Organism name (case-insensitive)
            
        Returns:
            List of matching datasets
        """
        organism_lower = organism.lower()
        return [
            ds for ds in self.datasets
            if ds.organism.lower() == organism_lower
        ]
    
    def filter_by_tissue(self, tissue: str) -> List[Dataset]:
        """
        Filter datasets by tissue type.
        
        Args:
            tissue: Tissue type (case-insensitive)
            
        Returns:
            List of matching datasets
        """
        tissue_lower = tissue.lower()
        return [
            ds for ds in self.datasets
            if ds.tissue.lower() == tissue_lower
        ]
    
    def filter_by_assay(self, assay: str) -> List[Dataset]:
        """
        Filter datasets by assay type.
        
        Args:
            assay: Assay type (case-insensitive)
            
        Returns:
            List of matching datasets
        """
        assay_lower = assay.lower()
        return [
            ds for ds in self.datasets
            if ds.assay.lower() == assay_lower
        ]
    
    def search(self, query: str) -> List[Dataset]:
        """
        Search datasets by name or description.
        
        Args:
            query: Search query (case-insensitive)
            
        Returns:
            List of matching datasets
        """
        query_lower = query.lower()
        
        return [
            ds for ds in self.datasets
            if query_lower in ds.display_name.lower()
            or query_lower in ds.description.lower()
        ]
    
    def sort_by_name(self, reverse: bool = False) -> List[Dataset]:
        """
        Sort datasets by display name.
        
        Args:
            reverse: If True, sort in descending order
            
        Returns:
            Sorted list of datasets
        """
        return sorted(
            self.datasets,
            key=lambda ds: ds.display_name.lower(),
            reverse=reverse
        )
    
    def sort_by_cell_count(self, reverse: bool = True) -> List[Dataset]:
        """
        Sort datasets by cell count.
        
        Args:
            reverse: If True, sort largest first (default)
            
        Returns:
            Sorted list of datasets
        """
        # Put datasets without cell_count at the end
        with_count = [ds for ds in self.datasets if ds.cell_count is not None]
        without_count = [ds for ds in self.datasets if ds.cell_count is None]
        
        sorted_with_count = sorted(
            with_count,
            key=lambda ds: ds.cell_count,
            reverse=reverse
        )
        
        return sorted_with_count + without_count
    
    def sort_by_file_size(self, reverse: bool = True) -> List[Dataset]:
        """
        Sort datasets by file size.
        
        Args:
            reverse: If True, sort largest first (default)
            
        Returns:
            Sorted list of datasets
        """
        return sorted(
            self.datasets,
            key=lambda ds: ds.file_size_bytes or 0,
            reverse=reverse
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get catalog statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_cells = sum(ds.cell_count or 0 for ds in self.datasets)
        total_size = sum(ds.file_size_bytes or 0 for ds in self.datasets)
        
        organisms = set(ds.organism for ds in self.datasets)
        tissues = set(ds.tissue for ds in self.datasets)
        assays = set(ds.assay for ds in self.datasets)
        
        return {
            'total_datasets': len(self.datasets),
            'total_cells': total_cells,
            'total_size_bytes': total_size,
            'unique_organisms': len(organisms),
            'unique_tissues': len(tissues),
            'unique_assays': len(assays),
            'organisms': sorted(organisms),
            'tissues': sorted(tissues),
            'assays': sorted(assays),
            'last_updated': self.last_updated.isoformat() + 'Z'
        }
    
    def to_json_list(self) -> List[Dict[str, Any]]:
        """
        Convert catalog to list of dictionaries for API responses.
        
        Returns:
            List of dataset dictionaries
        """
        return [ds.to_dict() for ds in self.datasets]
    
    def refresh(self, new_datasets: List[Dataset]) -> None:
        """
        Refresh catalog with new dataset list.
        
        Args:
            new_datasets: New list of datasets
        """
        self.datasets = new_datasets
        self._index = {ds.id: ds for ds in new_datasets}
        self.last_updated = datetime.utcnow()
        
        self.logger.info(f"Catalog refreshed with {len(new_datasets)} datasets")
    
    def __len__(self) -> int:
        """Return number of datasets in catalog."""
        return len(self.datasets)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"DatasetCatalog(datasets={len(self.datasets)})"
