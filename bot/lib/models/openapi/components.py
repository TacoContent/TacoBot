
import typing
AttrT = typing.TypeVar("AttrT")


def component(
    name: typing.Optional[str] = None, description: typing.Optional[str] = None
) -> typing.Callable[[type], type]:
    def _wrap(cls: type) -> type:
        setattr(cls, '__openapi_component__', name or cls.__name__)
        if description:
            setattr(cls, '__openapi_description__', description)
        return cls
    return _wrap

def property(
    property: str, name: str, value: typing.Optional[typing.Union[str, bool, int, float]]
) -> typing.Callable[[AttrT], AttrT]:
    def _wrap(attr: AttrT) -> AttrT:
        target = typing.cast(typing.Any, attr)
        if not hasattr(target, '__openapi_properties__'):
            setattr(target, '__openapi_properties__', {})
        if property not in target.__openapi_properties__:
            target.__openapi_properties__[property] = {}
        target.__openapi_properties__[property][name] = value
        return attr
    return _wrap


__all__ = [
    'component',
    'property'
]
