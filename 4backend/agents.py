import os
import json
import httpx
from typing import Type, List, Dict, Any
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

# Safe and robust import fallbacks to support backend/4backend folder configurations
try:
    from backend.schemas import (  # type: ignore
        CompanyBriefSchema,
        PainPointSchema,
        IcebreakerSchema,
        HookPitchSchema
    )
except ImportError:
    try:
        from .schemas import (
            CompanyBriefSchema,
            PainPointSchema,
            IcebreakerSchema,
            HookPitchSchema
        )
    except ImportError:
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from schemas import (
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
    Connects to OpenRouter using temperature 0.1 and enforces JSON output.
    Implements a 1-retry self-healing validation loop on failure.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set.")

    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/RJ-Guy/ConsulBot",
        "X-Title": "ConsulBot Sales Tool"
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # First attempt
        try:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            response_json = response.json()
            content = response_json["choices"][0]["message"]["content"]
            parsed_data = json.loads(content)
            # Try to validate with schema
            return schema.model_validate(parsed_data)
        except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError) as e:
            # Self-healing retry loop
            error_msg = str(e)
            
            # Format error details for the correction prompt
            correction_instruction = (
                f"Your previous response failed validation with the following error: {error_msg}.\n"
                f"Please output a corrected, valid JSON response that adheres strictly to the required schema "
                f"without any explanation or markdown formatting wrappers."
            )
            
            # Append correction flow to message history
            retry_messages = list(messages)
            retry_messages.append({"role": "assistant", "content": content if 'content' in locals() else ""})
            retry_messages.append({"role": "user", "content": correction_instruction})

            retry_payload = {
                "model": model,
                "messages": retry_messages,
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }

            # Retry attempt
            retry_response = await client.post(endpoint, headers=headers, json=retry_payload)
            retry_response.raise_for_status()
            retry_response_json = retry_response.json()
            retry_content = retry_response_json["choices"][0]["message"]["content"]
            retry_parsed_data = json.loads(retry_content)
            return schema.model_validate(retry_parsed_data)

async def run_company_brief_agent(raw_context: str) -> CompanyBriefSchema:
    """
    Extracts Company Brief schema from raw webpage markdown.
    """
    model = os.getenv("MODEL_COMPANY_BRIEF", "google/gemini-2.5-flash:free")
    system_prompt = (
        "You are an expert market research assistant. Your task is to analyze the provided raw company web text "
        "and extract a high-quality brief. "
        "You must respond with a JSON object matching this schema:\n"
        "{\n"
        '  "short_summary": "A concise summary of the company (maximum 2 sentences).",\n'
        '  "recent_milestones": ["list of 0 to 2 recent company milestones or updates (e.g. fundraise, product launch)"]\n'
        "}"
    )
    user_prompt = f"Here is the raw company website markdown:\n\n{raw_context}"
    return await call_openrouter(model, system_prompt, user_prompt, CompanyBriefSchema)

async def run_pain_points_agent(raw_context: str, job_title: str) -> PainPointSchema:
    """
    Infers exactly 3 strategic/operational pain points for a given prospect role.
    """
    model = os.getenv("MODEL_PAIN_POINTS", "meta-llama/llama-3-8b-instruct:free")
    system_prompt = (
        f"You are a sales preparation intelligence agent. Analyze the company website markdown and infer exactly 3 strategic "
        f"challenges or pain points relevant to the job title '{job_title}'. "
        f"You must respond with a JSON object matching this schema:\n"
        "{\n"
        '  "strategic_pain_points": [\n'
        '    {"challenge": "Specific operational or strategic challenge.", "why_it_matters": "Why it affects revenue, costs, or efficiency."},\n'
        '    {"challenge": "Second challenge.", "why_it_matters": "Why it matters."},\n'
        '    {"challenge": "Third challenge.", "why_it_matters": "Why it matters."}\n'
        "  ]\n"
        "}\n"
        "Ensure there are exactly 3 strategic pain points in the list."
    )
    user_prompt = f"Here is the raw company website markdown:\n\n{raw_context}"
    return await call_openrouter(model, system_prompt, user_prompt, PainPointSchema)

async def run_icebreakers_agent(company_brief: CompanyBriefSchema, job_title: str) -> IcebreakerSchema:
    """
    Generates 2 to 3 open-ended business questions tailored for a conversation starter.
    """
    model = os.getenv("MODEL_ICEBREAKERS", "google/gemini-2.5-flash:free")
    system_prompt = (
        f"You are a B2B sales advisor preparing cold outreach. Based on the company's summary and recent milestones, "
        f"generate 2 to 3 highly tailored, open-ended business questions to start a conversation with a prospect holding "
        f"the job title '{job_title}'.\n"
        f"Each question must end with a question mark '?'.\n"
        f"You must respond with a JSON object matching this schema:\n"
        "{\n"
        '  "icebreaker_questions": ["Question 1?", "Question 2?", "Question 3 (optional)?"]\n'
        "}"
    )
    user_prompt = (
        f"Company Summary: {company_brief.short_summary}\n"
        f"Company Milestones: {', '.join(company_brief.recent_milestones)}\n"
        f"Prospect Job Title: {job_title}"
    )
    return await call_openrouter(model, system_prompt, user_prompt, IcebreakerSchema)

async def run_hook_pitch_agent(
    company_brief: CompanyBriefSchema, 
    pain_points: PainPointSchema, 
    icebreakers: IcebreakerSchema, 
    job_title: str, 
    seller_product: str
) -> HookPitchSchema:
    """
    Writes a custom outreach golden hook and a value pitch addressing identified pain points.
    """
    model = os.getenv("MODEL_HOOK_PITCH", "meta-llama/llama-3-8b-instruct:free")
    system_prompt = (
        f"You are a world-class sales copywriter. Ingest the company brief, inferred pain points, and icebreakers. "
        f"Draft a highly personalized outreach hook and tailored value proposition pitch.\n"
        f"Rules:\n"
        f"1. 'golden_hook' must be a highly specific B2B opener/hook of 30 words or less.\n"
        f"2. 'tailored_pitch' must be a tailored 3-to-4 sentence value proposition pitch addressing identified pain points "
        f"with the seller's product/solution: '{seller_product}'.\n\n"
        f"You must respond with a JSON object matching this schema:\n"
        "{\n"
        '  "golden_hook": "Your specific cold opener under 30 words.",\n'
        '  "tailored_pitch": "Your value prop pitch of 3-to-4 sentences."\n'
        "}"
    )
    
    pain_points_text = "\n".join([f"- {p.challenge} (Why: {p.why_it_matters})" for p in pain_points.strategic_pain_points])
    icebreakers_text = "\n".join([f"- {q}" for q in icebreakers.icebreaker_questions])
    
    user_prompt = (
        f"Company Summary: {company_brief.short_summary}\n"
        f"Company Milestones: {', '.join(company_brief.recent_milestones)}\n"
        f"Prospect Job Title: {job_title}\n"
        f"Inferred Challenges:\n{pain_points_text}\n"
        f"Sample Icebreaker Questions:\n{icebreakers_text}\n"
        f"Seller Product/Solution: {seller_product}"
    )
    return await call_openrouter(model, system_prompt, user_prompt, HookPitchSchema)
