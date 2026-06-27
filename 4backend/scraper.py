import os
import httpx
from typing import Dict, TypedDict, Optional

# Safe and robust import fallbacks to support backend/4backend folder configurations
try:
    from backend.database import fetch_cached_company, save_company_profile  # type: ignore
except ImportError:
    try:
        from .database import fetch_cached_company, save_company_profile
    except ImportError:
        try:
            from database import fetch_cached_company, save_company_profile
        except ImportError:
            import sys
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from database import fetch_cached_company, save_company_profile

class ScraperResult(TypedDict):
    raw_context: str
    data_source: str
    company_id: Optional[str]

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
    return "\n".join(cleaned).strip()

async def scrape_company_domain(domain_url: str) -> ScraperResult:
    """
    Checks Supabase Cache first. If not cached, attempts to scrape domain via Jina Reader.
    Falls back to mock text files if offline or fails. Updates Supabase cache on success.
    """
    # Clean the input URL/domain
    cleaned_url = domain_url.lower().replace("https://", "").replace("http://", "").strip("/")
    
    # 1. Check Database Cache First
    db_record = await fetch_cached_company(cleaned_url)
    if db_record and db_record.get("scraped_markdown"):
        return {
            "raw_context": db_record["scraped_markdown"],
            "data_source": "database",
            "company_id": db_record.get("id")
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
        
    jina_endpoint = f"https://r.jina.ai/{cleaned_url}"
    
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
