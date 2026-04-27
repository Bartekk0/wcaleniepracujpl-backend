from app.models.application import ApplicationStatus

ALLOWED_STATUS_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.SUBMITTED: {ApplicationStatus.REVIEWING},
    ApplicationStatus.REVIEWING: {ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED},
    ApplicationStatus.ACCEPTED: set(),
    ApplicationStatus.REJECTED: set(),
}
