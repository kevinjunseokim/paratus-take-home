import enum


class UploadStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PersonnelType(str, enum.Enum):
    ENLISTED = "enlisted"
    OFFICER = "officer"


class IssueSeverity(str, enum.Enum):
    ERROR = "error"
    WARNING = "warning"
