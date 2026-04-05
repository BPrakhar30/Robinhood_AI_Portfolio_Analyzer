class AppException(Exception):
    """Base exception for the application."""

    def __init__(self, message: str, status_code: int = 500, details: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class BrokerConnectionError(AppException):
    """Raised when a broker connection fails."""

    def __init__(self, message: str = "Broker connection failed", details: dict | None = None):
        super().__init__(message, status_code=502, details=details)


class BrokerTimeoutError(AppException):
    """Raised when a broker API call times out."""

    def __init__(self, message: str = "Broker API request timed out", details: dict | None = None):
        super().__init__(message, status_code=504, details=details)


class BrokerAuthenticationError(AppException):
    """Raised when broker authentication fails or token is expired.
    Uses 502 (Bad Gateway) since the failure is with the upstream broker, not with our auth."""

    def __init__(self, message: str = "Broker authentication failed", details: dict | None = None):
        super().__init__(message, status_code=502, details=details)


class BrokerRateLimitError(AppException):
    """Raised when broker API rate limit is exceeded."""

    def __init__(self, message: str = "Broker API rate limit exceeded", details: dict | None = None):
        super().__init__(message, status_code=429, details=details)


class PortfolioSyncError(AppException):
    """Raised when portfolio synchronization fails."""

    def __init__(self, message: str = "Portfolio sync failed", details: dict | None = None):
        super().__init__(message, status_code=500, details=details)


class CSVParseError(AppException):
    """Raised when CSV file parsing fails."""

    def __init__(self, message: str = "CSV parsing failed", details: dict | None = None):
        super().__init__(message, status_code=400, details=details)


class EncryptionError(AppException):
    """Raised when token encryption or decryption fails."""

    def __init__(self, message: str = "Encryption operation failed", details: dict | None = None):
        super().__init__(message, status_code=500, details=details)
