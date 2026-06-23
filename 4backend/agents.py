from typing import Type
from pydantic import BaseModel
from backend.schemas import (
    CompanyBriefSchema,
    PainPointSchema,
    IcebreakerSchema,
    HookPitchSchema
)

async def call_openrouter(
    model: str, 
    system_prompt: str, 
    user_prompt: str, 
    schema: Type[BaseModel]
) -> BaseModel:
    """
    TODO: Implement the OpenRouter client completion query.
    - Set up endpoints and auth headers with OPENROUTER_API_KEY.
    - Enforce JSON output mode.
    - Validate results with the Pydantic schema model.
    - Implement a 1-retry self-healing validation loop on failure.
    """
    pass

async def run_company_brief_agent(raw_context: str) -> CompanyBriefSchema:
    """
    TODO: Implement Company Brief extraction prompt using google/gemini-2.5-flash:free.
    """
    pass

async def run_pain_points_agent(raw_context: str, job_title: str) -> PainPointSchema:
    """
    TODO: Implement Pain Points inference prompt using meta-llama/llama-3-8b-instruct:free.
    """
    pass

async def run_icebreakers_agent(company_brief: CompanyBriefSchema, job_title: str) -> IcebreakerSchema:
    """
    TODO: Implement Icebreaker questions generation prompt using google/gemini-2.5-flash:free.
    """
    pass

async def run_hook_pitch_agent(
    company_brief: CompanyBriefSchema, 
    pain_points: PainPointSchema, 
    icebreakers: IcebreakerSchema, 
    job_title: str, 
    seller_product: str
) -> HookPitchSchema:
    """
    TODO: Implement Hook & Pitch copy writing prompt using meta-llama/llama-3-8b-instruct:free.
    """
    pass
