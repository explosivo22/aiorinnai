"""Define package errors."""


class RinnaiError(Exception):
    """Base exception for all Rinnai errors."""


class RequestError(RinnaiError):
    """Exception raised for HTTP/connection failures during API requests."""


class CloudError(RinnaiError):
    """Base exception for AWS Cognito and cloud-related errors."""


class Unauthenticated(CloudError):
    """Raised when authentication credentials are invalid or missing."""


class UserNotFound(CloudError):
    """Raised when the specified user account does not exist."""


class UserExists(CloudError):
    """Raised when attempting to create a user that already exists."""


class UserNotConfirmed(CloudError):
    """Raised when a user has not confirmed their email address."""


class PasswordChangeRequired(CloudError):
    """Raised when a password change is required before authentication.

    Args:
        message: Optional custom message. Defaults to "Password change required."
    """

    def __init__(self, message: str = "Password change required.") -> None:
        """Initialize a password change required error."""
        super().__init__(message)


class UnknownError(CloudError):
    """Raised when an unrecognized AWS error occurs."""


# Mapping of AWS Cognito error codes to exception classes
AWS_EXCEPTIONS: dict[str, type[CloudError]] = {
    "UserNotFoundException": UserNotFound,
    "UserNotConfirmedException": UserNotConfirmed,
    "UsernameExistsException": UserExists,
    "NotAuthorizedException": Unauthenticated,
    "PasswordResetRequiredException": PasswordChangeRequired,
}