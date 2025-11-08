"""
Exceptions for ComfyUI API Client.
"""


class ComfyUIClientError(Exception):
    """Base exception for ComfyUI client errors."""
    pass


class APIError(ComfyUIClientError):
    """API returned an error response."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class JobNotFoundError(ComfyUIClientError):
    """Job ID was not found."""
    pass


class JobFailedError(ComfyUIClientError):
    """Job failed to complete successfully."""

    def __init__(self, message: str, job_id: str = None, error_details: str = None):
        super().__init__(message)
        self.job_id = job_id
        self.error_details = error_details


class TimeoutError(ComfyUIClientError):
    """Job did not complete within the specified timeout."""

    def __init__(self, message: str, job_id: str = None, elapsed_time: float = None):
        super().__init__(message)
        self.job_id = job_id
        self.elapsed_time = elapsed_time


class ConnectionError(ComfyUIClientError):
    """Failed to connect to the API."""
    pass


class AuthenticationError(ComfyUIClientError):
    """Authentication failed (invalid API key)."""
    pass


class RateLimitError(ComfyUIClientError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after
