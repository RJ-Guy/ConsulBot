from backend.schemas import FullPrepSheetSchema

async def generate_prep_sheet(
    company_domain: str, 
    job_title: str, 
    seller_product: str
) -> FullPrepSheetSchema:
    """
    TODO: Execute the multi-agent pipeline with caching checks:
    1. Query sales_prep_sheets table for matching company_domain + job_title + seller_product.
       - If cache dossier hit: immediately parse JSON payload and return (data_source = 'database').
    2. Check/load company scraper context from DB / Jina Reader.
    3. Feed context sequentially to LLM Agents:
       - run_company_brief_agent
       - run_pain_points_agent
       - run_icebreakers_agent
       - run_hook_pitch_agent
    4. Compile FullPrepSheetSchema output.
    5. Write final output JSONB to sales_prep_sheets table.
    6. Return validated model sheet.
    """
    pass
