from bot.lib.models.openapi import openapi


@openapi.component("DecoratorAttributeExample")
@openapi.attribute("custom-flag", "enabled")
class DecoratorAttributeExample:
    def __init__(self):
        self.primary = "value"
