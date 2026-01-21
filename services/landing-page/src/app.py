"""
Flask Application

Main Flask application for CellXGene Explorer landing page.

Constitutional Alignment:
- Principle IV (Fail-Fast): Validates on startup
- Principle II (Modular Architecture): Clear separation of concerns
- Principle III (Code Clarity): Well-documented initialization
"""

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import atexit
from pathlib import Path

from .config import load_config
from .logging_config import setup_logging
from .routes import health_bp, datasets_bp
from .startup import validate_and_initialize
from .errors import format_error_response
from .services.container_manager import CellxgeneContainerManager


def create_app(config=None):
    """
    Flask application factory.
    
    Args:
        config: Optional configuration override
        
    Returns:
        Configured Flask application
    """
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    
    # Load configuration
    if config is None:
        service_config = load_config()
    else:
        service_config = config
    
    # Setup logging
    logger = setup_logging(
        'cellxgene-landing-page',
        service_config.log_level,
        service_config.log_directory / 'landing-page.log',
        enable_console=True
    )
    
    # Run startup validation
    logger.info("Initializing application...")
    service_config, catalog = validate_and_initialize(logger)
    
    # Initialize container manager for dynamic CellXGene instances
    # Pass both container path and host path for volume mounting
    import os
    host_data_dir = os.environ.get('HOST_DATA_DIRECTORY', str(service_config.data_directory))
    logger.info(f"Using host data directory for container spawning: {host_data_dir}")
    
    container_manager = CellxgeneContainerManager(
        data_directory=str(service_config.data_directory),
        network_name="cellxgene_stack_cellxgene-network",
        host_data_directory=host_data_dir
    )
    logger.info("Container manager initialized")
    
    # Initialize background scheduler for container cleanup
    scheduler = BackgroundScheduler(daemon=True)
    # Run cleanup every 5 minutes, remove containers inactive for 48 hours (172800 seconds)
    scheduler.add_job(
        func=lambda: container_manager.cleanup_inactive(max_inactive_seconds=172800),
        trigger='interval',
        minutes=5,
        id='cleanup_inactive_containers',
        name='Cleanup inactive CellXGene containers',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Background scheduler started - checking for inactive containers every 5 minutes (48 hour timeout)")
    
    # Ensure scheduler shuts down when app terminates
    atexit.register(lambda: scheduler.shutdown())
    
    # Store configuration in app
    app.config['SERVICE_CONFIG'] = service_config
    app.config['CATALOG'] = catalog
    app.config['CONTAINER_MANAGER'] = container_manager
    app.config['CELLXGENE_URL'] = service_config.cellxgene_url
    app.config['DEBUG'] = service_config.debug
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Register blueprints
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(datasets_bp, url_prefix='/api')
    
    # Landing page route
    @app.route('/')
    def index():
        """Serve the landing page."""
        return render_template('index.html')
    
    # Static file serving
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Serve static files."""
        return send_from_directory(app.static_folder, filename)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return {
            'error_type': 'NotFound',
            'message': 'The requested resource was not found',
            'recovery_hint': 'Check the URL and try again'
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {str(error)}", exc_info=True)
        error_response, status_code = format_error_response(error, 500)
        return error_response, status_code
    
    logger.info("Application initialized successfully")
    
    return app


def main():
    """
    Main entry point for running the application.
    """
    app = create_app()
    config = app.config['SERVICE_CONFIG']
    
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug
    )


if __name__ == '__main__':
    main()
