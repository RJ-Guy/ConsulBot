# Backend Implementation Plan: Sales Call Prep-Sheet Generator

This document provides a highly detailed, component-by-component backend structure, interface specification, and step-by-step implementation guide for the **ConsulBot Sales Call Prep-Sheet Generator** backend. 

A backend development agent should be able to read this file and build the entire core pipeline (`backend/schemas.py`, `backend/scraper.py`, `backend/agents.py`, `backend/orchestrator.py`) and verify correctness using the included test scripts.

---

## 1. Directory Structure

The backend and frontend code will reside in separate `backend/` and `frontend/app/` directories. A mock data folder `mock_data/` and configuration files must be initialized at the project root.

```text
ConsulBot/
├── Plan/
│   └── backend_plan.md               # This plan
├── mock_data/                        # Pre-scraped company fallbacks
│   ├── stripe.txt                    # Stripe homepage markdown context
│   ├── vercel.txt                    # Vercel homepage markdown context
│   └── mock_company.txt              # Standard generic company fallback
├── backend/
│   ├── __init__.py
│   ├── schemas.py                    # Pydantic validation schemas
│   ├── scraper.py                    # Jina Reader client & caching logic
│   ├── agents.py                     # Agent system prompts & LLM client
│   └── orchestrator.py               # Chained pipeline execution logic
├── frontend/
│   └── app/
│       └── app.py                    # Streamlit UI Entry Point
├── tests/                            # Validation and testing scripts
│   ├── test_schemas.py
│   ├── test_scraper.py
│   ├── test_agents.py
│   └── test_orchestrator.py

├── .env.example                      # Configuration template
├── .gitignore                        # Git exclusion configuration
└── requirements.txt                  # Dependencies list

```

---

## 2. Dependencies & Configuration

### `requirements.txt`
The project requires asynchronous runtime support, schema validation, HTTP communication, frontend bindings (later), and config management.
```text
streamlit>=1.30.0
pydantic>=2.5.0
httpx>=0.25.0
python-dotenv>=1.0.0
openai>=1.3.0
```

### `.env.example`
Provide these configuration items:
```env
# API Keys
OPENROUTER_API_KEY=your_openrouter_api_key_here
JINA_API_KEY=your_jina_api_key_here

# LLM Model Configurations (OpenRouter Free Models)
MODEL_COMPANY_BRIEF=google/gemini-2.5-flash:free
MODEL_PAIN_POINTS=meta-llama/llama-3-8b-instruct:free
MODEL_ICEBREAKERS=google/gemini-2.5-flash:free
MODEL_HOOK_PITCH=meta-llama/llama-3-8b-instruct:free

```

---

## 3. Pydantic Schemas (`backend/schemas.py`)

Every agent step is constrained by a JSON contract enforced via Pydantic. Ensure strict types, explicit custom validators, and clean error descriptions are defined.

