class MinecraftWhitelistUser:
    def __init__(self, *args, **kwargs):
        # set properties from kwargs
        self.user_id = kwargs.get("user_id", 0)
        self.guild_id = kwargs.get("guild_id", 0)
        self.username = kwargs.get("username", "")
        self.uuid = kwargs.get("uuid", "")
        self.whitelist = kwargs.get("whitelist", False)

        self.op = kwargs.get("op", None)

    