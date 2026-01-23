"""
Logging Infrastructure for CellXGene Explorer

Provides structured JSON logging with consistent format across all services.

Constitutional Alignment:
- Principle III (Code Clarity): Structured, searchable logs
- Principle IV (Fail-Fast): Log errors with full context
- Principle I (Unit Testing): Designed for testability
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import traceback


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Each log entry is a single-line JSON object for easy parsing by log aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON string representing the log entry
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_console: bool = True,
) -> logging.Logger:
    """
    Set up logging for a service with consistent configuration.

    Args:
        service_name: Name of the service (e.g., 'landing-page', 'cellxgene')
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file for JSON output
        enable_console: Whether to enable console logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # JSON formatter for file output
    json_formatter = JSONFormatter()

    # Console handler (human-readable for development)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))

        # Use simple format for console
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler (JSON for parsing)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)

    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log a message with additional context fields.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields to include in JSON log
    """
    log_method = getattr(logger, level.lower())

    # Create a log record with extra fields
    extra = {"extra_fields": context}
    log_method(message, extra=extra)


# Example usage helpers
def log_request(
    logger: logging.Logger, method: str, path: str, status_code: int, duration_ms: float
):
    """Log an HTTP request."""
    log_with_context(
        logger,
        "info",
        f"{method} {path} - {status_code}",
        request_method=method,
        request_path=path,
        response_status=status_code,
        duration_ms=duration_ms,
    )


def log_error(logger: logging.Logger, error: Exception, context: Optional[Dict] = None):
    """Log an error with full traceback and context."""
    context = context or {}
    log_with_context(
        logger, "error", str(error), error_type=type(error).__name__, **context
    )
    logger.exception(error)


def log_startup(logger: logging.Logger, service_name: str, version: str, config: Dict):
    """Log service startup with configuration."""
    log_with_context(
        logger,
        "info",
        f"{service_name} starting",
        service=service_name,
        version=version,
        config=config,
    )


def log_validation_failure(logger: logging.Logger, item: str, errors: list):
    """Log validation failures."""
    log_with_context(
        logger, "error", f"Validation failed for {item}", item=item, errors=errors
    )
