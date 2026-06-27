import sys
import os
import unittest
from pydantic import ValidationError

# Add project root and 4backend to python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "4backend"))

# Use importlib to dynamically load schemas module due to numeric prefix "4backend"
import importlib.util
schemas_path = os.path.join(project_root, "4backend", "schemas.py")
spec = importlib.util.spec_from_file_location("schemas", schemas_path)
schemas = importlib.util.module_from_spec(spec)
sys.modules["schemas"] = schemas
spec.loader.exec_module(schemas)

class TestSchemas(unittest.TestCase):
    def test_company_brief_schema(self):
        """Test validation of company brief schema, including milestone length limits."""
        # Valid brief
        valid_data = {
            "short_summary": "Stripe building financial software infrastructure.",
            "recent_milestones": ["Launched Stripe Tax", "Completed $6.5B round"]
        }
        brief = schemas.CompanyBriefSchema(**valid_data)
        self.assertEqual(brief.short_summary, valid_data["short_summary"])

        # Invalid brief (3 milestones instead of max 2)
        invalid_data = {
            "short_summary": "Stripe summary.",
            "recent_milestones": ["Milestone 1", "Milestone 2", "Milestone 3"]
        }
        with self.assertRaises(ValidationError):
            schemas.CompanyBriefSchema(**invalid_data)

    def test_pain_point_schema(self):
        """Test that pain point schema enforces exactly 3 challenges."""
        # Valid pain points (exactly 3)
        valid_data = {
            "strategic_pain_points": [
                {"challenge": "C1", "why_it_matters": "W1"},
                {"challenge": "C2", "why_it_matters": "W2"},
                {"challenge": "C3", "why_it_matters": "W3"}
            ]
        }
        pain_points = schemas.PainPointSchema(**valid_data)
        self.assertEqual(len(pain_points.strategic_pain_points), 3)

        # Invalid pain points (2 items instead of 3)
        invalid_data = {
            "strategic_pain_points": [
                {"challenge": "C1", "why_it_matters": "W1"},
                {"challenge": "C2", "why_it_matters": "W2"}
            ]
        }
        with self.assertRaises(ValidationError):
            schemas.PainPointSchema(**invalid_data)

    def test_icebreaker_schema(self):
        """Test that icebreaker questions have lengths between 2 and 3, and end with '?'."""
        # Valid icebreakers
        valid_data = {
            "icebreaker_questions": ["How do you scale support?", "What is your roadmap?"]
        }
        icebreakers = schemas.IcebreakerSchema(**valid_data)
        self.assertEqual(len(icebreakers.icebreaker_questions), 2)

        # Invalid icebreakers (only 1 question)
        invalid_data_count = {
            "icebreaker_questions": ["Single question?"]
        }
        with self.assertRaises(ValidationError):
            schemas.IcebreakerSchema(**invalid_data_count)

        # Invalid icebreakers (question doesn't end with '?')
        invalid_data_format = {
            "icebreaker_questions": ["No question mark", "Valid question?"]
        }
        with self.assertRaises(ValidationError):
            schemas.IcebreakerSchema(**invalid_data_format)

    def test_hook_pitch_schema(self):
        """Test word limit assertions on the cold opener hook."""
        # Valid hook (10 words)
        valid_data = {
            "golden_hook": "I noticed Stripe recently completed a $6.5B series I funding round.",
            "tailored_pitch": "This is a tailored pitch of three sentences. It addresses pain points. It is complete."
        }
        hook = schemas.HookPitchSchema(**valid_data)
        self.assertEqual(hook.golden_hook, valid_data["golden_hook"])

        # Invalid hook (>30 words)
        invalid_hook = " ".join(["word"] * 35)
        invalid_data = {
            "golden_hook": invalid_hook,
            "tailored_pitch": "Standard pitch."
        }
        with self.assertRaises(ValidationError):
            schemas.HookPitchSchema(**invalid_data)

if __name__ == "__main__":
    unittest.main()
