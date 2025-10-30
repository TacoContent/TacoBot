import typing

from bot.lib.models.openapi import openapi


@openapi.component("ErrorStatusCodePayload", description="Error status code payload")
@openapi.property("error", description="Description of the error")
@openapi.property("message", description="Error message")
@openapi.property("code", description="Error code")
@openapi.property("stacktrace", description="Stack trace of the error")
@openapi.managed()
class ErrorStatusCodePayload:
    """Model for error status code payloads.
    Represents an error message.
    """

    def __init__(self, data: dict):
        self.error: typing.Optional[str] = data.get("error", None)
        self.message: typing.Optional[str] = data.get("message", None)
        self.code: typing.Optional[int] = data.get("code", None)
        self.stacktrace: typing.Optional[str] = data.get("stacktrace", None)

        if self.message and not self.error:
            self.error = self.message

        if self.error and not self.message:
            self.message = self.error

        if not self.message and not self.error:
            raise ValueError("Either 'error' or 'message' must be provided.")

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        # this should return a dict suitable for dumping to YAML
        # it should __dict__ recursively
        # exclude None values
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}
