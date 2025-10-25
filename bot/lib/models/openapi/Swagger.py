

import typing


AuthenticationTypes: typing.TypeAlias = typing.Literal["http", "apiKey", "oauth2", "openIdConnect"]
AuthenticationSchemes: typing.TypeAlias = typing.Literal["basic"]
ApiKeyLocations: typing.TypeAlias = typing.Literal["header", "query", "cookie"]
SwaggerParameterLocation: typing.TypeAlias = typing.Literal["query", "header", "path", "cookie"]
SwaggerPathParameterStyles: typing.TypeAlias = typing.Literal["label", "matrix", "simple"]
SwaggerQueryParameterStyles: typing.TypeAlias = typing.Literal["form", "spaceDelimited", "pipeDelimited", "deepObject"]
SwaggerHeaderParameterStyles: typing.TypeAlias = typing.Literal["simple"]
SwaggerCookieParameterStyles: typing.TypeAlias = typing.Literal["form"]


class Swagger:

    def __init__(self, data: typing.Dict[str, typing.Any]):

        self.openapi: str = data.get("openapi", "3.0.4")

        self.securitySchemes: typing.Dict[str, Authentication] = {}
        for key, value in data.get("securitySchemes", {}).items():
            self.securitySchemes[key] = Authentication(value)

        self.info: SwaggerInfo = SwaggerInfo(data.get("info", {}))
        self.servers: typing.List[SwaggerServer] = [SwaggerServer(server) for server in data.get("servers", [])]


class SwaggerInfo:

    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.title: str = data.get("title", "")
        self.description: str = data.get("description", "")
        self.version: str = data.get("version", "")


class SwaggerServer:

    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.url: str = data.get("url", "")
        self.description: str = data.get("description", "")


class SwaggerParameter:

    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.name: str = data.get("name", "")
        self.in_: SwaggerParameterLocation = data.get("in", "")
        if self.in_ not in SwaggerParameterLocation.__args__:
            raise ValueError("Invalid 'in' value for SwaggerParameter")
        self.description: typing.Optional[str] = data.get("description", None)
        self.required: typing.Optional[bool] = data.get("required", False)
        self.schema: typing.Dict[str, typing.Any] = data.get("schema", {})
        self.example: typing.Any = data.get("example", None)
        self.explode: typing.Optional[bool] = data.get("explode", False)


class SwaggerPathParameter(SwaggerParameter):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.in_ != "path":
            raise ValueError("Path parameters must have 'in' set to 'path'")
        self.required = True  # Path parameters are always required

        self.style: SwaggerPathParameterStyles = data.get("style", "simple")
        if self.style not in SwaggerPathParameterStyles.__args__:
            raise ValueError("Invalid 'style' value for Path Parameter")


class SwaggerQueryParameter(SwaggerParameter):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.in_ != "query":
            raise ValueError("Query parameters must have 'in' set to 'query'")

        self.allowReserved: typing.Optional[bool] = data.get("allowReserved", False)
        self.style: SwaggerQueryParameterStyles = data.get("style", "form")
        if self.style not in SwaggerQueryParameterStyles.__args__:
            raise ValueError("Invalid 'style' value for Query Parameter")


class SwaggerHeaderParameter(SwaggerParameter):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.in_ != "header":
            raise ValueError("Header parameters must have 'in' set to 'header'")

        self.style: SwaggerHeaderParameterStyles = data.get("style", "simple")
        if self.style != SwaggerHeaderParameterStyles:
            raise ValueError("Invalid 'style' value for Header Parameter")


class SwaggerCookieParameter(SwaggerParameter):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.in_ != "cookie":
            raise ValueError("Cookie parameters must have 'in' set to 'cookie'")

        self.style: SwaggerCookieParameterStyles = data.get("style", "form")
        if self.style != SwaggerCookieParameterStyles:
            raise ValueError("Invalid 'style' value for Cookie Parameter")


class Authentication:

    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.type: AuthenticationTypes = data.get("type", "http")


