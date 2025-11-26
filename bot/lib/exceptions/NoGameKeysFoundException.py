
class NoGameKeysFoundException(Exception):
    """Exception raised when no game keys are found."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
