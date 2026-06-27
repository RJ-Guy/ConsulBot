import os
import uuid
import datetime
from typing import Dict, Any, Optional, List
from supabase import create_client, Client

# Global supabase client initialization
_supabase_client: Optional[Client] = None

# In-memory dictionaries for offline development / isolation fallback
_offline_companies: Dict[str, Dict[str, Any]] = {}
_offline_prep_sheets: List[Dict[str, Any]] = []

def get_supabase_client() -> Optional[Client]:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
        
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
        
    try:
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        print(f"[DB Warning] Failed to initialize Supabase client: {e}")
    return None

def is_offline() -> bool:
    return os.getenv("SUPABASE_OFFLINE", "false").lower() == "true"

async def fetch_cached_company(company_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a cached company profile from `company_profiles` table or offline cache."""
    name_clean = company_name.lower().strip()
    if is_offline():
        return _offline_companies.get(name_clean)

    client = get_supabase_client()
    if not client:
        return _offline_companies.get(name_clean)
    try:
        response = client.table("company_profiles").select("*").eq("company_name", name_clean).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        print(f"[DB Warning] Error fetching cached company: {e}")
        return _offline_companies.get(name_clean)
    return None

async def save_company_profile(company_name: str, scraped_markdown: str, company_url: Optional[str] = None) -> Optional[str]:
    """Saves or updates a company's scraped markdown context. Returns the company UUID."""
    name_clean = company_name.lower().strip()
    
    # Save to local offline cache first as fallback
    if name_clean not in _offline_companies:
        company_id = str(uuid.uuid4())
        _offline_companies[name_clean] = {
            "id": company_id,
            "company_name": name_clean,
            "company_url": company_url or name_clean,
            "scraped_markdown": scraped_markdown,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    else:
        company_id = _offline_companies[name_clean]["id"]
        _offline_companies[name_clean]["scraped_markdown"] = scraped_markdown

    if is_offline():
        return company_id

    client = get_supabase_client()
    if not client:
        return company_id
    try:
        payload = {
            "company_name": name_clean,
            "company_url": company_url or name_clean,
            "scraped_markdown": scraped_markdown
        }
        response = client.table("company_profiles").upsert(payload, on_conflict="company_name").execute()
        if response.data:
            return response.data[0]["id"]
    except Exception as e:
        print(f"[DB Warning] Error saving company profile: {e}")
    return company_id

async def fetch_cached_prep_sheet(company_name: str, job_title: str, seller_product: str) -> Optional[Dict[str, Any]]:
    """Checks if a matching prep-sheet exists in `sales_prep_sheets` or offline cache."""
    name_clean = company_name.lower().strip()
    role_clean = job_title.strip()
    pitch_clean = seller_product.strip()

    if is_offline():
        company = _offline_companies.get(name_clean)
        if not company:
            return None
        for sheet in _offline_prep_sheets:
            if (sheet["company_id"] == company["id"] and 
                sheet["target_role"] == role_clean and 
                sheet["my_product_pitch"] == pitch_clean):
                return sheet
        return None

    client = get_supabase_client()
    if not client:
        return await fetch_cached_prep_sheet_offline(name_clean, role_clean, pitch_clean)
    try:
        company = await fetch_cached_company(name_clean)
        if not company:
            return None
            
        response = client.table("sales_prep_sheets").select("*")\
            .eq("company_id", company["id"])\
            .eq("target_role", role_clean)\
            .eq("my_product_pitch", pitch_clean)\
            .execute()
            
        if response.data:
            return response.data[0]
    except Exception as e:
        print(f"[DB Warning] Error fetching cached prep sheet: {e}")
        return await fetch_cached_prep_sheet_offline(name_clean, role_clean, pitch_clean)
    return None

async def fetch_cached_prep_sheet_offline(company_name: str, job_title: str, seller_product: str) -> Optional[Dict[str, Any]]:
    company = _offline_companies.get(company_name)
    if not company:
        return None
    for sheet in _offline_prep_sheets:
        if (sheet["company_id"] == company["id"] and 
            sheet["target_role"] == job_title and 
            sheet["my_product_pitch"] == seller_product):
            return sheet
    return None

async def save_prep_sheet(company_id: str, job_title: str, seller_product: str, payload: Dict[str, Any]) -> bool:
    """Inserts a generated prep-sheet dossier into the database or offline cache."""
    role_clean = job_title.strip()
    pitch_clean = seller_product.strip()

    # Save to local offline cache
    _offline_prep_sheets.append({
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "target_role": role_clean,
        "my_product_pitch": pitch_clean,
        "ai_generated_payload": payload,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    if is_offline():
        return True

    client = get_supabase_client()
    if not client:
        return True
    try:
        db_payload = {
            "company_id": company_id,
            "target_role": role_clean,
            "my_product_pitch": pitch_clean,
            "ai_generated_payload": payload
        }
        client.table("sales_prep_sheets").insert(db_payload).execute()
        return True
    except Exception as e:
        print(f"[DB Warning] Error inserting prep sheet: {e}")
    return True

async def fetch_recent_briefings(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches list of recently generated prep sheets with company details for sidebar history."""
    if is_offline():
        # Format list mapping structure
        return [{
            "id": s["id"],
            "target_role": s["target_role"],
            "my_product_pitch": s["my_product_pitch"],
            "ai_generated_payload": s["ai_generated_payload"],
            "created_at": s["created_at"],
            "company_profiles": {
                "company_name": next((c_name for c_name, c_val in _offline_companies.items() if c_val["id"] == s["company_id"]), "unknown")
            }
        } for s in _offline_prep_sheets[-limit:]]

    client = get_supabase_client()
    if not client:
        return await fetch_recent_briefings_offline(limit)
    try:
        response = client.table("sales_prep_sheets")\
            .select("id, target_role, my_product_pitch, ai_generated_payload, created_at, company_profiles(company_name)")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return response.data or []
    except Exception as e:
        print(f"[DB Warning] Error fetching recent briefings: {e}")
        return await fetch_recent_briefings_offline(limit)
    return []

async def fetch_recent_briefings_offline(limit: int = 10) -> List[Dict[str, Any]]:
    return [{
        "id": s["id"],
        "target_role": s["target_role"],
        "my_product_pitch": s["my_product_pitch"],
        "ai_generated_payload": s["ai_generated_payload"],
        "created_at": s["created_at"],
        "company_profiles": {
            "company_name": next((c_name for c_name, c_val in _offline_companies.items() if c_val["id"] == s["company_id"]), "unknown")
        }
    } for s in _offline_prep_sheets[-limit:]]
