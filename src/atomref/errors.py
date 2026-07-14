"""Catchable exceptions raised by `atomref` submodules."""


class AtomrefError(Exception):
    """Base class for package-defined operational errors.

    Notes:
        The exception classes are documented from `atomref.errors` but are not
        re-exported from the top-level `atomref` namespace.
    """


class DatasetError(AtomrefError):
    """Report an unavailable, unknown, or malformed dataset.

    Examples:
        Catch this exception when a user-selected dataset identifier may be
        unavailable:

        >>> from atomref.errors import DatasetError
        >>> try:
        ...     raise DatasetError("unknown dataset")
        ... except DatasetError:
        ...     pass
    """


class MissingValueError(AtomrefError):
    """Report that an operation requires an unavailable reference value.

    Notes:
        Ordinary lookup functions generally represent missing scientific data
        with `None` or a missing [LookupResult][atomref.LookupResult] rather than
        raising this exception.
    """


class PolicyError(AtomrefError):
    """Report invalid policy configuration or transfer resolution.

    Examples:
        This includes incompatible radii kinds, invalid transfer controls, and
        cyclic nested policies. Callers that accept user-authored policies can
        catch `PolicyError` to distinguish those failures from missing values.
    """
