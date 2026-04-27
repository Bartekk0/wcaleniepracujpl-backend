class JobNotFoundError(Exception):
    """Raised when a job cannot be found during a moderation operation."""


class AlreadyModeratedError(Exception):
    """Raised when attempting to moderate a job that has already been moderated."""


class ReportNotFoundError(Exception):
    """Raised when a report cannot be found during a reports operation."""


class ReportAlreadyHandledError(Exception):
    """Raised when attempting to handle a report that is no longer open."""
