from bot.lib.helpers import ContextHelper


def test_create_empty_context():
    ctx = ContextHelper().create_context()
    # Should be a tuple-like object with no attributes
    assert isinstance(ctx, tuple)
    assert hasattr(ctx, "__iter__")


def test_create_context_with_fields():
    bot = object()
    user = object()
    guild = object()
    channel = object()

    ctx = ContextHelper().create_context(bot=bot, author=user, guild=guild, channel=channel, extra=123)

    assert hasattr(ctx, "bot")
    assert hasattr(ctx, "author")
    assert hasattr(ctx, "guild")
    assert hasattr(ctx, "channel")
    assert hasattr(ctx, "extra")

    assert getattr(ctx, "bot") is bot
    assert getattr(ctx, "author") is user
    assert getattr(ctx, "guild") is guild
    assert getattr(ctx, "channel") is channel
    assert getattr(ctx, "extra") == 123
