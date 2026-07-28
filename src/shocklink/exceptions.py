"""Public exception hierarchy for ShockLink."""


class ShockLinkError(Exception):
    """Base class for expected ShockLink failures."""


class ConfigurationError(ShockLinkError):
    """Raised when an analysis configuration is missing or invalid."""


class DatasetError(ShockLinkError):
    """Raised when simulation data cannot be read or interpreted."""


class GeometryError(ShockLinkError):
    """Raised when field-line or surface geometry is invalid."""


class BackendUnavailableError(ShockLinkError):
    """Raised when an optional analysis backend is unavailable."""
