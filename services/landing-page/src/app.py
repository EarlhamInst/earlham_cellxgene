"""
Flask Application

Main Flask application for CellXGene Explorer landing page.

Constitutional Alignment:
- Principle IV (Fail-Fast): Validates on startup
- Principle II (Modular Architecture): Clear separation of concerns
- Principle III (Code Clarity): Well-documented initialization
"""

from flask import Flask, render_template, send_from_directory, Response, request
from flask_cors import CORS
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import atexit
import os
from pathlib import Path

from .config import load_config
from .logging_config import setup_logging
from .routes import health_bp, datasets_bp
from .routes.private import private_bp
from .startup import validate_and_initialize
from .errors import format_error_response
from .services.container_manager import CellxgeneContainerManager
from .models.access_grant import AccessGrantStore
from .models.shareable_link import ShareableLinkStore
from .services.email_service import EmailService, EmailConfig, MockEmailService


def create_app(config=None, testing=False):
    """
    Flask application factory.

    Args:
        config: Optional configuration override
        testing: If True, skip initialization and background tasks

    Returns:
        Configured Flask application
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config["TESTING"] = testing

    # Load configuration
    if testing and config is None:
        # Create a minimal test configuration
        from .config import ServiceConfig
        import tempfile
        from pathlib import Path

        # Use temp directories for testing
        temp_dir = Path(tempfile.gettempdir()) / "cellxgene_test"
        temp_dir.mkdir(exist_ok=True)

        service_config = ServiceConfig(
            data_directory=temp_dir / "datasets",
            log_directory=temp_dir / "logs",
            debug=True,
            log_level="DEBUG",
            host="127.0.0.1",
            port=8000,
            cellxgene_url="http://localhost:5005",
            enable_hot_reload=False,
            hot_reload_interval_seconds=300,
        )
        service_config.data_directory.mkdir(exist_ok=True)
        service_config.log_directory.mkdir(exist_ok=True)
    elif config is None:
        service_config = load_config()
    else:
        service_config = config

    # Setup logging
    logger = setup_logging(
        "cellxgene-landing-page",
        service_config.log_level,
        service_config.log_directory / "landing-page.log",
        enable_console=True,
    )

    # Skip initialization in testing mode
    if testing:
        logger.info("Running in testing mode - skipping initialization")
        # Create empty catalog for tests
        from .services.catalog import DatasetCatalog

        catalog = DatasetCatalog(datasets=[], logger=logger)
        container_manager = None
    else:
        # Run startup validation
        logger.info("Initializing application...")
        service_config, catalog = validate_and_initialize(logger)

        # Initialize container manager for dynamic CellXGene instances
        # Pass both container path and host path for volume mounting
        import os

        host_data_dir = os.environ.get(
            "HOST_DATA_DIRECTORY", str(service_config.data_directory)
        )
        logger.info(
            f"Using host data directory for container spawning: {host_data_dir}"
        )

        memory_gb = int(os.environ.get("CELLXGENE_MEMORY_PER_WORKER_GB", "4"))
        container_manager = CellxgeneContainerManager(
            data_directory=str(service_config.data_directory),
            network_name="cellxgene_stack_cellxgene-network",
            host_data_directory=host_data_dir,
            memory_gb=memory_gb,
        )
        logger.info("Container manager initialized")

        # Initialize background scheduler for container cleanup
        scheduler = BackgroundScheduler(daemon=True)
        # Run cleanup every 5 minutes, remove containers inactive for 48 hours (172800 seconds)
        scheduler.add_job(
            func=lambda: container_manager.cleanup_inactive(
                max_inactive_seconds=172800
            ),
            trigger="interval",
            minutes=5,
            id="cleanup_inactive_containers",
            name="Cleanup inactive CellXGene containers",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            "Background scheduler started - checking for inactive containers every 5 minutes (48 hour timeout)"
        )

        # Ensure scheduler shuts down when app terminates
        atexit.register(lambda: scheduler.shutdown())

    # Store configuration in app
    app.config["SERVICE_CONFIG"] = service_config
    app.config["CATALOG"] = catalog
    app.config["CONTAINER_MANAGER"] = container_manager
    app.config["CELLXGENE_URL"] = service_config.cellxgene_url
    app.config["DEBUG"] = service_config.debug
    
    # Set secret key for sessions
    import secrets
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    
    # Initialize private access components
    if not testing:
        # Access grant store
        grant_store = AccessGrantStore(service_config.grants_storage_path)
        app.config["GRANT_STORE"] = grant_store
        logger.info(f"Access grant store initialized: {service_config.grants_storage_path}")
        
        # Shareable link store (same directory as grants)
        links_storage_path = service_config.grants_storage_path.parent / "shareable_links.json"
        link_store = ShareableLinkStore(links_storage_path)
        app.config["LINK_STORE"] = link_store
        logger.info(f"Shareable link store initialized: {links_storage_path}")
        
        # Admin token for grant management
        app.config["ADMIN_TOKEN"] = service_config.admin_token
        
        # Private catalog (if configured)
        if service_config.private_data_directory and service_config.private_data_directory.exists():
            from .services.scanner import DatasetScanner
            from .services.catalog import DatasetCatalog
            
            private_scanner = DatasetScanner(service_config.private_data_directory, logger)
            private_datasets, _ = private_scanner.scan(fail_on_invalid=False)
            private_catalog = DatasetCatalog(private_datasets, logger)
            app.config["PRIVATE_CATALOG"] = private_catalog
            logger.info(f"Private catalog initialized with {len(private_datasets)} datasets")
            
            # Create container manager for private datasets
            host_private_dir = os.environ.get(
                "HOST_PRIVATE_DATA_DIRECTORY", str(service_config.private_data_directory)
            )
            private_container_manager = CellxgeneContainerManager(
                data_directory=str(service_config.private_data_directory),
                network_name="cellxgene_stack_cellxgene-network",
                host_data_directory=host_private_dir,
                memory_gb=memory_gb,
            )
            app.config["PRIVATE_CONTAINER_MANAGER"] = private_container_manager
            logger.info(f"Private container manager initialized for: {host_private_dir}")
        else:
            app.config["PRIVATE_CATALOG"] = None
            app.config["PRIVATE_CONTAINER_MANAGER"] = None
            if service_config.private_data_directory:
                logger.warning(f"Private data directory not found: {service_config.private_data_directory}")
        
        # Email service
        if service_config.smtp_host:
            email_config = EmailConfig(
                smtp_host=service_config.smtp_host,
                smtp_port=service_config.smtp_port,
                smtp_username=service_config.smtp_username or "",
                smtp_password=service_config.smtp_password or "",
                from_email=service_config.smtp_from_email or "noreply@earlham.ac.uk",
                base_url=service_config.base_url,
            )
            email_service = EmailService(email_config, logger)
            app.config["EMAIL_SERVICE"] = email_service
            logger.info("Email service initialized")
        else:
            # Use mock service for development
            app.config["EMAIL_SERVICE"] = MockEmailService(logger)
            logger.warning("Using mock email service (SMTP not configured)")

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(datasets_bp, url_prefix="/api")
    app.register_blueprint(private_bp, url_prefix="/api/private")

    # Landing page route
    @app.route("/")
    def index():
        """Serve the landing page."""
        return render_template("index.html")
    
    # Private access page route
    @app.route("/private")
    def private_access():
        """Serve the private dataset access page."""
        return render_template("private.html")
    
    # Admin page route
    @app.route("/admin")
    def admin_panel():
        """Serve the admin panel page."""
        return render_template("admin.html")

    # Static file serving
    @app.route("/static/<path:filename>")
    def serve_static(filename):
        """Serve static files."""
        return send_from_directory(app.static_folder, filename)

    # CellXGene proxy route - proxies to dynamically spawned containers
    @app.route("/cellxgene-<dataset_id>/", defaults={"path": ""})
    @app.route("/cellxgene-<dataset_id>/<path:path>")
    def proxy_cellxgene(dataset_id, path):
        """Proxy requests to CellXGene containers."""
        # Find the container port
        container_manager = app.config.get("CONTAINER_MANAGER")
        private_container_manager = app.config.get("PRIVATE_CONTAINER_MANAGER")
        
        port = None
        
        # Check public container manager
        if container_manager:
            port = container_manager.get_container_port(dataset_id)
        
        # Check private container manager if not found
        if port is None and private_container_manager:
            port = private_container_manager.get_container_port(dataset_id)
        
        if port is None:
            return {"error": "Container not running", "dataset_id": dataset_id}, 503
        
        # Proxy the request - use container name instead of localhost
        # Containers are named cellxgene-{dataset_id} and expose port 5005 internally
        container_name = f"cellxgene-{dataset_id}"
        target_url = f"http://{container_name}:5005/{path}"
        if request.query_string:
            target_url += f"?{request.query_string.decode()}"
        
        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers={key: value for (key, value) in request.headers if key != 'Host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                timeout=30,
            )
            
            # Build response
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items()
                       if name.lower() not in excluded_headers]
            
            return Response(resp.content, resp.status_code, headers)
        except requests.exceptions.RequestException as e:
            logger.error(f"Proxy error for {dataset_id}: {e}")
            return {"error": "Container unavailable"}, 503

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return {
            "error_type": "NotFound",
            "message": "The requested resource was not found",
            "recovery_hint": "Check the URL and try again",
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
    config = app.config["SERVICE_CONFIG"]

    app.run(host=config.host, port=config.port, debug=config.debug)


if __name__ == "__main__":
    main()
