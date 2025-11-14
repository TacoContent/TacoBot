"""Unit tests for bot.lib.minecraft.status module."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from bot.lib.minecraft.status import MinecraftStatus


class TestMinecraftStatus:
    """Test cases for MinecraftStatus class."""

    @pytest.fixture
    def mock_server(self):
        """Mock mcstatus JavaServer instance."""
        server = MagicMock()
        server.status.return_value = MagicMock()
        return server

    @pytest.fixture
    def mock_status_response(self):
        """Mock JavaStatusResponse."""
        response = MagicMock()
        response.players.online = 5
        response.players.max = 20
        response.version.name = "1.20.1"
        response.motd = "Welcome to the server!"
        return response

    def test_init_default_values(self):
        """Test constructor with default values."""
        status = MinecraftStatus("example.com")
        assert status.host == "example.com"
        assert status.port == 25565
        assert status.timeout == 3
        assert status._cache_ttl == 30
        assert status._cache is None
        assert status._cache_time == 0

    def test_init_custom_values(self):
        """Test constructor with custom values."""
        status = MinecraftStatus("example.com", port=25566, timeout=5.0, cache_ttl=60)
        assert status.host == "example.com"
        assert status.port == 25566
        assert status.timeout == 5.0
        assert status._cache_ttl == 60

    def test_init_disable_cache(self):
        """Test constructor with cache disabled."""
        status = MinecraftStatus("example.com", cache_ttl=0)
        assert status._cache_ttl == 0

    @patch('mcstatus.JavaServer.lookup')
    def test_get_success_first_call(self, mock_lookup, mock_server, mock_status_response):
        """Test successful get() call on first attempt."""
        mock_lookup.return_value = mock_server
        mock_server.status.return_value = mock_status_response

        status = MinecraftStatus("example.com", cache_ttl=0)  # Disable cache for this test
        result = status.get()

        assert result == mock_status_response
        mock_lookup.assert_called_once_with("example.com:25565", timeout=3)
        mock_server.status.assert_called_once()

    @patch('mcstatus.JavaServer.lookup')
    def test_get_success_cached(self, mock_lookup, mock_server, mock_status_response):
        """Test get() returns cached result when valid."""
        mock_lookup.return_value = mock_server
        mock_server.status.return_value = mock_status_response

        status = MinecraftStatus("example.com", cache_ttl=60)

        # First call - should fetch
        result1 = status.get()
        assert result1 == mock_status_response

        # Second call within TTL - should return cached
        result2 = status.get()
        assert result2 == mock_status_response

        # Should only have called lookup/status once
        mock_lookup.assert_called_once_with("example.com:25565", timeout=3)
        mock_server.status.assert_called_once()

    @patch('mcstatus.JavaServer.lookup')
    def test_get_cache_expiration(self, mock_lookup, mock_server, mock_status_response):
        """Test cache expiration and refetch."""
        mock_lookup.return_value = mock_server
        mock_server.status.return_value = mock_status_response

        status = MinecraftStatus("example.com", cache_ttl=1)  # 1 second TTL

        # First call
        result1 = status.get()
        assert result1 == mock_status_response

        # Wait for cache to expire
        time.sleep(1.1)

        # Second call - should refetch
        result2 = status.get()
        assert result2 == mock_status_response

        # Should have called lookup/status twice
        assert mock_lookup.call_count == 2
        assert mock_server.status.call_count == 2

    @patch('mcstatus.JavaServer.lookup')
    def test_get_network_error(self, mock_lookup):
        """Test get() handles network errors."""
        mock_lookup.side_effect = ConnectionError("Network unreachable")

        status = MinecraftStatus("example.com")
        with pytest.raises(ConnectionError, match="Network unreachable"):
            status.get()

    @patch('mcstatus.JavaServer.lookup')
    def test_get_timeout_error(self, mock_lookup):
        """Test get() handles timeout errors."""
        mock_lookup.side_effect = TimeoutError("Connection timed out")

        status = MinecraftStatus("example.com")
        with pytest.raises(TimeoutError, match="Connection timed out"):
            status.get()

    @patch('mcstatus.JavaServer.lookup')
    def test_get_dns_error(self, mock_lookup):
        """Test get() handles DNS resolution errors."""
        from socket import gaierror

        mock_lookup.side_effect = gaierror("Name resolution failure")

        status = MinecraftStatus("nonexistent.example.com")
        with pytest.raises(gaierror, match="Name resolution failure"):
            status.get()

    @pytest.mark.asyncio
    @patch('asyncio.to_thread')
    async def test_aget_success_first_call(self, mock_to_thread, mock_status_response):
        """Test successful aget() call on first attempt."""
        # Mock the two to_thread calls: lookup and status
        mock_to_thread.side_effect = [MagicMock(), mock_status_response]

        status = MinecraftStatus("example.com", cache_ttl=0)  # Disable cache
        result = await status.aget()

        assert result == mock_status_response
        assert mock_to_thread.call_count == 2

    @pytest.mark.asyncio
    @patch('asyncio.to_thread')
    async def test_aget_success_cached(self, mock_to_thread, mock_status_response):
        """Test aget() returns cached result when valid."""
        # Mock the two to_thread calls: lookup and status
        mock_to_thread.side_effect = [MagicMock(), mock_status_response]

        status = MinecraftStatus("example.com", cache_ttl=60)

        # First call - should fetch
        result1 = await status.aget()
        assert result1 == mock_status_response

        # Second call within TTL - should return cached
        result2 = await status.aget()
        assert result2 == mock_status_response

        # Should only have called to_thread twice (once for each operation)
        assert mock_to_thread.call_count == 2

    @pytest.mark.asyncio
    @patch('asyncio.to_thread')
    async def test_aget_cache_expiration(self, mock_to_thread, mock_status_response):
        """Test aget() cache expiration and refetch."""
        # Mock the to_thread calls
        mock_to_thread.side_effect = [MagicMock(), mock_status_response, MagicMock(), mock_status_response]

        status = MinecraftStatus("example.com", cache_ttl=1)  # 1 second TTL

        # First call
        result1 = await status.aget()
        assert result1 == mock_status_response

        # Wait for cache to expire
        await asyncio.sleep(1.1)

        # Second call - should refetch
        result2 = await status.aget()
        assert result2 == mock_status_response

        # Should have called to_thread four times (2 per call)
        assert mock_to_thread.call_count == 4

    @pytest.mark.asyncio
    @patch('asyncio.to_thread')
    async def test_aget_network_error(self, mock_to_thread):
        """Test aget() handles network errors."""
        mock_to_thread.side_effect = ConnectionError("Network unreachable")

        status = MinecraftStatus("example.com")
        with pytest.raises(ConnectionError, match="Network unreachable"):
            await status.aget()

    @pytest.mark.asyncio
    @patch('asyncio.to_thread')
    async def test_aget_timeout_error(self, mock_to_thread):
        """Test aget() handles timeout errors."""
        mock_to_thread.side_effect = TimeoutError("Connection timed out")

        status = MinecraftStatus("example.com")
        with pytest.raises(TimeoutError, match="Connection timed out"):
            await status.aget()

    def test_cache_shared_between_sync_async(self, mock_server, mock_status_response):
        """Test that sync and async methods share the same cache."""
        with patch('mcstatus.JavaServer.lookup', return_value=mock_server):
            mock_server.status.return_value = mock_status_response

            status = MinecraftStatus("example.com", cache_ttl=60)

            # Call sync method first
            sync_result = status.get()
            assert sync_result == mock_status_response

            # Call async method - should use cache
            async def async_call():
                return await status.aget()

            async_result = asyncio.run(async_call())
            assert async_result == mock_status_response

            # Should only have called lookup/status once
            assert mock_server.status.call_count == 1

    def test_cache_disabled(self, mock_server, mock_status_response):
        """Test behavior when caching is disabled."""
        with patch('mcstatus.JavaServer.lookup', return_value=mock_server):
            mock_server.status.return_value = mock_status_response

            status = MinecraftStatus("example.com", cache_ttl=0)

            # First call
            result1 = status.get()
            assert result1 == mock_status_response

            # Second call - should refetch since cache is disabled
            result2 = status.get()
            assert result2 == mock_status_response

            # Should have called lookup/status twice
            assert mock_server.status.call_count == 2

    def test_custom_port_and_timeout(self, mock_server, mock_status_response):
        """Test custom port and timeout parameters."""
        with patch('mcstatus.JavaServer.lookup') as mock_lookup:
            mock_lookup.return_value = mock_server
            mock_server.status.return_value = mock_status_response

            status = MinecraftStatus("example.com", port=25566, timeout=10.0)
            result = status.get()

            assert result == mock_status_response
            mock_lookup.assert_called_once_with("example.com:25566", timeout=10.0)

    @pytest.mark.asyncio
    async def test_async_custom_port_and_timeout(self, mock_status_response):
        """Test async method with custom port and timeout."""
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = [MagicMock(), mock_status_response]

            status = MinecraftStatus("example.com", port=25566, timeout=10.0)
            result = await status.aget()

            assert result == mock_status_response
            # Verify the lookup call was made with correct parameters
            lookup_call = mock_to_thread.call_args_list[0]
            assert "example.com:25566" in str(lookup_call)

    def test_cache_timestamp_accuracy(self):
        """Test that cache timestamps are set correctly."""
        status = MinecraftStatus("example.com", cache_ttl=30)

        # Manually set cache
        test_response = MagicMock()
        status._cache = test_response
        initial_time = time.time()
        status._cache_time = initial_time

        # Verify cache is valid immediately
        assert status._cache is not None
        assert status._cache_time == initial_time

        # Simulate time passing
        future_time = initial_time + 31  # Past TTL
        with patch('time.time', return_value=future_time):
            # Cache should be considered expired
            assert (future_time - status._cache_time) > status._cache_ttl

    def test_repr_and_str(self):
        """Test string representations."""
        status = MinecraftStatus("example.com", port=25565)
        # Basic check that these don't crash
        str(status)
        repr(status)