```python
import datetime
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator

# -------------------------------------------------------------
# Component Schemas
# -------------------------------------------------------------

class CompanyBriefSchema(BaseModel):
    short_summary: str = Field(
        ..., 
        description="A concise summary of the company (maximum 2 sentences)."
    )
    recent_milestones: List[str] = Field(
        ..., 
        min_items=0,
        max_items=2,
        description="List of 0 to 2 recent company milestones or updates (e.g. fundraise, product launch)."
    )

class PainPointItem(BaseModel):
    challenge: str = Field(..., description="The specific strategic challenge faced by this prospect profile.")
    why_it_matters: str = Field(..., description="Details on why this challenge affects operations or revenue.")

class PainPointSchema(BaseModel):
    strategic_pain_points: List[PainPointItem] = Field(
        ..., 
        min_items=3,
        max_items=3,
        description="Exactly 3 strategic pain points relevant to the job title based on the company data."
    )

    @field_validator("strategic_pain_points")
    @classmethod
    def check_exact_length(cls, v):
        if len(v) != 3:
            raise ValueError("The list of strategic pain points must contain exactly 3 items.")
        return v

class IcebreakerSchema(BaseModel):
    icebreaker_questions: List[str] = Field(
        ..., 
        min_items=2,
        max_items=3,
        description="2 to 3 open-ended business questions tailored for a conversation starter."
    )

    @field_validator("icebreaker_questions")
    @classmethod
    def check_question_format(cls, v):
        if not (2 <= len(v) <= 3):
            raise ValueError("Must contain between 2 and 3 icebreaker questions.")
        for idx, question in enumerate(v):
            cleaned = question.strip()
            if not cleaned.endswith("?"):
                raise ValueError(f"Question at index {idx} must end with a question mark '?'.")
        return v

class HookPitchSchema(BaseModel):
    golden_hook: str = Field(
        ..., 
        description="A highly specific B2B opener/hook. Maximum 30 words."
    )
    tailored_pitch: str = Field(
        ..., 
        description="A tailored 3-to-4 sentence value proposition pitch addressing identified pain points."
    )

    @field_validator("golden_hook")
    @classmethod
    def check_word_limit(cls, v):
        word_count = len(v.strip().split())
        if word_count > 30:
            raise ValueError(f"Golden hook must be 30 words or less. Found {word_count} words.")
        return v

# -------------------------------------------------------------
# Metadata Schema
# -------------------------------------------------------------

class MetaSchema(BaseModel):
    data_source: Literal["live", "cached"] = Field(..., description="Source of the scraped data.")
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="ISO 8601 generation timestamp."
    )

# -------------------------------------------------------------
# Master Sheet Schema
# -------------------------------------------------------------

class FullPrepSheetSchema(BaseModel):
    company_name: str = Field(..., description="Target company name or domain.")
    job_title: str = Field(..., description="Prospect's job title.")
    seller_product: str = Field(..., description="The seller's solution being pitched.")
    company_brief: CompanyBriefSchema = Field(..., description="Company summary and milestones.")
    pain_points: PainPointSchema = Field(..., description="Exactly 3 validated pain points.")
    icebreakers: IcebreakerSchema = Field(..., description="2-3 open-ended questions.")
    hook_pitch: HookPitchSchema = Field(..., description="Synthesized pitch & hook.")
    meta: MetaSchema = Field(..., description="Metadata tracking source and time.")
```

---

## 4. Data Scraping & Mock Fallback Layer (`backend/scraper.py`)

The scraper uses **Jina Reader API** (`https://r.jina.ai/`) to extract company homepage context. It must cleanly handle rate limits and fall back to local mock text files when offline or when specific domains are queried.

```python
import os
import httpx
from typing import Dict, TypedDict

class ScraperResult(TypedDict):
    raw_context: str
    data_source: str

# Map domain queries to local mock filepaths
MOCK_DOMAINS: Dict[str, str] = {
    "stripe.com": "mock_data/stripe.txt",
    "vercel.com": "mock_data/vercel.txt",
    "mock_company.com": "mock_data/mock_company.txt"
}

def clean_markdown(text: str) -> str:
    """Removes excessive line breaks, raw navigation menus, or system markdown junk."""
    lines = [line.strip() for line in text.splitlines()]
    # Remove large runs of empty lines
    cleaned = []
    prev_empty = False
    for line in lines:
        if line == "":
            if not prev_empty:
                cleaned.append(line)
                prev_empty = True
        else:
            cleaned.append(line)
            prev_empty = False
    return "\n".join(cleaned)

async def scrape_company_domain(domain_url: str) -> ScraperResult:
    """
    Attempts to scrape a domain via Jina Reader. 
    Falls back to mock data if domain matches MOCK_DOMAINS or if request fails.
    """
    cleaned_url = domain_url.lower().replace("https://", "").replace("http://", "").strip("/")
    
    # Check if domain has a direct mock registered
    if cleaned_url in MOCK_DOMAINS:
        file_path = MOCK_DOMAINS[cleaned_url]
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return {
                    "raw_context": clean_markdown(f.read()),
                    "data_source": "cached"
                }
                
    # Attempt Live Scrape
    jina_api_key = os.getenv("JINA_API_KEY")
    headers = {}
    if jina_api_key:
        headers["Authorization"] = f"Bearer {jina_api_key}"
        
    jina_endpoint = f"https://r.jina.ai/{domain_url}"
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(jina_endpoint, headers=headers)
            if response.status_code == 200:
                return {
                    "raw_context": clean_markdown(response.text),
                    "data_source": "live"
                }
        except httpx.HTTPError:
            # Fallback on exceptions (e.g. timeouts or connection errors)
            pass
            
    # Universal Fallback to mock_company.txt
    fallback_path = MOCK_DOMAINS["mock_company.com"]
    if os.path.exists(fallback_path):
         with open(fallback_path, "r", encoding="utf-8") as f:
             return {
                 "raw_context": clean_markdown(f.read()),
                 "data_source": "cached"
             }
             
    # Final emergency baseline context
    return {
        "raw_context": f"Baseline context for {domain_url}. Manual input required.",
        "data_source": "cached"
    }
```

