"""Backward-compatible re-export; route implementations live in ``app.domains.auth.router``."""

from app.domains.auth.router import router

__all__ = ["router"]
