class AgriVerdeException(Exception):
    """Base exception for AgriVerde."""
    pass

class DeviceNotFoundError(AgriVerdeException):
    pass

class InvalidTelemetryError(AgriVerdeException):
    pass

class UnauthorizedError(AgriVerdeException):
    pass