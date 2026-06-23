from typing import List, Literal, Dict, Any
from pydantic import BaseModel, Field

class CompanyBriefSchema(BaseModel):
    """
    TODO: Define company brief fields:
    - short_summary (str): Concise 2-sentence summary.
    - recent_milestones (List[str]): 0 to 2 milestones.
    """
    pass

class PainPointItem(BaseModel):
    """
    TODO: Define challenge and why_it_matters fields.
    """
    pass

class PainPointSchema(BaseModel):
    """
    TODO: Define strategic_pain_points (List[PainPointItem]).
    - Must validate that the list has exactly 3 items.
    """
    pass

class IcebreakerSchema(BaseModel):
    """
    TODO: Define icebreaker_questions (List[str]).
    - Must validate 2 to 3 items ending with '?'.
    """
    pass

class HookPitchSchema(BaseModel):
    """
    TODO: Define hook and pitch fields:
    - golden_hook (str): Max 30 words B2B opener.
    - tailored_pitch (str): 3-4 sentence value prop.
    """
    pass

class MetaSchema(BaseModel):
    """
    TODO: Define metadata tracking fields:
    - data_source (Literal['live', 'cached']).
    - timestamp (str): ISO formatted time.
    """
    pass

class FullPrepSheetSchema(BaseModel):
    """
    TODO: Combine all component schemas:
    - company_name (str)
    - job_title (str)
    - seller_product (str)
    - company_brief (CompanyBriefSchema)
    - pain_points (PainPointSchema)
    - icebreakers (IcebreakerSchema)
    - hook_pitch (HookPitchSchema)
    - meta (MetaSchema)
    """
    pass
