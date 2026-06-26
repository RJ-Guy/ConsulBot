# Backend Implementation Plan: Sales Call Prep-Sheet Generator (With Database Caching)

This document provides a highly detailed, component-by-component backend structure, interface specification, and step-by-step implementation guide for the **ConsulBot Sales Call Prep-Sheet Generator** backend, now integrated with a PostgreSQL/Supabase database caching layer. 

A backend development agent should be able to read this file and build the entire core pipeline (`backend/database.py`, `backend/schemas.py`, `backend/scraper.py`, `backend/agents.py`, `backend/orchestrator.py`) and verify correctness using the included test scripts.

---

## 1. Directory Structure

The backend and frontend code will reside in separate `backend/` and `frontend/app/` directories. A mock data folder `mock_data/` and configuration files must be initialized at the project root.

```text
ConsulBot/
├── Plan/
│   ├── backend_plan.md               # This plan
│   ├── frontend_plan.md
│   └── dataBase.md                   # Database blueprints
├── mock_data/                        # Pre-scraped company fallbacks
│   ├── stripe.txt                    # Stripe homepage markdown context
│   ├── vercel.txt                    # Vercel homepage markdown context
│   └── mock_company.txt              # Standard generic company fallback
├── backend/
│   ├── __init__.py
│   ├── database.py                   # Supabase database operations
│   ├── schemas.py                    # Pydantic validation schemas
│   ├── scraper.py                    # Jina Reader client & caching logic
│   ├── agents.py                     # Agent system prompts & LLM client
│   └── orchestrator.py               # Chained pipeline execution logic
├── frontend/
│   └── app/
│       └── app.py                    # Streamlit UI Entry Point (with DB History)
├── tests/                            # Validation and testing scripts
│   ├── test_schemas.py
│   ├── test_database.py              # Database integration checks
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
The project requires asynchronous runtime support, schema validation, HTTP communication, database bindings, and config management.
```text
streamlit>=1.30.0
pydantic>=2.5.0
httpx>=0.25.0
python-dotenv>=1.0.0
openai>=1.3.0
supabase>=2.3.0
```

### `.env.example`
Provide these configuration items:
```env
# API Keys
OPENROUTER_API_KEY=your_openrouter_api_key_here
JINA_API_KEY=your_jina_api_key_here

# Supabase Configurations
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_KEY=your_supabase_service_role_key_here

# LLM Model Configurations (OpenRouter Free Models)
MODEL_COMPANY_BRIEF=google/gemini-2.5-flash:free
MODEL_PAIN_POINTS=meta-llama/llama-3-8b-instruct:free
MODEL_ICEBREAKERS=google/gemini-2.5-flash:free
MODEL_HOOK_PITCH=meta-llama/llama-3-8b-instruct:free
```

---

## 3. Pydantic Schemas (`backend/schemas.py`)

Every agent step is constrained by a JSON contract enforced via Pydantic. Make sure to allow `"database"` as a valid data source in metadata.

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
    data_source: Literal["live", "cached", "database"] = Field(..., description="Source of the scraped data / cache status.")
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

## 4. Database Helper Layer (`backend/database.py`)

This module manages connectivity and queries to Supabase.

```python
import os
from typing import Dict, Any, Optional, List
from supabase import create_client, Client

# Global supabase client initialization
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
        
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
        
    _supabase_client = create_client(url, key)
    return _supabase_client

async def fetch_cached_company(company_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a cached company profile from `company_profiles` table."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        response = client.table("company_profiles").select("*").eq("company_name", company_name.lower().strip()).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        print(f"[DB Warning] Error fetching cached company: {e}")
    return None

async def save_company_profile(company_name: str, scraped_markdown: str, company_url: Optional[str] = None) -> Optional[str]:
    """Saves or updates a company's scraped markdown context. Returns the company UUID."""
    client = get_supabase_client()
    if not client:
        return None
    name_clean = company_name.lower().strip()
    try:
        # Upsert based on the unique company_name field
        payload = {
            "company_name": name_clean,
            "company_url": company_url or name_clean,
            "scraped_markdown": scraped_markdown
        }
        response = client.table("company_profiles").upsert(payload, on_conflict="company_name").execute()
        if response.data:
            return response.data[0]["id"]
    except Exception as e:
        print(f"[DB Error] Error saving company profile: {e}")
    return None

async def fetch_cached_prep_sheet(company_name: str, job_title: str, seller_product: str) -> Optional[Dict[str, Any]]:
    """Checks if a matching prep-sheet exists in `sales_prep_sheets`."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        company = await fetch_cached_company(company_name)
        if not company:
            return None
            
        response = client.table("sales_prep_sheets").select("*")\
            .eq("company_id", company["id"])\
            .eq("target_role", job_title.strip())\
            .eq("my_product_pitch", seller_product.strip())\
            .execute()
            
        if response.data:
            return response.data[0]
    except Exception as e:
        print(f"[DB Warning] Error fetching cached prep sheet: {e}")
    return None

async def save_prep_sheet(company_id: str, job_title: str, seller_product: str, payload: Dict[str, Any]) -> bool:
    """Inserts a generated prep-sheet dossier into the database."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        db_payload = {
            "company_id": company_id,
            "target_role": job_title.strip(),
            "my_product_pitch": seller_product.strip(),
            "ai_generated_payload": payload
        }
        client.table("sales_prep_sheets").insert(db_payload).execute()
        return True
    except Exception as e:
        print(f"[DB Error] Error inserting prep sheet: {e}")
        return False

