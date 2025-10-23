
import typing

from bot.lib.models.openapi import openapi

@openapi.component("TacoWebhookGamePayload", description="Represents the payload for a Taco webhook game event.")
@openapi.property("game_id", description="The unique identifier for the game.")
@openapi.property("end_date", description="The end date of the game.")
@openapi.property("worth", description="The worth of the game.")
@openapi.property("open_giveaway_url", description="The URL to open the giveaway.")
@openapi.property("title", description="The title of the game.")
@openapi.property("thumbnail", description="The thumbnail image URL of the game.")
@openapi.property("image", description="The main image URL of the game.")
@openapi.property("description", description="The description of the game.")
@openapi.property("instructions", description="The instructions for the game.")
@openapi.property("published_date", description="The published date of the game.")
@openapi.property("type", description="The type of the game.")
@openapi.property("platforms", description="The platforms the game is available on.")
@openapi.property("formatted_published_date", description="The formatted published date of the game.")
@openapi.property("formatted_end_date", description="The formatted end date of the game.")
@openapi.managed()
class TacoWebhookGamePayload:
    """Represents the payload for a Taco webhook game event."""

    def __init__(self, data: dict):
        self.game_id: str = data.get("game_id", "")
        self.end_date: typing.Optional[int] = data.get("end_date", None)
        self.worth: typing.Optional[str] = data.get("worth", None)
        self.open_giveaway_url: str = data.get("open_giveaway_url", "")
        self.title: str = data.get("title", "")
        self.thumbnail: str = data.get("thumbnail", "")
        self.image: str = data.get("image", "")
        self.description: str = data.get("description", "")
        self.instructions: typing.Optional[str] = data.get("instructions", None)
        self.published_date: int = data.get("published_date", 0)
        self.type: str = data.get("type", "")
        self.platforms: list[str] = data.get("platforms", [])
        self.formatted_published_date: typing.Optional[str] = data.get("formatted_published_date", None)
        self.formatted_end_date: typing.Optional[str] = data.get("formatted_end_date", None)

    def to_dict(self) -> dict:
        return self.__dict__
