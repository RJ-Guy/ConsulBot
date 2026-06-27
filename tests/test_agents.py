import sys
import os
import unittest
import asyncio
import httpx
from unittest.mock import patch, AsyncMock, MagicMock

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

agents_path = os.path.join(project_root, "4backend", "agents.py")
spec_agents = importlib.util.spec_from_file_location("agents", agents_path)
agents = importlib.util.module_from_spec(spec_agents)
sys.modules["agents"] = agents
spec_agents.loader.exec_module(agents)

class TestAgents(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "fake_openrouter_key",
            "MODEL_COMPANY_BRIEF": "fake-model-brief",
            "MODEL_PAIN_POINTS": "fake-model-pain",
            "MODEL_ICEBREAKERS": "fake-model-ice",
            "MODEL_HOOK_PITCH": "fake-model-hook"
        })
        self.env_patcher.start()
        # Mock request to prevent raise_for_status error
        self.mock_request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")

    def tearDown(self):
        self.env_patcher.stop()
        self.loop.close()

    @patch("httpx.AsyncClient.post")
    def test_openrouter_call(self, mock_post):
        """Test basic API formatting and request payloads to OpenRouter."""
        # Setup mock response with request
        mock_response = httpx.Response(
            status_code=200,
            json={
                "choices": [{
                    "message": {
                        "content": '{"short_summary": "Stripe processes online payments.", "recent_milestones": ["Stripe raised money."]}'
                    }
                }]
            },
            request=self.mock_request
        )
        mock_post.return_value = mock_response

        # Execute
        result = self.loop.run_until_complete(
            agents.call_openrouter(
                model="fake-model",
                system_prompt="system",
                user_prompt="user",
                schema=schemas.CompanyBriefSchema
            )
        )

        # Assertions
        self.assertIsInstance(result, schemas.CompanyBriefSchema)
        self.assertEqual(result.short_summary, "Stripe processes online payments.")
        self.assertEqual(result.recent_milestones, ["Stripe raised money."])
        
        # Verify post payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["model"], "fake-model")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer fake_openrouter_key")

    @patch("httpx.AsyncClient.post")
    def test_validation_retry_loop(self, mock_post):
        """Test that the self-healing retry loop executes when validation fails once."""
        # First response is invalid (missing recent_milestones)
        first_response = httpx.Response(
            status_code=200,
            json={
                "choices": [{
                    "message": {
                        "content": '{"short_summary": "Incomplete Stripe profile."}'
                    }
                }]
            },
            request=self.mock_request
        )
        # Second response is corrected
        second_response = httpx.Response(
            status_code=200,
            json={
                "choices": [{
                    "message": {
                        "content": '{"short_summary": "Incomplete Stripe profile.", "recent_milestones": ["Milestone fixed."]}'
                    }
                }]
            },
            request=self.mock_request
        )
        # Configure mock_post side effect to return first_response then second_response
        mock_post.side_effect = [first_response, second_response]

        # Execute
        result = self.loop.run_until_complete(
            agents.call_openrouter(
                model="fake-model",
                system_prompt="system",
                user_prompt="user",
                schema=schemas.CompanyBriefSchema
            )
        )

        # Assertions
        self.assertEqual(mock_post.call_count, 2)
        self.assertIsInstance(result, schemas.CompanyBriefSchema)
        self.assertEqual(result.short_summary, "Incomplete Stripe profile.")
        self.assertEqual(result.recent_milestones, ["Milestone fixed."])

    @patch("agents.call_openrouter", new_callable=AsyncMock)
    def test_agent_prompts(self, mock_call):
        """Test separate agent workflows (Company Brief, Pain Points, Hook & Pitch)."""
        # 1. Company Brief Agent
        mock_call.return_value = schemas.CompanyBriefSchema(
            short_summary="Test company brief summary.",
            recent_milestones=["Milestone A"]
        )
        brief_res = self.loop.run_until_complete(agents.run_company_brief_agent("raw website data"))
        self.assertEqual(brief_res.short_summary, "Test company brief summary.")
        mock_call.assert_called_with(
            "fake-model-brief",
            unittest.mock.ANY,
            "Here is the raw company website markdown:\n\nraw website data",
            schemas.CompanyBriefSchema
        )

        # 2. Pain Points Agent
        mock_call.reset_mock()
        mock_call.return_value = schemas.PainPointSchema(
            strategic_pain_points=[
                {"challenge": "C1", "why_it_matters": "W1"},
                {"challenge": "C2", "why_it_matters": "W2"},
                {"challenge": "C3", "why_it_matters": "W3"}
            ]
        )
        pain_res = self.loop.run_until_complete(agents.run_pain_points_agent("raw website data", "VP of Engineering"))
        self.assertEqual(len(pain_res.strategic_pain_points), 3)
        mock_call.assert_called_with(
            "fake-model-pain",
            unittest.mock.ANY,
            "Here is the raw company website markdown:\n\nraw website data",
            schemas.PainPointSchema
        )

        # 3. Hook & Pitch Agent
        mock_call.reset_mock()
        mock_call.return_value = schemas.HookPitchSchema(
            golden_hook="A custom opener.",
            tailored_pitch="A value prop pitch description."
        )
        
        brief = schemas.CompanyBriefSchema(short_summary="Summary", recent_milestones=["M1"])
        pain_points = schemas.PainPointSchema(
            strategic_pain_points=[
                {"challenge": "C1", "why_it_matters": "W1"},
                {"challenge": "C2", "why_it_matters": "W2"},
                {"challenge": "C3", "why_it_matters": "W3"}
            ]
        )
        icebreakers = schemas.IcebreakerSchema(icebreaker_questions=["Q1?", "Q2?"])
        
        hook_res = self.loop.run_until_complete(
            agents.run_hook_pitch_agent(
                company_brief=brief,
                pain_points=pain_points,
                icebreakers=icebreakers,
                job_title="VP of Sales",
                seller_product="SaaS Product"
            )
        )
        self.assertEqual(hook_res.golden_hook, "A custom opener.")
        mock_call.assert_called_with(
            "fake-model-hook",
            unittest.mock.ANY,
            unittest.mock.ANY,
            schemas.HookPitchSchema
        )

if __name__ == "__main__":
    unittest.main()
