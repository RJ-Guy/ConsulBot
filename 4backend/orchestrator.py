import datetime
import os

# Safe and robust import fallbacks to support backend/4backend folder configurations
try:
    from backend.database import fetch_cached_prep_sheet, save_prep_sheet  # type: ignore
    from backend.scraper import scrape_company_domain  # type: ignore
    from backend.schemas import FullPrepSheetSchema, MetaSchema  # type: ignore
    from backend.agents import (  # type: ignore
        run_company_brief_agent,
        run_pain_points_agent,
        run_icebreakers_agent,
        run_hook_pitch_agent
    )
except ImportError:
    try:
        from .database import fetch_cached_prep_sheet, save_prep_sheet
        from .scraper import scrape_company_domain
        from .schemas import FullPrepSheetSchema, MetaSchema
        from .agents import (
            run_company_brief_agent,
            run_pain_points_agent,
            run_icebreakers_agent,
            run_hook_pitch_agent
        )
    except ImportError:
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from database import fetch_cached_prep_sheet, save_prep_sheet
        from scraper import scrape_company_domain
        from schemas import FullPrepSheetSchema, MetaSchema
        from agents import (
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
