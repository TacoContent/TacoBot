from bot.lib.models.TacoWebhookMinecraftTacosPayload import TacoWebhookMinecraftTacosPayload


def test_taco_webhook_minecraft_tacos_payload():
    t = TacoWebhookMinecraftTacosPayload({"guild_id": "g", "from_user": "u", "to_user_id": "t", "amount": 1, "reason": "r", "type": "custom"})
    assert t.to_user_id == "t"