async def fetch_recent_briefings(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches list of recently generated prep sheets with company details for sidebar history."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        # Fetch sheets joined with company names
        response = client.table("sales_prep_sheets")\
            .select("id, target_role, my_product_pitch, ai_generated_payload, created_at, company_profiles(company_name)")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return response.data or []
    except Exception as e:
        print(f"[DB Error] Error fetching recent briefings: {e}")
        return []
```

---

## 5. Data Scraping & Database Cache Check (`backend/scraper.py`)

The scraper uses **Jina Reader API** (`https://r.jina.ai/`) but first checks if the company profile context exists in the Supabase database cache.

```python
import os
import httpx
from typing import Dict, TypedDict, Optional
from backend.database import fetch_cached_company, save_company_profile

class ScraperResult(TypedDict):
    raw_context: str
    data_source: str
    company_id: Optional[str] # DB reference ID if present

# Map domain queries to local mock filepaths
MOCK_DOMAINS: Dict[str, str] = {
    "stripe.com": "mock_data/stripe.txt",
    "vercel.com": "mock_data/vercel.txt",
    "mock_company.com": "mock_data/mock_company.txt"
}

def clean_markdown(text: str) -> str:
    """Removes excessive line breaks, raw navigation menus, or system markdown junk."""
    lines = [line.strip() for line in text.splitlines()]
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
    Checks Supabase Cache first. If not cached, attempts to scrape domain via Jina Reader.
    Falls back to mock text files if offline or fails. Updates Supabase cache on success.
    """
    cleaned_url = domain_url.lower().replace("https://", "").replace("http://", "").strip("/")
    
    # 1. Check Database Cache First
    db_record = await fetch_cached_company(cleaned_url)
    if db_record and db_record.get("scraped_markdown"):
        return {
            "raw_context": db_record["scraped_markdown"],
            "data_source": "database",
            "company_id": db_record["id"]
        }

    # 2. Check if domain has a direct local mock registered (for offline UI/testing compatibility)
    if cleaned_url in MOCK_DOMAINS:
        file_path = MOCK_DOMAINS[cleaned_url]
        if os.path.exists(file_path):
            content = ""
            with open(file_path, "r", encoding="utf-8") as f:
                content = clean_markdown(f.read())
            # Save mock load to database if connection available
            company_id = await save_company_profile(cleaned_url, content)
            return {
                "raw_context": content,
                "data_source": "cached",
                "company_id": company_id
            }
                
    # 3. Attempt Live Scrape via Jina Reader
    jina_api_key = os.getenv("JINA_API_KEY")
    headers = {}
    if jina_api_key:
        headers["Authorization"] = f"Bearer {jina_api_key}"
        
    jina_endpoint = f"https://r.jina.ai/{domain_url}"
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(jina_endpoint, headers=headers)
            if response.status_code == 200:
                raw_text = clean_markdown(response.text)
                # Store new scrape context in database
                company_id = await save_company_profile(cleaned_url, raw_text)
                return {
                    "raw_context": raw_text,
                    "data_source": "live",
                    "company_id": company_id
                }
        except httpx.HTTPError:
            pass
            
    # 4. Universal Fallback to mock_company.txt
    fallback_path = MOCK_DOMAINS["mock_company.com"]
    if os.path.exists(fallback_path):
        content = ""
        with open(fallback_path, "r", encoding="utf-8") as f:
            content = clean_markdown(f.read())
        company_id = await save_company_profile(cleaned_url, content)
        return {
            "raw_context": content,
            "data_source": "cached",
            "company_id": company_id
        }
             
    # 5. Final emergency baseline context
    company_id = await save_company_profile(cleaned_url, f"Baseline context for {domain_url}.")
    return {
        "raw_context": f"Baseline context for {domain_url}. Manual input required.",
        "data_source": "cached",
        "company_id": company_id
    }
```

---

## 6. Orchestration Flow (`backend/orchestrator.py`)

The orchestrator checks database history for the final generated sheet before kicking off the chained LLM pipeline.

```python
import datetime
from backend.database import fetch_cached_prep_sheet, save_prep_sheet
from backend.scraper import scrape_company_domain
from backend.schemas import (
    FullPrepSheetSchema, 
    MetaSchema,
    CompanyBriefSchema,
    PainPointSchema,
    IcebreakerSchema,
    HookPitchSchema
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
    Checks DB cache for pre-computed dossier first to return in 0.1 seconds.
    """
    domain_clean = company_domain.lower().strip()
    role_clean = job_title.strip()
    pitch_clean = seller_product.strip()

    # 1. Check if complete Dossier is already generated in database
    dossier_record = await fetch_cached_prep_sheet(domain_clean, role_clean, pitch_clean)
    if dossier_record:
        payload = dossier_record["ai_generated_payload"]
        # Update metadata to show it was sourced from database
        payload["meta"]["data_source"] = "database"
        return FullPrepSheetSchema.model_validate(payload)

    # 2. Complete Dossier is not found - Run Stage 0 (Scraper check / load)
    scraper_res = await scrape_company_domain(domain_clean)
    raw_context = scraper_res["raw_context"]
    data_source = scraper_res["data_source"]
    company_id = scraper_res["company_id"]
    
    # Stage 1: Extract Company Brief
    company_brief = await run_company_brief_agent(raw_context)
    
    # Stage 2: Infer Pain Points
    pain_points = await run_pain_points_agent(raw_context, role_clean)
    
    # Stage 3: Generate Icebreaker Questions
    icebreakers = await run_icebreakers_agent(company_brief, role_clean)
    
    # Stage 4: Synthesize Golden Hook and Pitch
    hook_pitch = await run_hook_pitch_agent(
        company_brief=company_brief,
        pain_points=pain_points,
        icebreakers=icebreakers,
        job_title=role_clean,
        seller_product=pitch_clean
    )
    
    # Package metadata
    meta = MetaSchema(
        data_source=data_source,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    
    final_sheet = FullPrepSheetSchema(
        company_name=domain_clean,
        job_title=role_clean,
        seller_product=pitch_clean,
        company_brief=company_brief,
        pain_points=pain_points,
        icebreakers=icebreakers,
        hook_pitch=hook_pitch,
        meta=meta
    )

    # 3. Save the newly generated prep sheet to the database
    if company_id:
        await save_prep_sheet(company_id, role_clean, pitch_clean, final_sheet.model_dump())
    
    return final_sheet
```

---

## 7. Step-by-Step Backend Agent Directives

1. **DB Schema Setup:** Install `supabase` in `requirements.txt`. Make sure the Postgres schema in Supabase has correct constraints.
2. **Database Helper (`backend/database.py`):** Code Supabase connection using async or standard calls.
3. **Scraper logic updates (`backend/scraper.py`):** Check DB for company markdown cache prior to contacting Jina Reader.
4. **Orchestrator logic updates (`backend/orchestrator.py`):** Check DB for existing compiled dossiers, returning immediately on hit, and saving on pipeline completion.

---

## 8. Verification & Isolation Test Scripts

Create `tests/test_database.py` to check database caching functions:

```python
# Run: python -m tests.test_database
import asyncio
import os
import unittest
from dotenv import load_dotenv
load_dotenv()

from backend.database import save_company_profile, fetch_cached_company, save_prep_sheet, fetch_cached_prep_sheet

class TestDatabaseCaching(unittest.TestCase):
    def setUp(self):
        self.test_company = "pytest_temp.com"
        self.test_role = "QA Engineer"
        self.test_pitch = "Testing software"

    async def run_db_tests(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            print("Skipping DB tests: No Supabase configs found.")
            return

        print("Testing company cache storage...")
        company_id = await save_company_profile(self.test_company, "## Temporary Scraped Markdown")
        self.assertIsNotNone(company_id)

        print("Testing company cache fetch...")
        company = await fetch_cached_company(self.test_company)
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
        success = await save_prep_sheet(company_id, self.test_role, self.test_pitch, dummy_payload)
        self.assertTrue(success)

        print("Testing prep-sheet cache read...")
        sheet = await fetch_cached_prep_sheet(self.test_company, self.test_role, self.test_pitch)
        self.assertIsNotNone(sheet)
        self.assertEqual(sheet["target_role"], self.test_role)
        print("All Database cache tests completed successfully!")

    def test_runner(self):
        asyncio.run(self.run_db_tests())

if __name__ == "__main__":
    unittest.main()
```
