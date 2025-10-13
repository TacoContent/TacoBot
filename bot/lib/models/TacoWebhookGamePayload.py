
import typing

from bot.lib.models.openapi import openapi_managed, openapi_model


@openapi_model("TacoWebhookGamePayload", description="Represents the payload for a Taco webhook game event.")
@openapi_managed()
class TacoWebhookGamePayload:
    """Represents the payload for a Taco webhook game event.

    >>>openapi
    properties:
      game_id:
        description: The unique identifier for the game.
      end_date:
        description: The end date of the game.
      worth:
        description: The worth of the game.
      open_giveaway_url:
        description: The URL to open the giveaway.
      title:
        description: The title of the game.
      thumbnail:
        description: The thumbnail image URL of the game.
      image:
        description: The main image URL of the game.
      description:
        description: The description of the game.
      instructions:
        description: The instructions for the game.
      published_date:
        description: The published date of the game.
      type:
        description: The type of the game.
      platforms:
        description: The platforms the game is available on.
      formatted_published_date:
        description: The formatted published date of the game.
      formatted_end_date:
        description: The formatted end date of the game.
    <<<openapi
    """

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
