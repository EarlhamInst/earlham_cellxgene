"""
Dataset API Routes

Provides REST API for dataset catalog and operations.

Constitutional Alignment:
- Principle IV (Fail-Fast): Clear error responses
- Principle VI (Accessibility): User-friendly error messages
"""

from flask import Blueprint, jsonify, request, current_app
import logging
from typing import Dict, Any

from ..errors import DatasetNotFoundError, format_error_response

datasets_bp = Blueprint('datasets', __name__)
logger = logging.getLogger(__name__)


@datasets_bp.route('/datasets', methods=['GET'])
def list_datasets():
    """
    List all available datasets.
    
    Query parameters:
        - organism: Filter by organism
        - tissue: Filter by tissue
        - assay: Filter by assay
        - search: Search in name and description
        - sort: Sort by (name, cell_count, file_size)
        - order: Sort order (asc, desc)
    
    Returns:
        JSON response with dataset list
    """
    try:
        catalog = current_app.config['CATALOG']
        
        # Get query parameters
        organism = request.args.get('organism')
        tissue = request.args.get('tissue')
        assay = request.args.get('assay')
        search_query = request.args.get('search')
        sort_by = request.args.get('sort', 'name')
        order = request.args.get('order', 'asc')
        
        # Start with all datasets
        datasets = catalog.get_all()
        
        # Apply filters
        if organism:
            datasets = [ds for ds in datasets if ds.organism.lower() == organism.lower()]
        
        if tissue:
            datasets = [ds for ds in datasets if ds.tissue.lower() == tissue.lower()]
        
        if assay:
            datasets = [ds for ds in datasets if ds.assay.lower() == assay.lower()]
        
        if search_query:
            search_lower = search_query.lower()
            datasets = [
                ds for ds in datasets
                if search_lower in ds.display_name.lower()
                or search_lower in ds.description.lower()
            ]
        
        # Apply sorting
        if sort_by == 'cell_count':
            datasets = sorted(
                datasets,
                key=lambda ds: ds.cell_count or 0,
                reverse=(order == 'desc')
            )
        elif sort_by == 'file_size':
            datasets = sorted(
                datasets,
                key=lambda ds: ds.file_size_bytes or 0,
                reverse=(order == 'desc')
            )
        else:  # Default: sort by name
            datasets = sorted(
                datasets,
                key=lambda ds: ds.display_name.lower(),
                reverse=(order == 'desc')
            )
        
        # Convert to dictionaries
        dataset_list = [ds.to_dict() for ds in datasets]
        
        return jsonify({
            'datasets': dataset_list,
            'count': len(dataset_list),
            'filters': {
                'organism': organism,
                'tissue': tissue,
                'assay': assay,
                'search': search_query
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing datasets: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e, 500)
        return jsonify(error_response), status_code


@datasets_bp.route('/datasets/<dataset_id>', methods=['GET'])
def get_dataset(dataset_id: str):
    """
    Get details for a specific dataset.
    
    Args:
        dataset_id: Dataset identifier
    
    Returns:
        JSON response with dataset details
    """
    try:
        catalog = current_app.config['CATALOG']
        dataset = catalog.get_by_id(dataset_id)
        
        if not dataset:
            raise DatasetNotFoundError(dataset_id)
        
        return jsonify(dataset.to_dict()), 200
    
    except DatasetNotFoundError as e:
        error_response, _ = format_error_response(e, 404)
        return jsonify(error_response), 404
    
    except Exception as e:
        logger.error(f"Error getting dataset {dataset_id}: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e, 500)
        return jsonify(error_response), status_code


@datasets_bp.route('/datasets/<dataset_id>/metadata', methods=['GET'])
def get_dataset_metadata(dataset_id: str):
    """
    Get metadata for a dataset (extracted from h5ad file).
    
    Args:
        dataset_id: Dataset identifier
    
    Returns:
        JSON response with metadata
    """
    try:
        catalog = current_app.config['CATALOG']
        dataset = catalog.get_by_id(dataset_id)
        
        if not dataset:
            raise DatasetNotFoundError(dataset_id)
        
        # Return full dataset info including metadata fields
        return jsonify(dataset.to_dict()), 200
    
    except DatasetNotFoundError as e:
        error_response, _ = format_error_response(e, 404)
        return jsonify(error_response), 404
    
    except Exception as e:
        logger.error(f"Error getting metadata for {dataset_id}: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e, 500)
        return jsonify(error_response), status_code


@datasets_bp.route('/datasets/<dataset_id>/launch', methods=['POST'])
def launch_dataset(dataset_id: str):
    """
    Launch CellXGene for a specific dataset.
    
    Spawns a dedicated CellXGene container for this dataset on-demand.
    
    Args:
        dataset_id: Dataset identifier
    
    Returns:
        JSON response with CellXGene URL
    """
    try:
        catalog = current_app.config['CATALOG']
        dataset = catalog.get_by_id(dataset_id)
        
        if not dataset:
            raise DatasetNotFoundError(dataset_id)
        
        # Get container manager
        container_manager = current_app.config['CONTAINER_MANAGER']
        
        # Launch container for this dataset
        logger.info(f"Launching CellXGene container for dataset {dataset_id}")
        port = container_manager.launch_dataset(dataset_id, dataset.filename)
        
        # Construct browser-accessible URL (proxied through nginx)
        # Each dataset gets its own route: /cellxgene-{dataset_id}/
        host = request.host.split(':')[0]  # Remove port if present
        scheme = request.scheme
        cellxgene_url = f"{scheme}://{host}/cellxgene-{dataset_id}/"
        
        logger.info(f"Dataset {dataset_id} launched on port {port}, accessible at {cellxgene_url}")
        
        return jsonify({
            'dataset_id': dataset_id,
            'dataset_name': dataset.display_name,
            'cellxgene_url': cellxgene_url,
            'container_port': port,
            'status': 'ready',
            'timeout_info': 'Container will be closed after 48 hours of inactivity'
        }), 200
    
    except DatasetNotFoundError as e:
        error_response, _ = format_error_response(e, 404)
        return jsonify(error_response), 404
    
    except Exception as e:
        logger.error(f"Error launching dataset {dataset_id}: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e, 500)
        return jsonify(error_response), status_code


@datasets_bp.route('/datasets/<dataset_id>/keepalive', methods=['POST'])
def keepalive_dataset(dataset_id: str):
    """
    Keep a CellXGene container active by updating its last access time.
    
    This endpoint can be called periodically by the frontend to prevent
    the container from being cleaned up due to inactivity.
    
    Args:
        dataset_id: Dataset identifier
    
    Returns:
        JSON response with status
    """
    try:
        catalog = current_app.config['CATALOG']
        dataset = catalog.get_by_id(dataset_id)
        
        if not dataset:
            raise DatasetNotFoundError(dataset_id)
        
        # Get container manager
        container_manager = current_app.config['CONTAINER_MANAGER']
        
        # Check if container is running
        port = container_manager.get_container_port(dataset_id)
        if port is None:
            return jsonify({
                'dataset_id': dataset_id,
                'status': 'not_running',
                'message': 'Container is not currently running'
            }), 404
        
        # Update access time
        container_manager.update_access_time(dataset_id)
        logger.debug(f"Keep-alive received for dataset {dataset_id}")
        
        return jsonify({
            'dataset_id': dataset_id,
            'status': 'active',
            'message': 'Container activity updated'
        }), 200
    
    except DatasetNotFoundError as e:
        error_response, _ = format_error_response(e, 404)
        return jsonify(error_response), 404
    
    except Exception as e:
        logger.error(f"Error updating keep-alive for {dataset_id}: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e, 500)
        return jsonify(error_response), status_code


@datasets_bp.route('/datasets/<dataset_id>/status', methods=['GET'])
def get_dataset_status(dataset_id: str):
    """
    Check the status of a CellXGene container.
    
    Used by the frontend to poll until the container is ready.
    
    Args:
        dataset_id: Dataset identifier
    
    Returns:
        JSON response with container status
    """
    try:
        catalog = current_app.config['CATALOG']
        dataset = catalog.get_by_id(dataset_id)
        
        if not dataset:
            raise DatasetNotFoundError(dataset_id)
        
        # Get container manager
        container_manager = current_app.config['CONTAINER_MANAGER']
        
        # Check if container exists and get its status
        port = container_manager.get_container_port(dataset_id)
        
        if port is None:
            return jsonify({
                'dataset_id': dataset_id,
                'status': 'not_running',
                'ready': False,
                'message': 'Container is not running'
            }), 200
        
        # Check if container is ready
        is_ready = container_manager.is_container_ready(dataset_id)
        
        # Update access time when checking status to prevent premature cleanup
        if is_ready:
            container_manager.update_access_time(dataset_id)
        
        # Construct URL
        host = request.host.split(':')[0]
        scheme = request.scheme
        cellxgene_url = f"{scheme}://{host}/cellxgene-{dataset_id}/"
        
        return jsonify({
            'dataset_id': dataset_id,
            'status': 'running' if is_ready else 'starting',
            'ready': is_ready,
            'cellxgene_url': cellxgene_url if is_ready else None,
            'container_port': port,
            'message': 'Container is ready' if is_ready else 'Container is starting...'
        }), 200
    
    except DatasetNotFoundError as e:
        error_response, _ = format_error_response(e, 404)
        return jsonify(error_response), 404
    
    except Exception as e:
        logger.error(f"Error checking status for {dataset_id}: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e, 500)
        return jsonify(error_response), status_code


@datasets_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """
    Get catalog statistics.
    
    Returns:
        JSON response with statistics
    """
    try:
        catalog = current_app.config['CATALOG']
        stats = catalog.get_statistics()
        
        return jsonify(stats), 200
    
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e, 500)
        return jsonify(error_response), status_code
