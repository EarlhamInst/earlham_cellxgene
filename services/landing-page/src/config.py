"""
Configuration Management Module

Loads and validates environment variables for the application.

Constitutional Alignment:
- Principle IV (Fail-Fast): Validates configuration on startup
- Principle III (Code Clarity): Clear configuration with defaults
- Principle V (Documentation): Well-documented configuration options
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


@dataclass
class ServiceConfig:
    """
    Application configuration loaded from environment variables.

    All configuration is loaded from environment variables with sensible defaults.
    Missing required values will cause a ConfigurationError on startup (fail-fast).
    """

    # Data paths
    data_directory: Path
    log_directory: Path

    # Service configuration
    debug: bool
    log_level: str
    host: str
    port: int

    # CellXGene service
    cellxgene_url: str

    # Optional features
    enable_hot_reload: bool
    hot_reload_interval_seconds: int
    
    # Private datasets
    private_data_directory: Optional[Path] = None
    grants_storage_path: Optional[Path] = None
    admin_token: Optional[str] = None
    
    # Email configuration (optional)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    
    # Base URL for links in emails
    base_url: str = "http://localhost:8000"
    
    # SQLite database
    database_path: Optional[Path] = None
    
    # ORCID OAuth (optional, for user uploads)
    orcid_client_id: Optional[str] = None
    orcid_client_secret: Optional[str] = None
    orcid_redirect_uri: Optional[str] = None
    orcid_sandbox: bool = True
    
    # Flask session secret (required for sessions)
    flask_secret_key: Optional[str] = None

    @classmethod
    def from_environment(cls) -> "ServiceConfig":
        """
        Load configuration from environment variables.

        Returns:
            ServiceConfig instance with loaded values

        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        # Required: Data directory
        data_dir_str = os.getenv("DATA_DIRECTORY")
        if not data_dir_str:
            raise ConfigurationError(
                "DATA_DIRECTORY environment variable is required. "
                "Set it in your .env file or docker-compose.yml"
            )
        data_directory = Path(data_dir_str)

        if not data_directory.exists():
            raise ConfigurationError(
                f"Data directory does not exist: {data_directory}. "
                f"Create it with: mkdir -p {data_directory}"
            )

        # Required: Log directory
        log_dir_str = os.getenv("LOG_DIRECTORY", "/data/logs")
        log_directory = Path(log_dir_str)

        # Create log directory if it doesn't exist
        log_directory.mkdir(parents=True, exist_ok=True)

        # Optional: Debug mode
        debug = os.getenv("DEBUG", "false").lower() == "true"

        # Optional: Log level
        log_level = os.getenv("LOG_LEVEL", "DEBUG" if debug else "INFO").upper()
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_log_levels:
            raise ConfigurationError(
                f"Invalid LOG_LEVEL: {log_level}. Must be one of {valid_log_levels}"
            )

        # Optional: Service binding
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))

        # Optional: CellXGene service URL
        cellxgene_url = os.getenv("CELLXGENE_URL", "http://cellxgene:5005")

        # Optional: Hot reload
        enable_hot_reload = os.getenv("ENABLE_HOT_RELOAD", "false").lower() == "true"
        hot_reload_interval = int(os.getenv("HOT_RELOAD_INTERVAL_SECONDS", "60"))
        
        # Optional: Private datasets
        private_data_dir_str = os.getenv("PRIVATE_DATA_DIRECTORY")
        private_data_directory = Path(private_data_dir_str) if private_data_dir_str else None
        
        grants_storage_str = os.getenv("GRANTS_STORAGE_PATH")
        grants_storage_path = Path(grants_storage_str) if grants_storage_str else log_directory / "access_grants.json"
        
        admin_token = os.getenv("ADMIN_TOKEN")
        
        # Optional: Email configuration
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from_email = os.getenv("SMTP_FROM_EMAIL")
        
        # Base URL for links in emails
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        
        # SQLite database path
        database_path_str = os.getenv("DATABASE_PATH")
        database_path = Path(database_path_str) if database_path_str else data_directory / "cellxgene.db"
        
        # ORCID OAuth configuration
        orcid_client_id = os.getenv("ORCID_CLIENT_ID")
        orcid_client_secret = os.getenv("ORCID_CLIENT_SECRET")
        orcid_redirect_uri = os.getenv("ORCID_REDIRECT_URI")
        orcid_sandbox = os.getenv("ORCID_SANDBOX", "true").lower() == "true"
        
        # Flask session secret key
        flask_secret_key = os.getenv("FLASK_SECRET_KEY")

        return cls(
            data_directory=data_directory,
            log_directory=log_directory,
            debug=debug,
            log_level=log_level,
            host=host,
            port=port,
            cellxgene_url=cellxgene_url,
            enable_hot_reload=enable_hot_reload,
            hot_reload_interval_seconds=hot_reload_interval,
            private_data_directory=private_data_directory,
            grants_storage_path=grants_storage_path,
            admin_token=admin_token,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_from_email=smtp_from_email,
            base_url=base_url,
            database_path=database_path,
            orcid_client_id=orcid_client_id,
            orcid_client_secret=orcid_client_secret,
            orcid_redirect_uri=orcid_redirect_uri,
            orcid_sandbox=orcid_sandbox,
            flask_secret_key=flask_secret_key,
        )

    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary for logging.

        Returns:
            Dictionary representation (safe for logging, no secrets)
        """
        return {
            "data_directory": str(self.data_directory),
            "log_directory": str(self.log_directory),
            "debug": self.debug,
            "log_level": self.log_level,
            "host": self.host,
            "port": self.port,
            "cellxgene_url": self.cellxgene_url,
            "enable_hot_reload": self.enable_hot_reload,
            "hot_reload_interval_seconds": self.hot_reload_interval_seconds,
        }

    def validate(self) -> None:
        """
        Validate configuration values.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate data directory is readable
        if not os.access(self.data_directory, os.R_OK):
            raise ConfigurationError(
                f"Data directory is not readable: {self.data_directory}"
            )

        # Validate log directory is writable
        if not os.access(self.log_directory, os.W_OK):
            raise ConfigurationError(
                f"Log directory is not writable: {self.log_directory}"
            )

        # Validate port range
        if not (1 <= self.port <= 65535):
            raise ConfigurationError(
                f"Invalid port number: {self.port}. Must be between 1 and 65535"
            )


def load_config() -> ServiceConfig:
    """
    Load and validate configuration.

    This is the main entry point for loading configuration.
    It will fail fast if configuration is invalid.

    Returns:
        Validated ServiceConfig instance

    Raises:
        ConfigurationError: If configuration is invalid or missing
    """
    config = ServiceConfig.from_environment()
    config.validate()
    return config
