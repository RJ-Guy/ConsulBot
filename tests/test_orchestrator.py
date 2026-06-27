import sys
import os
import unittest
import asyncio
from unittest.mock import patch, AsyncMock

# Add project root and 4backend to python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "4backend"))

# Use importlib to dynamically load modules due to numeric prefix "4backend"
import importlib.util

schemas_path = os.path.join(project_root, "4backend", "schemas.py")
spec_schemas = importlib.util.spec_from_file_location("schemas", schemas_path)
schemas = importlib.util.module_from_spec(spec_schemas)
sys.modules["schemas"] = schemas
spec_schemas.loader.exec_module(schemas)

orchestrator_path = os.path.join(project_root, "4backend", "orchestrator.py")
spec_orchestrator = importlib.util.spec_from_file_location("orchestrator", orchestrator_path)
orchestrator = importlib.util.module_from_spec(spec_orchestrator)
sys.modules["orchestrator"] = orchestrator
spec_orchestrator.loader.exec_module(orchestrator)

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    @patch("orchestrator.fetch_cached_prep_sheet", new_callable=AsyncMock)
    @patch("orchestrator.scrape_company_domain", new_callable=AsyncMock)
    def test_orchestrator_cache_hit(self, mock_scrape, mock_fetch_sheet):
        """Test that orchestrator returns cached dossier instantly on hit without running agents."""
        # Mock cached dossier response
        mock_fetch_sheet.return_value = {
            "ai_generated_payload": {
                "company_name": "stripe.com",
                "job_title": "VP of Sales",
                "seller_product": "AI Bot",
                "company_brief": {"short_summary": "Stripe summary.", "recent_milestones": []},
                "pain_points": {"strategic_pain_points": [{"challenge": "c", "why_it_matters": "w"}] * 3},
                "icebreakers": {"icebreaker_questions": ["Q1?", "Q2?"]},
                "hook_pitch": {"golden_hook": "Hook.", "tailored_pitch": "Pitch."},
                "meta": {"data_source": "live", "timestamp": "2026-06-25T21:55:00Z"}
            }
        }

        # Run
        result = self.loop.run_until_complete(
            orchestrator.generate_prep_sheet("stripe.com", "VP of Sales", "AI Bot")
        )

        # Assertions
        self.assertIsInstance(result, schemas.FullPrepSheetSchema)
        self.assertEqual(result.meta.data_source, "database") # Overridden to database
        self.assertEqual(result.company_name, "stripe.com")
        
        # Verify no scrape occurred
        mock_scrape.assert_not_called()

    @patch("orchestrator.fetch_cached_prep_sheet", new_callable=AsyncMock)
    @patch("orchestrator.scrape_company_domain", new_callable=AsyncMock)
    @patch("orchestrator.run_company_brief_agent", new_callable=AsyncMock)
    @patch("orchestrator.run_pain_points_agent", new_callable=AsyncMock)
    @patch("orchestrator.run_icebreakers_agent", new_callable=AsyncMock)
    @patch("orchestrator.run_hook_pitch_agent", new_callable=AsyncMock)
    @patch("orchestrator.save_prep_sheet", new_callable=AsyncMock)
    def test_orchestrator_cache_miss_full_pipeline(
        self, mock_save, mock_hook, mock_ice, mock_pain, mock_brief, mock_scrape, mock_fetch
    ):
        """Test that orchestrator runs the entire chained agent pipeline on cache miss."""
        mock_fetch.return_value = None
        mock_scrape.return_value = {
            "raw_context": "Raw web markdown content.",
            "data_source": "live",
            "company_id": "uuid-company-123"
        }
        
        # Setup mock returns for agents
        mock_brief.return_value = schemas.CompanyBriefSchema(
            short_summary="Summary.",
            recent_milestones=["Milestone A"]
        )
        mock_pain.return_value = schemas.PainPointSchema(
            strategic_pain_points=[
                {"challenge": "C1", "why_it_matters": "W1"},
                {"challenge": "C2", "why_it_matters": "W2"},
                {"challenge": "C3", "why_it_matters": "W3"}
            ]
        )
        mock_ice.return_value = schemas.IcebreakerSchema(
            icebreaker_questions=["Q1?", "Q2?"]
        )
        mock_hook.return_value = schemas.HookPitchSchema(
            golden_hook="Golden hook.",
            tailored_pitch="Pitch."
        )
        mock_save.return_value = True

        # Run
        result = self.loop.run_until_complete(
            orchestrator.generate_prep_sheet("stripe.com", "VP of Sales", "AI Bot")
        )

        # Assertions
        self.assertIsInstance(result, schemas.FullPrepSheetSchema)
        self.assertEqual(result.company_name, "stripe.com")
        self.assertEqual(result.meta.data_source, "live")
        
        # Verify agents execution and saving
        mock_brief.assert_called_once()
        mock_pain.assert_called_once()
        mock_ice.assert_called_once()
        mock_hook.assert_called_once()
        mock_save.assert_called_once()

if __name__ == "__main__":
    unittest.main()
