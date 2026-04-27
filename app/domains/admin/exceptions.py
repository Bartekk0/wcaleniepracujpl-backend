class JobNotFoundError(Exception):
    """Raised when a job cannot be found during a moderation operation."""


class AlreadyModeratedError(Exception):
    """Raised when attempting to moderate a job that has already been moderated."""