---

## 5. Agent Engine & OpenRouter Client (`backend/agents.py`)

This file manages the communication with **OpenRouter**, enforcing structured JSON responses and implementing a self-healing **1-Retry Validation Loop** if Pydantic parsing fails.

```python
import os
import json
from typing import Type
import httpx
from pydantic import BaseModel, ValidationError

async def call_openrouter(
    model: str, 
    system_prompt: str, 
    user_prompt: str, 
    schema: Type[BaseModel]
) -> BaseModel:
    """
    Sends request to OpenRouter API. Enforces JSON output using JSON Mode, 
    and handles Pydantic schema validation. If validation fails, performs
    one defensive re-prompt containing validation details.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set.")
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501", # Required OpenRouter origin metadata
        "X-Title": "ConsulBot"
    }
    
    # Construct structured prompt informing model of JSON expectations
    # Inject schema.model_json_schema() into user guidelines to give LLM exact shape
    schema_definition = json.dumps(schema.model_json_schema(), indent=2)
    
    formatted_user_prompt = (
        f"{user_prompt}\n\n"
        f"IMPORTANT: You must return a JSON object that adheres strictly to this schema:\n"
        f"{schema_definition}\n\n"
        f"Do not write any markdown wrappers (like ```json ... ```) outside the JSON block."
    )
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_user_prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1 # Low temperature for reliable extraction
    }
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        # --- Attempt 1 ---
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        res_data = response.json()
        raw_text = res_data["choices"][0]["message"]["content"]
        
        try:
            return schema.model_validate_json(raw_text)
        except (ValidationError, json.JSONDecodeError) as e:
            # --- Attempt 2: Structured Re-prompt / Recovery Loop ---
            retry_user_prompt = (
                f"{formatted_user_prompt}\n\n"
                f"--- EXCEPTION DETECTED ---\n"
                f"Your previous response failed validation with the following error:\n"
                f"{str(e)}\n\n"
                f"Please fix the error, make sure all constraints (such as length, item count) "
                f"are strictly met, and provide a valid JSON object."
            )
            payload["messages"] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": retry_user_prompt}
            ]
            
            retry_response = await client.post(url, headers=headers, json=payload)
            retry_response.raise_for_status()
            retry_res_data = retry_response.json()
            retry_raw_text = retry_res_data["choices"][0]["message"]["content"]
            
            # If this validation fails, propagate the error up
            return schema.model_validate_json(retry_raw_text)

# -------------------------------------------------------------
# Individual Agent Execution Logic & Prompts
# -------------------------------------------------------------

async def run_company_brief_agent(raw_context: str) -> CompanyBriefSchema:
    model = os.getenv("MODEL_COMPANY_BRIEF", "google/gemini-2.5-flash:free")
    
    system_prompt = (
        "You are an expert analyst. Your job is to extract high-level intelligence "
        "about a target company from its website markdown. Focus on what they do "
        "and find up to 2 major recent updates (fundraising, product expansions, milestones)."
    )
    
    user_prompt = (
        f"Read the following website markdown context and extract a short summary "
        f"and 0 to 2 milestones.\n\n"
        f"Context:\n{raw_context}"
    )
    
    return await call_openrouter(model, system_prompt, user_prompt, CompanyBriefSchema)


async def run_pain_points_agent(raw_context: str, job_title: str) -> PainPointSchema:
    model = os.getenv("MODEL_PAIN_POINTS", "meta-llama/llama-3-8b-instruct:free")
    
    system_prompt = (
        "You are a B2B sales strategist. You infer pain points for specific corporate job roles "
        "by looking at company website context. Focus on strategic, operational, or technical pain "
        "points they likely face based on their context."
    )
    
    user_prompt = (
        f"Analyze the context and details for the job title: '{job_title}'. "
        f"Infer EXACTLY 3 strategic pain points that this role is responsible for solving. "
        f"For each, write down the 'challenge' and 'why_it_matters'.\n\n"
        f"Context:\n{raw_context}"
    )
    
    return await call_openrouter(model, system_prompt, user_prompt, PainPointSchema)


async def run_icebreakers_agent(company_brief: CompanyBriefSchema, job_title: str) -> IcebreakerSchema:
    model = os.getenv("MODEL_ICEBREAKERS", "google/gemini-2.5-flash:free")
    
    system_prompt = (
        "You are a warm, professional networker. You formulate open-ended conversational questions "
        "that showcase you have done your research about their company. Do not use generic templates."
    )
    
    brief_data = f"Summary: {company_brief.short_summary}\nMilestones: {', '.join(company_brief.recent_milestones)}"
    user_prompt = (
        f"Based on the following company profile and the prospect's job title: '{job_title}', "
        f"generate between 2 and 3 open-ended icebreaker questions ending with '?'.\n\n"
        f"Company Details:\n{brief_data}"
    )
    
    return await call_openrouter(model, system_prompt, user_prompt, IcebreakerSchema)


async def run_hook_pitch_agent(
    company_brief: CompanyBriefSchema, 
    pain_points: PainPointSchema, 
    icebreakers: IcebreakerSchema, 
    job_title: str, 
    seller_product: str
) -> HookPitchSchema:
    model = os.getenv("MODEL_HOOK_PITCH", "meta-llama/llama-3-8b-instruct:free")
    
    system_prompt = (
        "You are a world-class B2B sales copywriter. You write compelling hooks (cold email openers "
        "or verbal openers) and value-proposition pitches that connect a seller's product directly "
        "to a prospect's inferred pain points."
    )
    
    pain_points_text = "\n".join([f"- {p.challenge}: {p.why_it_matters}" for p in pain_points.strategic_pain_points])
    
    user_prompt = (
        f"Target Job Title: {job_title}\n"
        f"Seller's Product/Solution: {seller_product}\n\n"
        f"Company Brief:\n{company_brief.short_summary}\n\n"
        f"Prospect's Pain Points:\n{pain_points_text}\n\n"
        f"Your task:\n"
        f"1. Generate a 'golden_hook' - a B2B conversation opener/cold email hook. Maximum 30 words. "
        f"It must capture attention instantly, referring subtly to their corporate context.\n"
        f"2. Generate a 'tailored_pitch' - a highly relevant, 3-to-4 sentence value proposition "
        f"connecting the seller's product to the pain points."
    )
    
    return await call_openrouter(model, system_prompt, user_prompt, HookPitchSchema)
```

