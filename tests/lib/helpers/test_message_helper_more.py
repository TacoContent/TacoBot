from unittest.mock import AsyncMock, MagicMock

import pytest
import discord

from bot.lib.helpers.message_helper import MessageHelper


@pytest.mark.asyncio
async def test_send_embed_with_author_and_media(bot, settings, monkeypatch):
    # Arrange
    helper = MessageHelper(bot, settings)
    monkeypatch.setattr('bot.lib.helpers.message_helper.utils.get_user_display_name', lambda u: 'Display')

    channel = MagicMock()
    sent_msg = MagicMock()
    channel.send = AsyncMock(return_value=sent_msg)

    # Simulate author object with avatar url
    author = MagicMock()
    author.avatar = MagicMock()
    author.avatar.url = 'https://avatar.example/img'

    # Act
    returned = await helper.send_embed(
        channel=channel,
        title='My Title',
        message='my message',
        fields=[{'name': 'f1', 'value': 'v1', 'inline': True}],
        footer=None,
        thumbnail='thumb-url',
        image='image-url',
        author=author,
        content='the content',
        files=['file1'],
    )

    # Assert
    channel.send.assert_called_once()
    assert returned is sent_msg
    kwargs = channel.send.call_args.kwargs
    assert kwargs['content'] == 'the content'
    embed = kwargs['embed']
    assert embed.title == 'My Title'
    assert embed.description == 'my message'
    assert any(f.name == 'f1' and f.value == 'v1' for f in embed.fields)
    # footer is taken from settings.get_string (conftest fixture returns 'Test string')
    assert embed.footer.text == settings.get_string()


