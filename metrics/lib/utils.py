import datetime
import typing


def dict_get(dictionary, key, default_value=None) -> typing.Any:
    if key in dictionary.keys():
        return dictionary[key] or default_value
    else:
        return default_value


def to_timestamp(date, tz: typing.Optional[datetime.timezone] = None) -> float:
    date = date.replace(tzinfo=tz)
    return (date - datetime.datetime(1970, 1, 1, tzinfo=tz)).total_seconds()


def from_timestamp(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp)


def get_timestamp() -> float:
    return to_timestamp(datetime.datetime.utcnow())
