# {
#     "id": str(guild.id),
#     "name": guild.name,
#     "member_count": guild.member_count,
#     "icon": guild.icon.url if guild.icon else None,
#     "banner": guild.banner.url if guild.banner else None,
#     "owner_id": str(guild.owner_id) if guild.owner_id else None,
#     "features": guild.features,
#     "description": guild.description,
#     "vanity_url": guild.vanity_url if guild.vanity_url else None,
#     "vanity_url_code": guild.vanity_url_code if guild.vanity_url_code else None,
#     "preferred_locale": guild.preferred_locale,
#     "verification_level": str(guild.verification_level.name),
#     "boost_level": str(guild.premium_tier),
#     "boost_count": guild.premium_subscription_count,
# }
class DiscordGuild:
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.name = data.get("name")
        self.member_count = data.get("member_count")
        self.icon = data.get("icon")
        self.banner = data.get("banner")
        self.owner_id = data.get("owner_id")
        self.features = data.get("features", [])
        self.description = data.get("description")
        self.vanity_url = data.get("vanity_url")
        self.vanity_url_code = data.get("vanity_url_code")
        self.preferred_locale = data.get("preferred_locale")
        self.verification_level = data.get("verification_level")
        self.boost_level = data.get("boost_level")
        self.boost_count = data.get("boost_count")

    def to_dict(self) -> dict:
        return self.__dict__
