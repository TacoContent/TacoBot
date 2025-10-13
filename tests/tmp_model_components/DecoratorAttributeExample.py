from bot.lib.models.openapi import openapi_attribute, openapi_model


@openapi_model("DecoratorAttributeExample")
@openapi_attribute("custom-flag", "enabled")
class DecoratorAttributeExample:
    def __init__(self):
        self.primary = "value"
