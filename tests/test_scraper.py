import sys
import os
import unittest
import asyncio
import httpx
from unittest.mock import patch, AsyncMock

# Add project root and 4backend to python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "4backend"))

# Use importlib to dynamically load scraper module due to numeric prefix "4backend"
import importlib.util
scraper_path = os.path.join(project_root, "4backend", "scraper.py")
spec = importlib.util.spec_from_file_location("scraper", scraper_path)
scraper = importlib.util.module_from_spec(spec)
sys.modules["scraper"] = scraper
spec.loader.exec_module(scraper)

class TestScraper(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    @patch("scraper.fetch_cached_company", new_callable=AsyncMock)
    @patch("scraper.save_company_profile", new_callable=AsyncMock)
    def test_database_cache_hit(self, mock_save, mock_fetch):
        """Test that scraping hits DB cache first without hitting Jina API."""
        mock_fetch.return_value = {
            "id": "uuid-1234",
            "company_name": "stripe.com",
            "scraped_markdown": "Stripe is a suite of APIs powering commerce."
        }
        
        result = self.loop.run_until_complete(scraper.scrape_company_domain("stripe.com"))
        
        # Assertions
        self.assertEqual(result["raw_context"], "Stripe is a suite of APIs powering commerce.")
        self.assertEqual(result["data_source"], "database")
        self.assertEqual(result["company_id"], "uuid-1234")
        
        # Verify db fetch was called but save was not
        mock_fetch.assert_called_once_with("stripe.com")
        mock_save.assert_not_called()

    @patch("scraper.fetch_cached_company", new_callable=AsyncMock)
    @patch("scraper.save_company_profile", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.get")
    def test_jina_reader_scrape(self, mock_get, mock_save, mock_fetch):
        """Test web scraping logic when cache is a miss."""
        mock_fetch.return_value = None
        mock_save.return_value = "uuid-live"
        
        # Mock httpx response
        mock_response = httpx.Response(
            status_code=200,
            text="## Live Scraped Jina Markdown  \n\n\n  Some duplicate line breaks. \n\n"
        )
        mock_get.return_value = mock_response

        # Set env variable
        with patch.dict(os.environ, {"JINA_API_KEY": "test_jina_key"}):
            result = self.loop.run_until_complete(scraper.scrape_company_domain("somecompany.com"))
        
        # Assertions
        self.assertEqual(result["raw_context"], "## Live Scraped Jina Markdown\n\nSome duplicate line breaks.")
        self.assertEqual(result["data_source"], "live")
        self.assertEqual(result["company_id"], "uuid-live")
        
        # Verify database calls and API headers
        mock_fetch.assert_called_once_with("somecompany.com")
        mock_save.assert_called_once_with("somecompany.com", "## Live Scraped Jina Markdown\n\nSome duplicate line breaks.")
        
        # Verify client headers
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs.get("headers"), {"Authorization": "Bearer test_jina_key"})

    @patch("scraper.fetch_cached_company", new_callable=AsyncMock)
    @patch("scraper.save_company_profile", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.get")
    def test_mock_fallback_offline(self, mock_get, mock_save, mock_fetch):
        """Test loading pre-scraped markdown files when scraper fails."""
        mock_fetch.return_value = None
        mock_save.return_value = "uuid-fallback"
        
        # Simulate network failure or timeout in httpx
        mock_get.side_effect = httpx.ConnectTimeout("Connection timed out")
        
        # We query a domain that is NOT registered under mock domains, which triggers default mock_company.txt fallback
        result = self.loop.run_until_complete(scraper.scrape_company_domain("unknown-domain.com"))
        
        # Assertions
        self.assertTrue(result["raw_context"].startswith("# Acme Enterprise Solutions"))
        self.assertEqual(result["data_source"], "cached")
        self.assertEqual(result["company_id"], "uuid-fallback")
        
        # Verify fetch was called and save was called for the fallback
        mock_fetch.assert_called_once_with("unknown-domain.com")
        mock_save.assert_called_once()
        self.assertEqual(mock_save.call_args[0][0], "unknown-domain.com")
        self.assertTrue(mock_save.call_args[0][1].startswith("# Acme Enterprise Solutions"))

    @patch("scraper.fetch_cached_company", new_callable=AsyncMock)
    @patch("scraper.save_company_profile", new_callable=AsyncMock)
    def test_direct_local_mock_domains(self, mock_save, mock_fetch):
        """Test that registered local mock domains load instantly from local files and cache to DB."""
        mock_fetch.return_value = None
        mock_save.return_value = "uuid-local-mock"

        result = self.loop.run_until_complete(scraper.scrape_company_domain("stripe.com"))
        
        # Assertions
        self.assertTrue("stripe" in result["raw_context"].lower())
        self.assertEqual(result["data_source"], "cached")
        self.assertEqual(result["company_id"], "uuid-local-mock")
        
        mock_fetch.assert_called_once_with("stripe.com")
        mock_save.assert_called_once()
        self.assertEqual(mock_save.call_args[0][0], "stripe.com")

if __name__ == "__main__":
    unittest.main()
