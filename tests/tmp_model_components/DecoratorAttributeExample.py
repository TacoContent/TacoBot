from bot.lib.models.openapi import openapi_attribute, component


@component("DecoratorAttributeExample")
@openapi_attribute("custom-flag", "enabled")
class DecoratorAttributeExample:
    def __init__(self):
        self.primary = "value"
