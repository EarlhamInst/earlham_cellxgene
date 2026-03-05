"""
Startup Validation

Validates datasets and configuration on application startup.

Constitutional Alignment:
- Principle IV (Fail-Fast): Fail immediately if any dataset is invalid
- Principle VI (Accessibility): Clear error messages with recovery steps
"""

import sys
import logging
from pathlib import Path

from .config import load_config, ConfigurationError
from .services.scanner import DatasetScanner
from .services.catalog import DatasetCatalog
from .services.database import init_database, DatabaseError
from .models.dataset import DatasetStoreSQLite
from .errors import ValidationError


def validate_and_initialize(logger: logging.Logger) -> tuple:
    """
    Validate configuration and datasets on startup.

    This function implements fail-fast validation:
    - Load and validate configuration
    - Initialize SQLite database
    - Scan and validate all datasets
    - Sync datasets to database
    - Fail immediately if anything is wrong

    Args:
        logger: Logger instance

    Returns:
        Tuple of (config, catalog, database)

    Raises:
        SystemExit: If validation fails (exits with code 1)
    """
    logger.info("=" * 60)
    logger.info("Starting CellXGene Explorer Landing Page")
    logger.info("=" * 60)

    # Step 1: Load and validate configuration
    logger.info("Step 1: Loading configuration...")
    try:
        config = load_config()
        logger.info("✓ Configuration loaded successfully")
        logger.info(f"  Data directory: {config.data_directory}")
        logger.info(f"  Log directory: {config.log_directory}")
        logger.info(f"  Database path: {config.database_path}")
        logger.info(f"  Debug mode: {config.debug}")
        logger.info(f"  Log level: {config.log_level}")
    except ConfigurationError as e:
        logger.error(f"✗ Configuration validation failed: {e.message}")
        if e.recovery_hint:
            logger.error(f"  Recovery hint: {e.recovery_hint}")
        sys.exit(1)

    # Step 2: Initialize SQLite database
    logger.info("Step 2: Initializing database...")
    try:
        database = init_database(config.database_path, logger)
        stats = database.get_stats()
        logger.info("✓ Database initialized successfully")
        logger.info(f"  Users: {stats.get('users', 0)}")
        logger.info(f"  Datasets: {stats.get('datasets', 0)}")
        logger.info(f"  Access grants: {stats.get('access_grants', 0)}")
        logger.info(f"  Shareable links: {stats.get('shareable_links', 0)}")
    except DatabaseError as e:
        logger.error(f"✗ Database initialization failed: {e}")
        sys.exit(1)

    # Step 3: Scan and validate datasets from filesystem
    logger.info("Step 3: Scanning datasets...")
    scanner = DatasetScanner(config.data_directory, logger)

    try:
        valid_datasets, invalid_datasets = scanner.scan(fail_on_invalid=True)
        logger.info(f"✓ Found {len(valid_datasets)} valid datasets on filesystem")

        for dataset in valid_datasets:
            logger.info(f"  - {dataset.id}: {dataset.display_name}")

    except ValidationError as e:
        logger.error(f"✗ Dataset validation failed: {e.message}")
        if e.recovery_hint:
            logger.error(f"  Recovery hint: {e.recovery_hint}")
        logger.error("")
        logger.error("Fix the errors above and restart the service.")
        logger.error(
            "Run 'python scripts/validate-datasets.py' for detailed validation."
        )
        sys.exit(1)

    # Step 4: Sync curated datasets to database
    logger.info("Step 4: Syncing datasets to database...")
    dataset_store = DatasetStoreSQLite(database)
    sync_stats = dataset_store.sync_curated_datasets(valid_datasets)
    logger.info(f"✓ Database sync complete")
    logger.info(f"  Added: {sync_stats['added']}")
    logger.info(f"  Updated: {sync_stats['updated']}")
    logger.info(f"  Removed: {sync_stats['removed']}")

    # Step 5: Create dataset catalog (from database for consistency)
    logger.info("Step 5: Creating dataset catalog...")
    # Get all public datasets from database (includes curated + user-uploaded public)
    all_public = dataset_store.get_public()
    catalog = DatasetCatalog(all_public, logger)
    logger.info(f"✓ Catalog initialized with {len(catalog)} public datasets")

    # Step 6: Display catalog statistics
    stats = catalog.get_statistics()
    logger.info("Step 6: Catalog statistics:")
    logger.info(f"  Total public datasets: {stats['total_datasets']}")
    logger.info(f"  Total cells: {stats['total_cells']:,}")
    logger.info(f"  Unique organisms: {stats['unique_organisms']}")
    logger.info(f"  Unique tissues: {stats['unique_tissues']}")
    logger.info(f"  Unique assays: {stats['unique_assays']}")

    logger.info("=" * 60)
    logger.info("✓ Startup validation complete - all checks passed")
    logger.info("=" * 60)

    return config, catalog, database


def validate_on_startup_decorator(app_factory):
    """
    Decorator to add startup validation to Flask app factory.

    Args:
        app_factory: Flask app factory function

    Returns:
        Wrapped app factory with validation
    """

    def wrapper(*args, **kwargs):
        app = app_factory(*args, **kwargs)

        # Run validation
        logger = logging.getLogger("cellxgene-landing-page")
        config, catalog, database = validate_and_initialize(logger)

        # Store in app config
        app.config["SERVICE_CONFIG"] = config
        app.config["CATALOG"] = catalog
        app.config["DATABASE"] = database
        app.config["CELLXGENE_URL"] = config.cellxgene_url

        return app

    return wrapper
