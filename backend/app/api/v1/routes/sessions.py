"""
Compatibility wrapper.

Routes moved to `app.features.sessions.api`.
"""

from app.features.sessions.api import router

__all__ = ["router"]
