"""Component service entry point; the implementation lives in services/."""
from .services.profile_service import process_cv

__all__ = ['process_cv']
