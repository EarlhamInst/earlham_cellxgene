"""Package initialization for routes."""
from .health import health_bp
from .datasets import datasets_bp

__all__ = ['health_bp', 'datasets_bp']
