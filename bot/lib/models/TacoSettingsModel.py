from typing import Any, Dict, Generic, TypeVar

from lib.models.openapi import openapi


T = TypeVar('T')

@openapi.component("TacoSettingsModel", description="Generic Taco Settings Model")
@openapi.property("guild_id", description="The ID of the guild.")
@openapi.property("name", description="The name of the settings.")
@openapi.property("metadata", description="Additional metadata for the settings.")
@openapi.property("settings", description="The specific settings data.", hint=Dict[str, Any])
class TacoSettingsModel(Generic[T]):

    def __init__(self, data: dict):
        self.guild_id: str = data.get("guild_id", "")
        self.name: str = data.get("name", "")
        self.metadata: Dict[str, Any] = data.get("metadata", {})
        self.settings: T = data.get("settings", None)  # type: ignore
