# Owner: Dewmi - Component 04. Kept dependency-free so importing the router never loads C4 data.


class ModelsUnavailable(RuntimeError):
    """The trained model files are missing or cannot be loaded."""


class EvidenceError(ValueError):
    """Invalid proof submission; the message is shown to the student as-is."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code
