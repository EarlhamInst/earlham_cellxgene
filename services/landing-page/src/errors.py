"""
Error Handling Framework

Explicit exception types for clear error handling.

Constitutional Alignment:
- Principle IV (Fail-Fast): Explicit errors with clear messages
- Principle III (Code Clarity): Well-defined exception hierarchy
- Principle VI (Accessibility): User-friendly error messages with recovery steps
"""

from typing import Optional, List


class CellXGeneExplorerError(Exception):
    """
    Base exception for all CellXGene Explorer errors.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(self, message: str, recovery_hint: Optional[str] = None):
        """
        Initialize error with message and optional recovery hint.
        
        Args:
            message: Error message describing what went wrong
            recovery_hint: Optional hint about how to fix the error
        """
        self.message = message
        self.recovery_hint = recovery_hint
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert error to dictionary for JSON API responses."""
        result = {
            'error_type': self.__class__.__name__,
            'message': self.message
        }
        if self.recovery_hint:
            result['recovery_hint'] = self.recovery_hint
        return result


class DatasetNotFoundError(CellXGeneExplorerError):
    """
    Raised when a requested dataset cannot be found.
    
    Example:
        User requests a dataset by ID that doesn't exist in the catalog.
    """
    
    def __init__(self, dataset_id: str):
        message = f"Dataset not found: {dataset_id}"
        recovery_hint = (
            "Check that the dataset ID is correct and that the dataset exists "
            "in the data directory. Use the /api/datasets endpoint to list available datasets."
        )
        super().__init__(message, recovery_hint)
        self.dataset_id = dataset_id


class ValidationError(CellXGeneExplorerError):
    """
    Raised when data validation fails.
    
    Example:
        h5ad file is corrupted, embedded metadata is invalid, etc.
    """
    
    def __init__(self, item: str, errors: List[str]):
        message = f"Validation failed for {item}: {'; '.join(errors)}"
        recovery_hint = (
            "Fix the validation errors listed above. "
            "Run scripts/validate-datasets.py for detailed error information."
        )
        super().__init__(message, recovery_hint)
        self.item = item
        self.errors = errors


class ServiceUnavailableError(CellXGeneExplorerError):
    """
    Raised when a required service (e.g., CellXGene) is unavailable.
    
    Example:
        CellXGene service is not responding or is unhealthy.
    """
    
    def __init__(self, service_name: str, details: Optional[str] = None):
        message = f"Service unavailable: {service_name}"
        if details:
            message += f" - {details}"
        recovery_hint = (
            f"Check that the {service_name} service is running and healthy. "
            "Use 'docker compose ps' to check service status and 'docker compose logs' to view logs."
        )
        super().__init__(message, recovery_hint)
        self.service_name = service_name


class ConfigurationError(CellXGeneExplorerError):
    """
    Raised when configuration is invalid or missing.
    
    Example:
        Required environment variable is not set, invalid port number, etc.
    """
    
    def __init__(self, message: str, config_var: Optional[str] = None):
        recovery_hint = "Check your .env file and docker-compose.yml for correct configuration."
        if config_var:
            recovery_hint = f"Set the {config_var} environment variable. {recovery_hint}"
        super().__init__(message, recovery_hint)
        self.config_var = config_var


class MetadataValidationError(CellXGeneExplorerError):
    """
    Raised when dataset metadata fails validation.
    
    Example:
        Embedded metadata is missing required fields, has invalid values, etc.
    """
    
    def __init__(self, dataset_name: str, field: str, issue: str):
        message = f"Metadata validation failed for {dataset_name}: {field} - {issue}"
        recovery_hint = (
            f"Fix the '{field}' field in the h5ad file's embedded metadata (adata.uns). "
            "See docs/adding-datasets.md for metadata format requirements."
        )
        super().__init__(message, recovery_hint)
        self.dataset_name = dataset_name
        self.field = field
        self.issue = issue


class DatasetLaunchError(CellXGeneExplorerError):
    """
    Raised when launching CellXGene for a dataset fails.
    
    Example:
        Dataset file is locked, CellXGene fails to load the file, etc.
    """
    
    def __init__(self, dataset_id: str, reason: str):
        message = f"Failed to launch CellXGene for dataset {dataset_id}: {reason}"
        recovery_hint = (
            "Check the CellXGene service logs for details. "
            "Verify that the dataset file is not corrupted and is in valid h5ad format."
        )
        super().__init__(message, recovery_hint)
        self.dataset_id = dataset_id
        self.reason = reason


class FileAccessError(CellXGeneExplorerError):
    """
    Raised when file operations fail.
    
    Example:
        Cannot read h5ad file, cannot write logs, permission denied, etc.
    """
    
    def __init__(self, filepath: str, operation: str, reason: str):
        message = f"File access error during {operation} on {filepath}: {reason}"
        recovery_hint = (
            "Check file permissions and that the file exists. "
            "Verify that volume mounts are configured correctly in docker-compose.yml."
        )
        super().__init__(message, recovery_hint)
        self.filepath = filepath
        self.operation = operation


def format_error_response(error: Exception, status_code: int = 500) -> tuple:
    """
    Format an exception as an API error response.
    
    Args:
        error: The exception to format
        status_code: HTTP status code
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    if isinstance(error, CellXGeneExplorerError):
        return error.to_dict(), status_code
    else:
        # Generic error response for unexpected exceptions
        return {
            'error_type': 'InternalServerError',
            'message': 'An unexpected error occurred',
            'recovery_hint': 'Check the server logs for details'
        }, status_code
