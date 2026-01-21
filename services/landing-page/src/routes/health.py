"""
Health Check Endpoint

Provides health status for the landing page service.

Constitutional Alignment:
- Principle IV (Fail-Fast): Reports service health explicitly
"""

from flask import Blueprint, jsonify
import logging

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON response with service status
    """
    return jsonify({
        'status': 'healthy',
        'service': 'cellxgene-landing-page',
        'version': '1.0.0'
    }), 200