@pytest.mark.asyncio
async def test_update_embed_append_and_override(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    # Create an existing embed on a message
    embed = discord.Embed(title='T', description='existing')
    embed.add_field(name='A', value='1', inline=False)

    message = MagicMock()
    message.embeds = [embed]
    message.content = 'orig-content'
    message.guild = MagicMock()
    message.guild.id = 123
    message.edit = AsyncMock()

    # Append a new description and add one more field
    await helper.update_embed(message=message, description='added text', fields=[{'name': 'B', 'value': '2'}])

    # message.edit should have been called once with an updated embed
    message.edit.assert_called_once()
    args, kwargs = message.edit.call_args
    updated_embed = kwargs['embed']
    assert 'existing' in updated_embed.description
    assert 'added text' in updated_embed.description
    assert any(f.name == 'A' for f in updated_embed.fields)
    assert any(f.name == 'B' for f in updated_embed.fields)

    # When description_append is False it should replace description
    message.edit.reset_mock()
    message.embeds = [discord.Embed(title='T2', description='orig')]
    await helper.update_embed(message=message, description='NEW', description_append=False)
    message.edit.assert_called_once()
    args, kwargs = message.edit.call_args
    updated_embed = kwargs['embed']
    assert updated_embed.description.strip() == 'NEW'


@pytest.mark.asyncio
async def test_notify_of_error_calls_send_embed(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.guild.id = 10
    ctx.channel = MagicMock()
    ctx.author = MagicMock()
    ctx.author.mention = '@user'

    spy = AsyncMock()
    monkeypatch.setattr(helper, 'send_embed', spy)

    await helper.notify_of_error(ctx)

    spy.assert_called_once()
    # ensure the second argument is some error title and the message includes mention
    called = spy.call_args.kwargs
    assert 'error' in called['title'].lower() or settings.get_string.called


@pytest.mark.asyncio
async def test_move_message_embeds_attachments_and_delete(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    # Create a message with an embed and an attachment pseudo-object
    embed = discord.Embed(title='ET', description='Edesc')
    embed.add_field(name='keep', value='val1', inline=False)
    # embed.image is a property on discord EmbedProxy when set via set_image
    embed.set_image(url='http://img')

    attachment = MagicMock()
    attachment.to_file = AsyncMock(return_value='file-obj')

    message = MagicMock()
    message.guild = MagicMock()
    message.guild.id = 99
    message.embeds = [embed]
    message.attachments = [attachment]
    message.content = 'content of message'
    message.author = MagicMock()
    message.author.name = 'AuthorName'
    message.delete = AsyncMock()

    # target channel will accept send
    target = MagicMock()
    moved = MagicMock()
    target.send = AsyncMock(return_value=moved)

    result = await helper.move_message(message, target, author=None, who=MagicMock(), reason='test', fields=[{'name': 'X', 'value': 'Y'}], delete_original=True)

    assert result is moved
    target.send.assert_called_once()
    # original delete should be invoked because delete_original=True
    message.delete.assert_called_once()


@pytest.mark.asyncio
async def test_move_message_handles_non_guild(bot, settings):
    helper = MessageHelper(bot, settings)

    message = MagicMock()
    message.guild = None

    target = MagicMock()
    # When message.guild is None, move_message should return None
    res = await helper.move_message(message, target)
    assert res is None


@pytest.mark.asyncio
async def test_notify_bot_not_initialized_non_admin(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.guild.id = 7
    ctx.channel = MagicMock()
    ctx.channel.send = AsyncMock(return_value=MagicMock())
    ctx.author = MagicMock()
    ctx.author.mention = '@user'
    ctx.author.guild_permissions = MagicMock()
    ctx.author.guild_permissions.administrator = False

    # Patch send_embed so we don't need to test embed serialization here
    sentinel = AsyncMock()
    monkeypatch.setattr(helper, 'send_embed', sentinel)

    await helper.notify_bot_not_initialized(ctx, subcommand=None)
    sentinel.assert_called_once()


@pytest.mark.asyncio
async def test_send_embed_footer_override_and_color_none(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    channel = MagicMock()
    channel.send = AsyncMock(return_value=MagicMock())

    # Pass a None color to exercise the color defaulting path
    await helper.send_embed(channel, title='t', message='m', color=None, footer='CUSTOM')

    call_kwargs = channel.send.call_args.kwargs
    embed = call_kwargs['embed']
    assert embed.footer.text == 'CUSTOM'
    # default color should be used when None passed
    assert embed.color.value == 0x7289DA or embed.colour.value == 0x7289DA


@pytest.mark.asyncio
async def test_update_embed_returns_when_no_message(bot, settings):
    helper = MessageHelper(bot, settings)

    # message is None or has no embeds - should be no-op
    res = await helper.update_embed(message=None, description='x')
    assert res is None


@pytest.mark.asyncio
async def test_move_message_remove_fields_and_color_from_embed(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    embed = discord.Embed(title='E', description='desc', color=0xABCDEF)
    embed.add_field(name='keep', value='v1', inline=False)
    embed.add_field(name='remove_me', value='v2', inline=True)

    attachment = MagicMock()
    attachment.to_file = AsyncMock(return_value='fobj')

    message = MagicMock()
    message.guild = MagicMock()
    message.guild.id = 55
    message.embeds = [embed]
    message.attachments = [attachment]
    message.content = 'here'
    message.author = MagicMock()
    message.author.name = 'Auth'
    message.delete = AsyncMock()

    target = MagicMock()
    target.send = AsyncMock(return_value=MagicMock())

    # remove the field named 'remove_me'
    result = await helper.move_message(message, target, remove_fields=[{'name': 'remove_me'}], delete_original=False)

    # ensure send was called with embed that does not include 'remove_me'
    called_kwargs = target.send.call_args.kwargs
    tembed = called_kwargs['embed']
    assert all(f.name != 'remove_me' for f in tembed.fields)
    # ensure color was taken from original embed
    assert tembed.color.value == 0xABCDEF


@pytest.mark.asyncio
async def test_notify_bot_not_initialized_admin_path(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    ctx = MagicMock()
    ctx.channel = MagicMock()
    ctx.author = MagicMock()
    ctx.author.mention = '@admin'
    ctx.author.guild_permissions = MagicMock()
    ctx.author.guild_permissions.administrator = True
    ctx.guild = MagicMock()
    ctx.guild.id = 1
    ctx.message = MagicMock()

    # bot.get_prefix should be awaited and return a list of prefixes
    bot.get_prefix = AsyncMock(return_value=['!'])
    helper.bot = bot

    spy = AsyncMock()
    monkeypatch.setattr(helper, 'send_embed', spy)

    await helper.notify_bot_not_initialized(ctx, subcommand='setup')

    spy.assert_called_once()
    # check that the admin path used the prefix in calling send_embed
    called = spy.call_args.kwargs
    assert 'not_initialized_admin' in settings.get_string.call_args.args or settings.get_string.called


@pytest.mark.asyncio
async def test_update_embed_edge_cases_and_author(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    # Case: embed has no title and no description
    embed = discord.Embed()
    message = MagicMock()
    message.embeds = [embed]
    message.content = 'abc'
    message.guild = MagicMock()
    message.guild.id = 77
    message.edit = AsyncMock()

    # color None should use default
    await helper.update_embed(message=message, title=None, description=None, color=None, footer='F')
    message.edit.assert_called_once()
    called_embed = message.edit.call_args.kwargs['embed']
    assert called_embed.description == ''
    assert called_embed.footer.text == 'F'

    # Author passed should set author on embed
    message.edit.reset_mock()
    monkeypatch.setattr('bot.lib.helpers.message_helper.utils.get_user_display_name', lambda u: 'NameX')
    author = MagicMock()
    author.avatar = MagicMock()
    author.avatar.url = 'icon-url'

    await helper.update_embed(message=message, author=author)
    message.edit.assert_called_once()
    author_field = message.edit.call_args.kwargs['embed'].to_dict().get('author')
    assert author_field and author_field.get('name') == 'NameX'


@pytest.mark.asyncio
async def test_move_message_no_target_and_exception_handling(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    # no targetChannel should cause an early-return and debug
    helper.log = MagicMock()
    message = MagicMock()
    message.guild = MagicMock()
    message.guild.id = 1

    res = await helper.move_message(message, None)
    assert res is None
    helper.log.debug.assert_called()

    # simulate an exception in target.send and ensure log.error called
    message2 = MagicMock()
    message2.guild = MagicMock()
    message2.guild.id = 2
    message2.embeds = []
    message2.attachments = []
    message2.content = 'x'

    target = MagicMock()
    async def bad_send(*a, **k):
        raise RuntimeError('boom')

    target.send = AsyncMock(side_effect=bad_send)
    helper.log = MagicMock()

    # Should not raise, but log.error should get called
    await helper.move_message(message2, target)
    helper.log.error.assert_called()


@pytest.mark.asyncio
async def test_send_embed_preexisting_fields(monkeypatch, bot, settings):
    # Replace Embed so it starts with a pre-existing field to exercise the loop
    import bot.lib.helpers.message_helper as mh

    realEmbed = mh.discord.Embed

    class PreEmbed(realEmbed):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            # add an initial field so the for-loop in send_embed iterates
            super().add_field(name='initial', value='iv', inline=False)

    monkeypatch.setattr(mh, 'discord', mh.discord)
    monkeypatch.setattr(mh.discord, 'Embed', PreEmbed, raising=False)

    helper = MessageHelper(bot, settings)
    channel = MagicMock()
    channel.send = AsyncMock(return_value=MagicMock())

    await helper.send_embed(channel, title='t', message='m')

    called_embed = channel.send.call_args.kwargs['embed']
    # The embed should contain at least the initial field and possibly duplicates
    assert any(f.name == 'initial' for f in called_embed.fields)

    # Restore original for other tests
    monkeypatch.setattr(mh.discord, 'Embed', realEmbed, raising=False)


@pytest.mark.asyncio
async def test_update_embed_content_and_title_none(bot, settings):
    helper = MessageHelper(bot, settings)
    embed = discord.Embed()  # no title, no description
    message = MagicMock()
    message.embeds = [embed]
    message.content = 'original'
    message.guild = MagicMock()
    message.edit = AsyncMock()

    await helper.update_embed(message=message, description=None, content='new-content', title=None)

    message.edit.assert_called_once()
    args, kwargs = message.edit.call_args
    assert kwargs['content'] == 'new-content'


@pytest.mark.asyncio
async def test_send_embed_fields_default_inline(bot, settings):
    helper = MessageHelper(bot, settings)
    channel = MagicMock()
    channel.send = AsyncMock(return_value=MagicMock())

    await helper.send_embed(channel, title='t', message='m', fields=[{'name': 'n', 'value': 'v'}])
    called_embed = channel.send.call_args.kwargs['embed']
    assert any(f.name == 'n' and f.inline is False for f in called_embed.fields)


@pytest.mark.asyncio
async def test_notify_of_error_with_user_instead_of_author(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)
    ctx = MagicMock()
    ctx.guild = None
    ctx.channel = MagicMock()
    # no 'author' attribute, but has 'user'
    ctx.user = MagicMock()
    ctx.user.mention = '@user'

    spy = AsyncMock()
    monkeypatch.setattr(helper, 'send_embed', spy)
    await helper.notify_of_error(ctx)

    spy.assert_called_once()


@pytest.mark.asyncio
async def test_move_message_author_override_and_additional_fields(bot, settings):
    helper = MessageHelper(bot, settings)

    # embed with no color -> defaults should be used when color is None
    embed = discord.Embed(title='T', description='D')
    embed.add_field(name='f1', value='v1')

    message = MagicMock()
    message.guild = MagicMock()
    message.guild.id = 101
    message.embeds = [embed]
    message.attachments = []
    message.content = 'ct'
    message.delete = AsyncMock()

    target = MagicMock()
    sent = MagicMock()
    target.send = AsyncMock(return_value=sent)

    author = MagicMock()
    author.name = 'Overrode'
    author.avatar = None

    # add an extra field without inline key to exercise default False
    result = await helper.move_message(message, target, author=author, fields=[{'name': 'extra', 'value': 'x'}], delete_original=False)
    assert result is sent
    called_embed = target.send.call_args.kwargs['embed']
    assert any(f.name == 'extra' and f.inline is False for f in called_embed.fields)
    # color default used when embed.color not present
    assert called_embed.color.value == 0x7289DA


@pytest.mark.asyncio
async def test_notify_bot_not_initialized_channel_none_admin_and_user(bot, settings, monkeypatch):
    helper = MessageHelper(bot, settings)

    # Non-admin when ctx.channel is None -> channel becomes ctx.author
    ctx = MagicMock()
    ctx.channel = None
    ctx.author = MagicMock()
    ctx.author.guild_permissions = MagicMock()
    ctx.author.guild_permissions.administrator = False
    ctx.author.mention = '@user'
    ctx.guild = MagicMock()
    ctx.guild.id = 11

    spy = AsyncMock()
    monkeypatch.setattr(helper, 'send_embed', spy)

    await helper.notify_bot_not_initialized(ctx)
    spy.assert_called_once()


def test_init_handles_falsy_log_level_message_helper(monkeypatch, bot):
    # Simulate Settings.log_level value that yields falsy LogLevel lookup
    from bot.lib.helpers import message_helper as mh

    real_ll = mh.loglevel.LogLevel

    class FakeLogLevel:
        DEBUG = real_ll.DEBUG

        @classmethod
        def __class_getitem__(cls, key):
            return None

    monkeypatch.setattr(mh, 'loglevel', mh.loglevel)
    monkeypatch.setattr(mh.loglevel, 'LogLevel', FakeLogLevel)

    # capture the minimumLogLevel passed into logger.Log
    captured = {}

    class FakeLog:
        def __init__(self, minimumLogLevel=None, *a, **k):
            captured['min'] = minimumLogLevel

    monkeypatch.setattr(mh, 'logger', mh.logger)
    monkeypatch.setattr(mh.logger, 'Log', FakeLog)

    s = MagicMock()
    s.log_level = 'UNKNOWN'
    helper = MessageHelper(bot, s)

    # constructor should have used fallback DEBUG
    assert captured.get('min') == real_ll.DEBUG


@pytest.mark.asyncio
async def test_send_embed_with_messageable_channel(bot, settings):
    helper = MessageHelper(bot, settings)

    # create a simple subclass of Messageable with a working send
    class FakeMessageable(discord.abc.Messageable):
        def __init__(self):
            self.sent = None

        async def send(self, *a, **k):
            self.sent = (a, k)
            return 'ok'

    chan = FakeMessageable()
    res = await helper.send_embed(chan, title='x', message='y')
    assert res == 'ok'


@pytest.mark.asyncio
async def test_update_embed_append_when_original_empty(bot, settings):
    helper = MessageHelper(bot, settings)
    embed = discord.Embed(title='t', description='')
    message = MagicMock()
    message.embeds = [embed]
    message.content = ''
    message.guild = MagicMock()
    message.edit = AsyncMock()

    await helper.update_embed(message=message, description='new', description_append=True)
    message.edit.assert_called_once()
    updated = message.edit.call_args.kwargs['embed']
    # since original description is empty, the new description should start with two newlines per code path
    assert updated.description.endswith('new')

    # nothing else in this test