---

## 6. Orchestration Flow (`backend/orchestrator.py`)

The orchestrator brings the scraping and agent logic together, passing inputs between stages and returning the finalized complete schema structure.

```python
import datetime
from backend.scraper import scrape_company_domain
from backend.schemas import (
    FullPrepSheetSchema, 
    MetaSchema
)
from backend.agents import (
    run_company_brief_agent,
    run_pain_points_agent,
    run_icebreakers_agent,
    run_hook_pitch_agent
)

async def generate_prep_sheet(
    company_domain: str, 
    job_title: str, 
    seller_product: str
) -> FullPrepSheetSchema:
    """
    Executes the sequential multi-agent execution pipeline.
    """
    # Stage 0: Scrape or Fallback Mock Data
    scraper_res = await scrape_company_domain(company_domain)
    raw_context = scraper_res["raw_context"]
    data_source = scraper_res["data_source"]
    
    # Stage 1: Extract Company Brief
    company_brief = await run_company_brief_agent(raw_context)
    
    # Stage 2: Infer Pain Points
    pain_points = await run_pain_points_agent(raw_context, job_title)
    
    # Stage 3: Generate Icebreaker Questions
    icebreakers = await run_icebreakers_agent(company_brief, job_title)
    
    # Stage 4: Synthesize Golden Hook and Pitch
    hook_pitch = await run_hook_pitch_agent(
        company_brief=company_brief,
        pain_points=pain_points,
        icebreakers=icebreakers,
        job_title=job_title,
        seller_product=seller_product
    )
    
    # Package metadata
    meta = MetaSchema(
        data_source=data_source,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    
    # Return fully validated payload
    return FullPrepSheetSchema(
        company_name=company_domain,
        job_title=job_title,
        seller_product=seller_product,
        company_brief=company_brief,
        pain_points=pain_points,
        icebreakers=icebreakers,
        hook_pitch=hook_pitch,
        meta=meta
    )
```

---

## 7. Step-by-Step Backend Agent Directives

The backend agent should follow this sequence to implement and test the backend.

