from __future__ import annotations

from typing import Any, Dict, Optional


class OnceOnlyError(Exception):
    """Base exception class for OnceOnly SDK."""


class UnauthorizedError(OnceOnlyError):
    """401/403 Invalid or disabled API key."""


class OverLimitError(OnceOnlyError):
    """402 Free plan limit reached."""

    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.detail = detail or {}


class RateLimitError(OnceOnlyError):
    """429 Rate limit exceeded."""


class ValidationError(OnceOnlyError):
    """422 validation error."""


class ApiError(OnceOnlyError):
    """Non-2xx API errors (except those mapped to typed errors)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or {}
