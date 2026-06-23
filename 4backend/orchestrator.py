from backend.schemas import FullPrepSheetSchema

async def generate_prep_sheet(
    company_domain: str, 
    job_title: str, 
    seller_product: str
) -> FullPrepSheetSchema:
    """
    TODO: Coordinate execution sequence:
    1. Scrape domain context via scrape_company_domain.
    2. Execute run_company_brief_agent.
    3. Execute run_pain_points_agent.
    4. Execute run_icebreakers_agent.
    5. Execute run_hook_pitch_agent.
    6. Pack results with metadata and return FullPrepSheetSchema.
    """
    pass
