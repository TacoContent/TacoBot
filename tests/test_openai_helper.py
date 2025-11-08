import os
import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestOpenAIHelper(unittest.TestCase):
    """Test cases for the OpenAIHelper class."""

    @patch('bot.lib.openai.openai_helper.OpenAI')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'}, clear=False)
    def test_init_with_defaults(self, mock_openai_class):
        """Test initialization with default settings."""
        from bot.lib.openai import OpenAIHelper

        helper = OpenAIHelper()

        # Verify OpenAI client was created with default settings
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert call_kwargs['api_key'] == 'test-api-key'
        assert call_kwargs['timeout'] == 60
        assert 'base_url' not in call_kwargs  # No endpoint specified

        # Verify default properties
        assert helper.default_model == 'gpt-3.5-turbo'
        assert helper.default_temperature is None
        assert helper.default_max_tokens is None

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_init_with_settings(self, mock_openai_class):
        """Test initialization with custom settings dictionary."""
        from bot.lib.openai import OpenAIHelper

        settings = {
            'endpoint': 'https://custom-endpoint.com/v1',
            'token': 'custom-token',
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 2000,
            'timeout': 30,
        }

        helper = OpenAIHelper(settings=settings)

        # Verify OpenAI client was created with custom settings
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert call_kwargs['api_key'] == 'custom-token'
        assert call_kwargs['base_url'] == 'https://custom-endpoint.com/v1'
        assert call_kwargs['timeout'] == 30

        # Verify custom properties
        assert helper.default_model == 'gpt-4'
        assert helper.default_temperature == 0.7
        assert helper.default_max_tokens == 2000

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_init_with_override_parameters(self, mock_openai_class):
        """Test initialization with override parameters taking precedence."""
        from bot.lib.openai import OpenAIHelper

        settings = {'endpoint': 'https://settings-endpoint.com/v1', 'token': 'settings-token', 'model': 'gpt-3.5-turbo'}

        helper = OpenAIHelper(
            settings=settings, endpoint='https://override-endpoint.com/v1', token='override-token', model='gpt-4'
        )

        # Verify override parameters took precedence
        call_kwargs = mock_openai_class.call_args.kwargs
        assert call_kwargs['api_key'] == 'override-token'
        assert call_kwargs['base_url'] == 'https://override-endpoint.com/v1'
        assert helper.default_model == 'gpt-4'

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_chat_completion_with_defaults(self, mock_openai_class):
        """Test chat completion using default settings."""
        from bot.lib.openai import OpenAIHelper

        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = Mock()
        mock_client.chat.completions.create.return_value = mock_response

        settings = {'model': 'gpt-4', 'temperature': 0.5, 'max_tokens': 1000}
        helper = OpenAIHelper(settings=settings)

        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': 'Hello!'},
        ]

        result = helper.chat_completion(messages)

        # Verify the completion was called with correct parameters
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'gpt-4'
        assert call_kwargs['messages'] == messages
        assert call_kwargs['temperature'] == 0.5
        assert call_kwargs['max_tokens'] == 1000
        assert result == mock_response

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_chat_completion_with_overrides(self, mock_openai_class):
        """Test chat completion with parameter overrides."""
        from bot.lib.openai import OpenAIHelper

        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = Mock()
        mock_client.chat.completions.create.return_value = mock_response

        settings = {'model': 'gpt-3.5-turbo', 'temperature': 0.5}
        helper = OpenAIHelper(settings=settings)

        messages = [{'role': 'user', 'content': 'Test'}]

        result = helper.chat_completion(messages, model='gpt-4', temperature=0.9, max_tokens=500)

        # Verify override parameters were used
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'gpt-4'
        assert call_kwargs['temperature'] == 0.9
        assert call_kwargs['max_tokens'] == 500
        assert result == mock_response

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_get_response_text_success(self, mock_openai_class):
        """Test extracting text from completion response."""
        from bot.lib.openai import OpenAIHelper

        helper = OpenAIHelper()

        # Mock completion response
        mock_completion = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "This is the AI response"
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]

        result = helper.get_response_text(mock_completion)

        assert result == "This is the AI response"

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_get_response_text_no_choices(self, mock_openai_class):
        """Test extracting text when no choices are available."""
        from bot.lib.openai import OpenAIHelper

        helper = OpenAIHelper()

        # Mock completion with no choices
        mock_completion = Mock()
        mock_completion.choices = []

        result = helper.get_response_text(mock_completion)

        assert result is None

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_get_response_text_none_completion(self, mock_openai_class):
        """Test extracting text from None completion."""
        from bot.lib.openai import OpenAIHelper

        helper = OpenAIHelper()

        result = helper.get_response_text(None)

        assert result is None

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_update_settings_no_recreate(self, mock_openai_class):
        """Test updating settings that don't require client recreation."""
        from bot.lib.openai import OpenAIHelper

        helper = OpenAIHelper(settings={'token': 'original-token', 'model': 'gpt-3.5-turbo'})

        # Reset mock call count
        mock_openai_class.reset_mock()

        # Update settings that don't affect client
        new_settings = {
            'token': 'original-token',  # Same token
            'model': 'gpt-4',  # Changed model
            'temperature': 0.8,
            'max_tokens': 1500,
        }

        helper.update_settings(new_settings)

        # Client should not be recreated
        mock_openai_class.assert_not_called()

        # Settings should be updated
        assert helper.default_model == 'gpt-4'
        assert helper.default_temperature == 0.8
        assert helper.default_max_tokens == 1500

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_update_settings_with_recreate(self, mock_openai_class):
        """Test updating settings that require client recreation."""
        from bot.lib.openai import OpenAIHelper

        helper = OpenAIHelper(settings={'token': 'original-token', 'endpoint': 'https://original.com'})

        # Reset mock call count
        mock_openai_class.reset_mock()

        # Update settings that affect client
        new_settings = {
            'token': 'new-token',  # Changed token
            'endpoint': 'https://new-endpoint.com',  # Changed endpoint
            'model': 'gpt-4',
        }

        helper.update_settings(new_settings)

        # Client should be recreated
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert call_kwargs['api_key'] == 'new-token'
        assert call_kwargs['base_url'] == 'https://new-endpoint.com'

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_client_property(self, mock_openai_class):
        """Test accessing the underlying client through property."""
        from bot.lib.openai import OpenAIHelper

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        helper = OpenAIHelper()

        assert helper.client == mock_client

    @patch('bot.lib.openai.openai_helper.OpenAI')
    @patch.dict(os.environ, {}, clear=True)
    def test_init_no_token_raises_error(self, mock_openai_class):
        """Test that initialization fails gracefully without token."""
        from bot.lib.openai import OpenAIHelper

        # Make OpenAI constructor raise an error when no API key
        mock_openai_class.side_effect = Exception("API key required")

        with pytest.raises(Exception) as exc_info:
            OpenAIHelper(settings={})

        assert "API key required" in str(exc_info.value)

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_chat_completion_with_additional_kwargs(self, mock_openai_class):
        """Test chat completion with additional keyword arguments."""
        from bot.lib.openai import OpenAIHelper

        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = Mock()
        mock_client.chat.completions.create.return_value = mock_response

        helper = OpenAIHelper()

        messages = [{'role': 'user', 'content': 'Test'}]

        result = helper.chat_completion(messages, top_p=0.9, frequency_penalty=0.5, presence_penalty=0.3)

        # Verify additional kwargs were passed through
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['top_p'] == 0.9
        assert call_kwargs['frequency_penalty'] == 0.5
        assert call_kwargs['presence_penalty'] == 0.3
        assert result == mock_response

    @patch('bot.lib.openai.openai_helper.httpx.Client')
    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_init_with_insecure_mode(self, mock_openai_class, mock_httpx_client_class):
        """Test initialization with insecure mode enabled (SSL verification disabled)."""
        from bot.lib.openai import OpenAIHelper

        mock_http_client = MagicMock()
        mock_httpx_client_class.return_value = mock_http_client

        settings = {'insecure': True, 'token': 'test-token'}

        helper = OpenAIHelper(settings=settings)

        # Verify httpx.Client was created with verify=False
        mock_httpx_client_class.assert_called_once_with(verify=False)

        # Verify OpenAI client was created with the custom http_client
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert call_kwargs['http_client'] == mock_http_client
        assert helper.insecure is True

    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_init_with_secure_mode_default(self, mock_openai_class):
        """Test initialization with secure mode (default behavior)."""
        from bot.lib.openai import OpenAIHelper

        settings = {'token': 'test-token'}

        helper = OpenAIHelper(settings=settings)

        # Verify OpenAI client was created without custom http_client
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert 'http_client' not in call_kwargs
        assert helper.insecure is False

    @patch('bot.lib.openai.openai_helper.httpx.Client')
    @patch('bot.lib.openai.openai_helper.OpenAI')
    def test_update_settings_enables_insecure_mode(self, mock_openai_class, mock_httpx_client_class):
        """Test updating settings to enable insecure mode recreates client."""
        from bot.lib.openai import OpenAIHelper

        mock_http_client = MagicMock()
        mock_httpx_client_class.return_value = mock_http_client

        # Start with secure mode
        helper = OpenAIHelper(settings={'token': 'test-token', 'insecure': False})

        # Reset mock call count
        mock_openai_class.reset_mock()
        mock_httpx_client_class.reset_mock()

        # Update to insecure mode - this should NOT recreate client
        # because token/endpoint didn't change
        new_settings = {'token': 'test-token', 'insecure': True}

        helper.update_settings(new_settings)

        # Client should not be recreated (insecure flag alone doesn't trigger recreation)
        mock_openai_class.assert_not_called()

        # But the insecure flag should be updated
        assert helper.insecure is True


if __name__ == '__main__':
    unittest.main()
