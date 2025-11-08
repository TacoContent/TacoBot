import inspect
import os
import traceback
import typing

import httpx
from bot.lib import logger
from bot.lib.enums import loglevel
from openai import OpenAI


class OpenAIHelper:
    """
    Helper class to wrap OpenAI client with configurable settings.

    Settings are loaded from the 'openai' section of cog settings and can include:
    - endpoint: Base URL for OpenAI API (default: uses OpenAI's default)
    - token: API key for authentication (default: from OPENAI_API_KEY env var)
    - model: Default model to use (default: "gpt-3.5-turbo")
    - max_tokens: Maximum tokens for completion (optional)
    - temperature: Temperature for completion (optional)
    - timeout: Request timeout in seconds (default: 60)
    - insecure: Disable SSL certificate verification (default: false, WARNING: use only for development/testing)

    Example settings in MongoDB:
    {
        "guild_id": "123456789",
        "name": "openai",
        "settings": {
            "endpoint": "https://api.openai.com/v1",
            "token": "sk-...",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
            "timeout": 30,
            "insecure": false
        }
    }

    WARNING: Setting 'insecure' to true disables SSL certificate verification.
    This should ONLY be used in development/testing environments with self-signed
    certificates. Never use this in production as it makes connections vulnerable
    to man-in-the-middle attacks.
    """

    def __init__(
        self,
        settings: typing.Optional[dict] = None,
        endpoint: typing.Optional[str] = None,
        token: typing.Optional[str] = None,
        model: typing.Optional[str] = None,
    ):
        """
        Initialize OpenAI helper with optional settings override.

        Args:
            settings: Dictionary of OpenAI settings from cog configuration
            endpoint: Override endpoint URL
            token: Override API token
            model: Override default model
        """
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

        log_level_str = os.getenv('LOG_LEVEL', 'DEBUG')
        log_level = loglevel.LogLevel[log_level_str.upper()]
        self.log = logger.Log(minimumLogLevel=log_level)

        # Load settings with fallbacks
        self.settings = settings or {}

        # Configure endpoint (base_url in OpenAI client)
        self._endpoint = endpoint or self.settings.get("endpoint") or os.getenv("OPENAI_ENDPOINT")

        # Configure token with fallback to environment variable
        self._token = token or self.settings.get("token") or os.getenv("OPENAI_API_KEY")

        # Configure default model
        self.default_model = model or self.settings.get("model", "gpt-3.5-turbo") or os.getenv("OPENAI_MODEL")

        # Configure optional parameters
        self.default_temperature = self.settings.get("temperature")
        self.default_max_tokens = self.settings.get("max_tokens")
        self.timeout = self.settings.get("timeout", 60)
        self.insecure = self.settings.get("insecure", False)

        # Initialize the OpenAI client
        self._client = self._create_client()

    def _create_client(self) -> OpenAI:
        """Create and configure the OpenAI client."""
        _method = inspect.stack()[0][3]
        try:
            client_kwargs = {"api_key": self._token, "timeout": self.timeout}

            # Only add base_url if endpoint is specified
            if self._endpoint:
                client_kwargs["base_url"] = self._endpoint

            # Configure SSL verification if insecure mode is enabled
            if self.insecure:
                # Create a custom HTTP client that disables SSL verification
                http_client = httpx.Client(verify=False)
                client_kwargs["http_client"] = http_client
                self.log.warn(
                    0,
                    f"{self._module}.{self._class}.{_method}",
                    "SSL certificate verification is disabled (insecure mode enabled)",
                )

            return OpenAI(**client_kwargs)
        except Exception as ex:
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Failed to create OpenAI client: {ex}",
                traceback.format_exc(),
            )
            raise

    @property
    def client(self) -> OpenAI:
        """Get the underlying OpenAI client."""
        return self._client

    def chat_completion(
        self,
        messages: list[dict],
        model: typing.Optional[str] = None,
        temperature: typing.Optional[float] = None,
        max_tokens: typing.Optional[int] = None,
        **kwargs,
    ) -> typing.Any:
        """
        Create a chat completion using the configured OpenAI client.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to configured default model)
            temperature: Temperature for sampling (defaults to configured default)
            max_tokens: Maximum tokens to generate (defaults to configured default)
            **kwargs: Additional arguments to pass to OpenAI API

        Returns:
            OpenAI ChatCompletion response object
        """
        _method = inspect.stack()[0][3]
        try:
            # Use provided values or fall back to defaults
            completion_kwargs = {"model": model or self.default_model, "messages": messages, **kwargs}

            # Add optional parameters only if they're set
            if temperature is not None or self.default_temperature is not None:
                completion_kwargs["temperature"] = temperature if temperature is not None else self.default_temperature

            if max_tokens is not None or self.default_max_tokens is not None:
                completion_kwargs["max_tokens"] = max_tokens if max_tokens is not None else self.default_max_tokens

            return self._client.chat.completions.create(**completion_kwargs)
        except Exception as ex:
            self.log.error(
                0, f"{self._module}.{self._class}.{_method}", f"Chat completion failed: {ex}", traceback.format_exc()
            )
            raise

    def get_response_text(self, completion: typing.Any) -> typing.Optional[str]:
        """
        Extract the text content from a chat completion response.

        Args:
            completion: OpenAI ChatCompletion response object

        Returns:
            The text content of the first choice, or None if unavailable
        """
        _method = inspect.stack()[0][3]
        try:
            if completion and completion.choices and len(completion.choices) > 0:
                return completion.choices[0].message.content
            return None
        except Exception as ex:
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Failed to extract response text: {ex}",
                traceback.format_exc(),
            )
            return None

    def update_settings(self, settings: dict) -> None:
        """
        Update the helper's settings and recreate the client if necessary.

        Args:
            settings: New settings dictionary
        """
        _method = inspect.stack()[0][3]
        try:
            # Check if critical settings changed
            new_endpoint = settings.get("endpoint")
            new_token = settings.get("token")

            needs_recreate = (new_endpoint and new_endpoint != self._endpoint) or (
                new_token and new_token != self._token
            )

            # Update settings
            self.settings = settings
            self._endpoint = new_endpoint or self._endpoint
            self._token = new_token or self._token
            self.default_model = settings.get("model", self.default_model)
            self.default_temperature = settings.get("temperature", self.default_temperature)
            self.default_max_tokens = settings.get("max_tokens", self.default_max_tokens)
            self.timeout = settings.get("timeout", self.timeout)
            self.insecure = settings.get("insecure", False)

            # Recreate client if needed
            if needs_recreate:
                self._client = self._create_client()
        except Exception as ex:
            self.log.error(
                0, f"{self._module}.{self._class}.{_method}", f"Failed to update settings: {ex}", traceback.format_exc()
            )
            raise
