"""Package-local exceptions used across :mod:`atomref`."""


class AtomrefError(Exception):
    """Base class for package-defined errors."""


class DatasetError(AtomrefError):
    """Raised when packaged data or registry metadata are invalid."""


class MissingValueError(AtomrefError):
    """Raised when a required reference value is unavailable."""


class PolicyError(AtomrefError):
    """Raised for invalid policy configuration or transfer resolution."""
