
class ExistingOpenGameKeyOfferFoundException(Exception):
    """Exception raised when an existing open game key offer is found."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
