"""Custom exceptions for email notification workflows."""


class EmailNotificationError(Exception):
    """Base class for email notification errors."""


class EmailAuthenticationError(EmailNotificationError):
    """Raised when Microsoft Graph authentication fails."""


class EmailSendError(EmailNotificationError):
    """Raised when Microsoft Graph rejects or fails an email send request."""


class DuplicateEmailSkipped(EmailNotificationError):
    """Raised when idempotency protection prevents a duplicate email send."""
