import discord
import discordhealthcheck

class TacoBotClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        self.healthcheck_server = await discordhealthcheck.start(self)
        # Later you can close or check on self.healthcheck_server