class BasicAuthentication(Authentication):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.type != "http":
            raise ValueError("Invalid authentication type for BasicAuthentication")
        self.scheme: AuthenticationSchemes = data.get("scheme", "basic")
        if self.scheme != "basic":
            raise ValueError("Invalid authentication scheme for BasicAuthentication")


class ApiKeyAuthentication(Authentication):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.type != "apiKey":
            raise ValueError("Invalid authentication type for ApiKeyAuthentication")
        self.name: str = data.get("name", "")
        self.in_: ApiKeyLocations = data.get("in", "header")
        if self.in_ not in ApiKeyLocations.__args__:
            raise ValueError("Invalid 'in' value for ApiKeyAuthentication")


class BearerAuthentication(Authentication):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.type != "http":
            raise ValueError("Invalid authentication type for BearerAuthentication")
        self.scheme: AuthenticationSchemes = data.get("scheme", "bearer")
        if self.scheme != "bearer":
            raise ValueError("Invalid authentication scheme for BearerAuthentication")
        self.bearerFormat: typing.Optional[str] = data.get("bearerFormat", None)


class CookieAuthentication(Authentication):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.type != "apiKey":
            raise ValueError("Invalid authentication type for CookieAuthentication")
        self.in_: ApiKeyLocations = data.get("in", "cookie")
        if self.in_ != "cookie":
            raise ValueError("Invalid 'in' value for CookieAuthentication")

        self.name: str = data.get("name", "")
        if not self.name:
            raise ValueError("name is required for CookieAuthentication")


class OpenIDConnectDiscoveryAuthentication(Authentication):
    """OpenID Connect Discovery Authentication

    see: https://swagger.io/docs/specification/v3_0/authentication/openid-connect-discovery/
    """

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.type != "openIdConnect":
            raise ValueError("Invalid authentication type for OpenIDConnectDiscoveryAuthentication")
        self.openIdConnectUrl: str = data.get("openIdConnectUrl", "")
        if not self.openIdConnectUrl:
            raise ValueError("openIdConnectUrl is required for OpenIDConnectDiscoveryAuthentication")

        self.scopes: typing.Optional[typing.List[str]] = data.get("scopes", [])


class OAuth2Authentication(Authentication):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if self.type != "oauth2":
            raise ValueError("Invalid authentication type for OAuth2Authentication")
        self.flows: OAuth2Flows = OAuth2Flows(data.get("flows", {}))


class OAuth2Flows:

    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.authorizationCode: typing.Optional[OAuth2Flow] = OAuth2Flow(data.get("authorizationCode", {}))
        self.clientCredentials: typing.Optional[OAuth2ClientCredentialsFlow] = OAuth2ClientCredentialsFlow(
            data.get("clientCredentials", {})
        )
        self.implicit: typing.Optional[OAuth2ImplicitFlow] = OAuth2ImplicitFlow(data.get("implicit", {}))
        self.password: typing.Optional[OAuth2PasswordFlow] = OAuth2PasswordFlow(data.get("password", {}))


class OAuth2Flow:

    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.authorizationUrl: typing.Optional[str] = data.get("authorizationUrl", None)
        self.tokenUrl: typing.Optional[str] = data.get("tokenUrl", None)
        self.refreshUrl: typing.Optional[str] = data.get("refreshUrl", None)
        self.scopes: typing.Dict[str, str] = data.get("scopes", {})


class OAuth2ImplicitFlow(OAuth2Flow):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if not self.authorizationUrl:
            raise ValueError("authorizationUrl is required for Implicit Flow")

        self.tokenUrl = None  # Implicit flow does not use tokenUrl
        self.refreshUrl = None  # Implicit flow does not use refreshUrl


class OAuth2PasswordFlow(OAuth2Flow):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if not self.tokenUrl:
            raise ValueError("tokenUrl is required for Password Flow")

        self.authorizationUrl = None  # Password flow does not use authorizationUrl


class OAuth2ClientCredentialsFlow(OAuth2Flow):

    def __init__(self, data: typing.Dict[str, typing.Any]):
        super().__init__(data)
        if not self.tokenUrl:
            raise ValueError("tokenUrl is required for Client Credentials Flow")

        self.authorizationUrl = None  # Client Credentials flow does not use authorizationUrl
