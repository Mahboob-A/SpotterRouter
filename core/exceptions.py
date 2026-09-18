"""Project exception hierarchy for expected domain failures."""


class FuelRouterError(Exception):
    """Base class for handled fuel router errors."""


class RoutingUnavailableError(FuelRouterError):
    """Raised when the routing provider cannot return a usable route."""


class GeocodingUnresolvedError(FuelRouterError):
    """Raised when an input cannot be resolved to an in-scope location."""


class InsufficientStationCoverageError(FuelRouterError):
    """Raised when available stations cannot support the route."""