### Phase 1: Environment & File Prep
1. Initialize the `requirements.txt` file at root level.
2. Initialize `.env` file from the templates and add valid API credentials.
3. Create the directories: `backend/`, `frontend/`, `tests/` and `mock_data/`.
4. Create mock data files in `mock_data/`:
   - `stripe.txt`: Copy standard homepage texts or use clean mockup data.
   - `vercel.txt`: Mock Vercel homepage data.
   - `mock_company.txt`: Universal generic profile.

### Phase 2: Schema Development
1. Create `backend/schemas.py` and populate the structures.
2. Create and run `tests/test_schemas.py` to ensure Pydantic validates inputs correctly and fails when custom validations fail.

### Phase 3: Scraper Logic
1. Create `backend/scraper.py`.
2. Create `tests/test_scraper.py` to assert correct mock mappings and live HTTP call handling (offline behavior vs online behavior).

### Phase 4: Agents Core & Retry System
1. Create `backend/agents.py`.
2. Implement OpenRouter call with validation retries.
3. Test OpenRouter connectivity with standard models configured.

### Phase 5: Pipeline Orchestration
1. Create `backend/orchestrator.py` chaining the agents sequentially.
2. Build and run `tests/test_orchestrator.py` executing a full pass using mock scraper fallbacks to verify JSON integration.

---

## 8. Verification & Isolation Test Scripts

The following scripts should be created in the `tests/` directory to facilitate unit testing during implementation.

### Test 1: Pydantic Schema Validation (`tests/test_schemas.py`)
Run command: `python -m tests.test_schemas`
```python
import unittest
from pydantic import ValidationError
from backend.schemas import PainPointSchema, IcebreakerSchema, HookPitchSchema

class TestValidationSchemas(unittest.TestCase):
    def test_pain_point_validation(self):
        # Should fail when list count != 3
        with self.assertRaises(ValidationError):
            PainPointSchema(strategic_pain_points=[
                {"challenge": "c1", "why_it_matters": "w1"}
            ])
            
    def test_icebreaker_validation(self):
        # Should fail if question does not end with "?"
        with self.assertRaises(ValidationError):
            IcebreakerSchema(icebreaker_questions=["No question mark"])

    def test_hook_validation(self):
        # Should fail if hook is > 30 words
        long_hook = " ".join(["word"] * 31)
        with self.assertRaises(ValidationError):
            HookPitchSchema(golden_hook=long_hook, tailored_pitch="A good pitch.")

if __name__ == "__main__":
    unittest.main()
```

### Test 2: Scraper Mock and API Fetching (`tests/test_scraper.py`)
Run command: `python -m tests.test_scraper`
```python
import asyncio
from backend.scraper import scrape_company_domain

async def run_scraper_test():
    print("Testing stripe.com fallback...")
    res = await scrape_company_domain("stripe.com")
    print(f"Data source: {res['data_source']}")
    assert res["data_source"] == "cached"
    
    print("Testing unregistered domain fallback...")
    res2 = await scrape_company_domain("unknown-domain.io")
    print(f"Data source: {res2['data_source']}")
    assert res2["data_source"] == "cached"
    print("All scraper isolation checks passed!")

if __name__ == "__main__":
    asyncio.run(run_scraper_test())
```

### Test 3: Orchestrator End-to-End Pipeline (`tests/test_orchestrator.py`)
Run command: `python -m tests.test_orchestrator`
```python
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from backend.orchestrator import generate_prep_sheet

async def main():
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Skipping integration test: OPENROUTER_API_KEY is not set.")
        return
        
    print("Running integration test for stripe.com with orchestrator...")
    result = await generate_prep_sheet(
        company_domain="stripe.com",
        job_title="Director of Engineering",
        seller_product="ConsulBot automated scaling platform"
    )
    
    print("\n--- Synthesis Complete ---")
    print(f"Company Summary:\n{result.company_brief.short_summary}\n")
    print(f"Milestones: {result.company_brief.recent_milestones}\n")
    print(f"Pain Points:")
    for point in result.pain_points.strategic_pain_points:
        print(f"- {point.challenge} (Why: {point.why_it_matters})")
    print(f"\nIcebreakers:")
    for question in result.icebreakers.icebreaker_questions:
        print(f"- {question}")
    print(f"\nGolden Hook: {result.hook_pitch.golden_hook}")
    print(f"Pitch: {result.hook_pitch.tailored_pitch}")
    print(f"Source: {result.meta.data_source}")

if __name__ == "__main__":
    asyncio.run(main())
```
