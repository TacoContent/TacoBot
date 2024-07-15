from aiohttp import web
import json
import asyncio
from bot.cogs.lib.messaging import Messaging

class WebhookListener:
    def __init__(self, bot):
        self.bot = bot
        self.messaging = Messaging(bot)
        return

    def start(self):
        print(f"Starting webhook listener: -> :8090")
        self.webhook_listener = web.Application()
        self.webhook_listener.router.add_post("/webhook/game", self.game)
        web.run_app(self.webhook_listener, port=8090, handle_signals=True)

    async def game(self, request, *args, **kwargs):
        if int(request.headers.get("Content-Length", 0)) > 0:
            body = await request.json()
        else:
            body = ""
        print(body)
        return web.Response(body=json.dumps(body, indent=4), content_type="application/json")
