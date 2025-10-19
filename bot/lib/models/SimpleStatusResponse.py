from lib.models.openapi import openapi


@openapi.component("SimpleStatusResponse", description="Simple status response with a status string")
@openapi.managed()
class SimpleStatusResponse:
    def __init__(self, status: str):
        self.status = status

    def to_dict(self) -> dict:
        return {"status": self.status}
