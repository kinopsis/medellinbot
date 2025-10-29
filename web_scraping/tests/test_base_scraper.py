"""
Test Base Scraper
=================

Unit tests for the base scraper functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from web_scraping.core.base_scraper import BaseScraper, ScrapingConfig, ScrapingResult


class TestScrapingConfig:
    """Test ScrapingConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ScrapingConfig(base_url="https://example.com")
        
        assert config.base_url == "https://example.com"
        assert config.rate_limit_delay == 1.0
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.user_agent == "MedellínBot/1.0"
        assert config.headers is not None
        assert "User-Agent" in config.headers
        
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ScrapingConfig(
            base_url="https://example.com",
            rate_limit_delay=2.5,
            timeout=60,
            max_retries=5,
            user_agent="TestBot/1.0"
        )
        
        assert config.rate_limit_delay == 2.5
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.user_agent == "TestBot/1.0"
        
    def test_custom_headers(self):
        """Test custom headers."""
        custom_headers = {"Authorization": "Bearer token"}
        config = ScrapingConfig(
            base_url="https://example.com",
            headers=custom_headers
        )
        
        assert config.headers == custom_headers


class TestScrapingResult:
    """Test ScrapingResult class."""
    
    def test_result_creation(self):
        """Test creating a scraping result."""
        result = ScrapingResult(
            success=True,
            data=[{"test": "data"}],
            error_message=None
        )
        
        assert result.success is True
        assert result.data == [{"test": "data"}]
        assert result.error_message is None
        assert result.timestamp is not None
        
    def test_result_with_error(self):
        """Test creating a result with error."""
        result = ScrapingResult(
            success=False,
            data=None,
            error_message="Test error"
        )
        
        assert result.success is False
        assert result.data is None
        assert result.error_message == "Test error"
        assert result.timestamp is not None


class MockScraper(BaseScraper):
    """Mock scraper for testing base functionality."""
    
    async def scrape(self):
        """Mock scrape method."""
        return ScrapingResult(success=True, data=[{"test": "data"}])


class TestBaseScraper:
    """Test BaseScraper class."""
    
    @pytest.fixture
    async def scraper(self):
        """Create a mock scraper for testing."""
        config = ScrapingConfig(base_url="https://example.com")
        scraper = MockScraper(config)
        await scraper.initialize()
        yield scraper
        await scraper.cleanup()
        
    def test_initialization(self):
        """Test scraper initialization."""
        config = ScrapingConfig(base_url="https://example.com")
        scraper = MockScraper(config)
        
        assert scraper.config == config
        assert scraper.session is None
        
    @pytest.mark.asyncio
    async def test_context_manager(self, scraper):
        """Test async context manager."""
        async with MockScraper(ScrapingConfig(base_url="https://example.com")) as ctx_scraper:
            assert ctx_scraper.session is not None
            
        # Session should be closed after context
        assert ctx_scraper.session is None
        
    @pytest.mark.asyncio
    async def test_fetch_page_success(self, scraper):
        """Test successful page fetching."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.text = AsyncMock(return_value="<html></html>")
            mock_response.raise_for_status = Mock()
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await scraper.fetch_page("https://example.com")
            
            assert result == "<html></html>"
            mock_get.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_fetch_page_retry_on_failure(self, scraper):
        """Test retry logic on page fetch failure."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # First two calls fail, third succeeds
            mock_get.side_effect = [
                Exception("Network error"),
                Exception("Network error"),
                Mock(
                    __aenter__=Mock(return_value=Mock(
                        text=AsyncMock(return_value="<html></html>"),
                        raise_for_status=Mock()
                    ))
                )
            ]
            
            result = await scraper.fetch_page("https://example.com")
            
            assert result == "<html></html>"
            assert mock_get.call_count == 3
            
    @pytest.mark.asyncio
    async def test_fetch_page_max_retries_exceeded(self, scraper):
        """Test behavior when max retries are exceeded."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            with pytest.raises(Exception):
                await scraper.fetch_page("https://example.com")
                
            assert mock_get.call_count == 3  # max_retries
            
    def test_parse_html(self, scraper):
        """Test HTML parsing."""
        html_content = "<html><body><h1>Test</h1></body></html>"
        soup = scraper.parse_html(html_content)
        
        assert soup is not None
        assert soup.find('h1').text == "Test"
        
    def test_extract_json_ld(self, scraper):
        """Test JSON-LD extraction."""
        html_content = """
        <html>
        <body>
            <script type="application/ld+json">
            {"@type": "Organization", "name": "Test Org"}
            </script>
            <script type="application/ld+json">
            {"@type": "Person", "name": "John Doe"}
            </script>
        </body>
        </html>
        """
        soup = scraper.parse_html(html_content)
        json_ld_data = scraper.extract_json_ld(soup)
        
        assert len(json_ld_data) == 2
        assert json_ld_data[0]["@type"] == "Organization"
        assert json_ld_data[1]["@type"] == "Person"
        
    def test_extract_json_ld_invalid(self, scraper):
        """Test JSON-LD extraction with invalid JSON."""
        html_content = """
        <html>
        <body>
            <script type="application/ld+json">
            invalid json
            </script>
        </body>
        </html>
        """
        soup = scraper.parse_html(html_content)
        json_ld_data = scraper.extract_json_ld(soup)
        
        assert len(json_ld_data) == 0
        
    def test_validate_data_valid(self, scraper):
        """Test data validation with valid data."""
        valid_data = [
            {"field1": "value1", "field2": "value2"},
            {"field1": "value3", "field2": "value4"}
        ]
        
        is_valid, errors = scraper.validate_data(valid_data)
        
        assert is_valid is True
        assert len(errors) == 0
        
    def test_validate_data_invalid(self, scraper):
        """Test data validation with invalid data."""
        invalid_data = [
            {"field1": "value1"},  # Missing field2
            "not a dict",  # Not a dict
            {},  # Empty dict
            None  # None value
        ]
        
        is_valid, errors = scraper.validate_data(invalid_data)
        
        assert is_valid is False
        assert len(errors) > 0
        
    def test_validate_data_empty(self, scraper):
        """Test data validation with empty data."""
        is_valid, errors = scraper.validate_data([])
        
        assert is_valid is False
        assert "No data to validate" in errors