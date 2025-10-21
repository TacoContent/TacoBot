
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
    property: str,
    **kwargs: typing.Any
) -> typing.Callable[[AttrT], AttrT]:
    """Annotate an OpenAPI component property with schema attributes.

    Flexible usage patterns supported:
    - Keyword form:     @openapi.property("name", description="My desc", minimum=0)

    All provided attributes are merged into the component's
    "__openapi_properties__" mapping under the given property key.

    Args:
        property: The schema property name (e.g., "name", "count").
        name: Optional single attribute name (legacy usage), e.g., "description".
        value: Optional single attribute value (legacy usage).
        **kwargs: Arbitrary OpenAPI schema attributes for this property
                 (e.g., description, minimum, maximum, default, format, etc.).

    Returns:
        A decorator that records the provided attributes for the target component.
    """

    def _wrap(attr: AttrT) -> AttrT:
        target = typing.cast(typing.Any, attr)
        if not hasattr(target, '__openapi_properties__'):
            setattr(target, '__openapi_properties__', {})

        # Ensure a dict exists for this property name
        prop_map = target.__openapi_properties__.setdefault(property, {})

        # if 'hint' in kwargs:
        #     type_hint = kwargs.pop('hint', str)
        #     if isinstance(type_hint, type):
        #         type_hint_name = type_hint.__name__
        #     else:
        #         type_hint_name = str(type_hint)

            # prop_map['type'] = type_hint_name

        # Merge any additional keyword attributes
        if kwargs:
            # Let explicit kwargs override the legacy pair if duplicated
            # ignore `property` key since it is the identifier
            if 'property' in kwargs:
                del kwargs['property']
            if 'hint' in kwargs:
                del kwargs['hint']
            prop_map.update(kwargs)

        return attr

    return _wrap

__all__ = [
    'component',
    'property'
]
