
from bot.lib.models.openapi import openapi_model


@openapi_model("TacoMinecraftWorlds", description="Represents a Minecraft world managed by TacoBot.")
class TacoMinecraftWorlds():
    """Represents a Minecraft world managed by TacoBot.

    >>>openapi
    default: taco_atm10-2
    type: string
    enum:
      - taco_atm8
      - taco_atm9
      - taco_atm10
      - taco_atm10-2
    <<<openapi
    """

    taco_atm8: str = "taco_atm8"
    taco_atm9: str = "taco_atm9"
    taco_atm10: str = "taco_atm10"
    taco_atm10_2: str = "taco_atm10-2"
    default: str = "taco_atm10-2"

    def from_str(self, value: str) -> 'TacoMinecraftWorlds':
        """Create a TacoMinecraftWorlds instance from a string value."""
        if value in (self.taco_atm8, self.taco_atm9, self.taco_atm10, self.taco_atm10_2):
            return value
        return self.default
