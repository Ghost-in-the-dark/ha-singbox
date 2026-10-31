"""Exceptions shared by the sing-box backends and the config entry setup."""

from __future__ import annotations


class SingBoxError(Exception):
    """Base class for every error raised by the sing-box clients."""

    status: int = 0


class SingBoxAuthError(SingBoxError):
    """The sing-box API rejected the configured secret."""


class SingBoxNotSupported(SingBoxError):
    """The configured backend does not implement this operation."""
