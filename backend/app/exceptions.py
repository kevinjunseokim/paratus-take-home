class DomainError(Exception):
    pass


class AfscValidationError(DomainError):
    pass


class AfscResolutionError(DomainError):
    pass


class RosterImportError(DomainError):
    pass


class RosterNotFoundError(DomainError):
    pass
