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
import typing


class DiscordGuild:
    def __init__(self, data: dict):
        self.id: str = data.get("id", "0")
        self.name: str = data.get("name", "Unknown Guild")
        self.member_count: int = data.get("member_count", 0)
        self.icon: typing.Optional[str] = data.get("icon", None)
        self.banner: typing.Optional[str] = data.get("banner", None)
        self.owner_id: typing.Optional[str] = data.get("owner_id", None)
        self.features: typing.Optional[list] = data.get("features", None)
        self.description: typing.Optional[str] = data.get("description", None)
        self.vanity_url: typing.Optional[str] = data.get("vanity_url", None)
        self.vanity_url_code: typing.Optional[str] = data.get("vanity_url_code", None)
        self.preferred_locale: typing.Optional[str] = data.get("preferred_locale", None)
        self.verification_level: typing.Optional[str] = data.get("verification_level", None)
        self.boost_level: typing.Optional[str] = data.get("boost_level", None)
        self.boost_count: int = data.get("boost_count", 0)

    def to_dict(self) -> dict:
        return self.__dict__
