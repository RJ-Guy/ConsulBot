import sys
import os
import unittest
import asyncio
from dotenv import load_dotenv
load_dotenv()

# Add project root and 4backend to python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "4backend"))

# Use importlib to dynamically load database module due to numeric prefix "4backend"
import importlib.util
database_path = os.path.join(project_root, "4backend", "database.py")
spec = importlib.util.spec_from_file_location("database", database_path)
database = importlib.util.module_from_spec(spec)
sys.modules["database"] = database
spec.loader.exec_module(database)

class TestDatabaseCaching(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.test_company = "pytest_temp.com"
        self.test_role = "QA Engineer"
        self.test_pitch = "Testing software"

    def tearDown(self):
        self.loop.close()

    async def run_db_tests(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            print("Skipping DB tests: No Supabase configs found.")
            return

        print("Testing company cache storage...")
        company_id = await database.save_company_profile(self.test_company, "## Temporary Scraped Markdown")
        self.assertIsNotNone(company_id)

        print("Testing company cache fetch...")
        company = await database.fetch_cached_company(self.test_company)
        self.assertIsNotNone(company)
        self.assertEqual(company["company_name"], self.test_company)

        print("Testing prep-sheet cache insertion...")
        dummy_payload = {
            "company_name": self.test_company,
            "job_title": self.test_role,
            "seller_product": self.test_pitch,
            "company_brief": {"short_summary": "Test Co summary.", "recent_milestones": []},
            "pain_points": {"strategic_pain_points": [{"challenge": "c", "why_it_matters": "w"}] * 3},
            "icebreakers": {"icebreaker_questions": ["Q1?", "Q2?"]},
            "hook_pitch": {"golden_hook": "Hook.", "tailored_pitch": "Pitch."},
            "meta": {"data_source": "live"}
        }
        success = await database.save_prep_sheet(company_id, self.test_role, self.test_pitch, dummy_payload)
        self.assertTrue(success)

        print("Testing prep-sheet cache read...")
        sheet = await database.fetch_cached_prep_sheet(self.test_company, self.test_role, self.test_pitch)
        self.assertIsNotNone(sheet)
        self.assertEqual(sheet["target_role"], self.test_role)

        print("Testing recent briefings retrieval...")
        recent = await database.fetch_recent_briefings(limit=5)
        self.assertIsInstance(recent, list)
        print("All Database cache tests completed successfully!")

    def test_runner(self):
        self.loop.run_until_complete(self.run_db_tests())

if __name__ == "__main__":
    unittest.main()
