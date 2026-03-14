class AtomrefError(Exception):
    """Base package error."""


class DatasetError(AtomrefError):
    """Packaged dataset or registry error."""


class MissingValueError(AtomrefError):
    """Raised when a required reference value is unavailable."""


class PolicyError(AtomrefError):
    """Raised for invalid policy configuration."""
