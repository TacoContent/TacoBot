import datetime
import json
import random
import re
import string
import typing

import discord
import requests


def human_time_duration(seconds: int) -> str:
    TIME_DURATION_UNITS = (
        ('year', 60 * 60 * 24 * 365),
        ('week', 60 * 60 * 24 * 7),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1),
    )
    if seconds == 0:
        return 'now'

    parts = []
    for unit, duration in TIME_DURATION_UNITS:
        amount, seconds = divmod(seconds, duration)
        if amount > 0:
            parts.append(f"{amount} {unit}{'s' if amount > 1 else ''}")
    return ', '.join(parts)


def dict_get(dictionary, key, default_value=None) -> typing.Any:
    if key in dictionary.keys():
        return dictionary[key] or default_value
    else:
        return default_value


def get_scalar_result(conn, sql, default_value=None, *args) -> typing.Any:
    cursor = conn.cursor()
    try:
        cursor.execute(sql, args)
        return cursor.fetchone()[0]
    except Exception:
        return default_value


def clean_channel_name(channel: str) -> str:
    return channel.lower().strip().replace("#", "").replace("@", "")


def str2bool(v) -> bool:
    return v.lower() in ("yes", "true", "yup", "1", "t", "y", "on")


def chunk_list(lst, size):
    # looping till length l
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def get_random_string(length: int = 10) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def get_random_name(noun_count=1, adjective_count=1) -> str:
    fallback_nouns = ["Aardvark", "Albatross", "Alligator", "Alpaca"]
    fallback_adjectives = ["Able", "Acidic", "Adorable", "Aggressive"]
    try:
        adjectives = load_from_gist("adjectives", adjective_count)
        nouns = load_from_gist("nouns", noun_count)
        results = adjectives + nouns
        return " ".join(w.title() for w in results)
    except Exception:
        try:
            nouns = requests.get(f"https://random-word-form.herokuapp.com/random/noun?count={str(noun_count)}").json()
            adjectives = requests.get(
                f"https://random-word-form.herokuapp.com/random/adjective?count={str(adjective_count)}"
            ).json()
            results = adjectives + nouns
            return " ".join(w.title() for w in results)
        except Exception:
            try:
                results = requests.get(
                    f"https://random-word-api.herokuapp.com/word?number={str(noun_count + adjective_count)}&swear=0"
                ).json()
                return " ".join(w.title() for w in results)
            except Exception:
                return " ".join(
                    random.sample(fallback_adjectives, adjective_count) + random.sample(fallback_nouns, noun_count)
                )


def get_user_display_name(user: typing.Union[discord.User, discord.Member]) -> str:
    """
    Gets the display name for the user.
    If the user has a discriminator of 0, then it will return the display name (new format).
    Otherwise it will return the display name and discriminator (old format)."""
    if user.discriminator == "0":
        return user.display_name
    else:
        return f"{user.display_name}#{user.discriminator}"


def to_timestamp(date, tz: typing.Optional[datetime.timezone] = None) -> float:
    date = date.replace(tzinfo=tz)
    return (date - datetime.datetime(1970, 1, 1, tzinfo=tz)).total_seconds()


def from_timestamp(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp)


def get_timestamp() -> float:
    # Get the current datetime in UTC and convert it to a timestamp
    return to_timestamp(datetime.datetime.now(datetime.timezone.utc))
    # return to_timestamp(datetime.datetime.now(datetime.UTC))


def get_seconds_until(end_ts: float) -> int:
    now = get_timestamp()
    return int(end_ts - now) if end_ts > now else 0


def load_from_gist(type, count) -> typing.List[str]:
    types = ["adjectives", "nouns", "verbs"]
    if type not in types:
        type = "nouns"
    if count <= 0:
        count = 1
    elif count > 10:
        count = 10
    data = requests.get(
        f"https://gist.githubusercontent.com/camalot/8d2af3796ac86083e873995eab98190d/raw/b39de3a6ba03205380caf5d58e0cae8a869ac36d/{type}.js"
    ).text
    data = re.sub(r"(var\s(adjectives|nouns|verbs)\s=\s)|;$", "", data)
    jdata = json.loads(data)
    return random.sample(jdata, count)


def get_args_dict(func, args, kwargs) -> dict:
    args_names = func.__code__.co_varnames[: func.__code__.co_argcount]
    return {**dict(zip(args_names, args)), **kwargs}


def str_replace(input_string: str, *args, **kwargs) -> str:
    xargs = get_args_dict(str_replace, args, kwargs)
    result = input_string
    for a in xargs:
        result = result.replace(f"{{{{{a}}}}}", str(kwargs[a]))
    return result


def isAdmin(ctx, settings) -> bool:
    is_in_guild_admin_role = False
    user = ctx.author if hasattr(ctx, "author") else ctx.user
    channel = ctx.channel if hasattr(ctx, "channel") else None
    # see if there are guild settings for admin role
    is_bot_owner = str(user.id) == settings.bot_owner
    has_admin = user.guild_permissions.administrator or (user.permission_in(channel).manage_guild if channel else False)
    return is_bot_owner or is_in_guild_admin_role or has_admin

    # is_bot_owner = str(ctx.author.id) == settings.bot_owner
    # has_admin = ctx.author.guild_permissions.administrator or ctx.author.permission_in(ctx.channel).manage_guild
    # return is_bot_owner or has_admin


def get_by_name_or_id(iterable, nameOrId: typing.Union[int, str]) -> typing.Optional[typing.Any]:
    if isinstance(nameOrId, str):
        return discord.utils.get(iterable, name=str(nameOrId))
    elif isinstance(nameOrId, int):
        return discord.utils.get(iterable, id=int(nameOrId))


def get_last_section_in_url(name) -> str:
    if "/" in name:
        # if the name has a slash in it, then it is a url. Remove everything before and including the slash
        name_split = name.rsplit("/", 1)
        if len(name_split) > 1:
            name = name_split[1]
    return name
