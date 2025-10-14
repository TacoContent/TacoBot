import typing

from bot.lib.models.openapi import openapi

@openapi.component("ErrorStatusCodePayload", description="Represents an error status code payload.")
@openapi.openapi_managed()
class ErrorStatusCodePayload:
    """Model for error status code payloads.
    Represents an error message.

    >>>openapi
    properties:
      error:
        description: Description of the error.
      code:
        description: Error code.
    <<<openapi
    """
    def __init__(self, data: dict):
        self.error: str = data.get("error", "An unknown error occurred.")
        self.code: typing.Optional[int] = data.get("code", None)
