from typing import List, Literal, Dict, Any
from pydantic import BaseModel, Field

class CompanyBriefSchema(BaseModel):
    """
    TODO: Define company brief fields:
    - short_summary (str): Concise 2-sentence summary of what the company does.
    - recent_milestones (List[str]): List of 0 to 2 recent company milestones.
    """
    pass

class PainPointItem(BaseModel):
    """
    TODO: Define specific prospect challenges and relevance details:
    - challenge (str): The strategic/operational issue.
    - why_it_matters (str): Impact on metrics/operations.
    """
    pass

class PainPointSchema(BaseModel):
    """
    TODO: Define strategic_pain_points (List[PainPointItem]).
    - Validate that the list contains exactly 3 pain points.
    """
    pass

class IcebreakerSchema(BaseModel):
    """
    TODO: Define icebreaker_questions (List[str]).
    - Validate that the list contains 2 to 3 questions.
    - Validate that each question ends with a question mark '?'.
    """
    pass

class HookPitchSchema(BaseModel):
    """
    TODO: Define cold hook and product pitch value propositions:
    - golden_hook (str): 30 words or less conversational B2B opener.
    - tailored_pitch (str): 3-to-4 sentence customized pitch.
    - Validate golden_hook word limit.
    """
    pass

class MetaSchema(BaseModel):
    """
    TODO: Define cache validation tracking details:
    - data_source (Literal['live', 'cached', 'database']): Origin source of data.
    - timestamp (str): UTC ISO 8601 generation timestamp.
    """
    pass

class FullPrepSheetSchema(BaseModel):
    """
    TODO: Aggregate all constituent schemas:
    - company_name (str): Domain query name.
    - job_title (str): Target prospect job title.
    - seller_product (str): Seller solution product details.
    - company_brief (CompanyBriefSchema)
    - pain_points (PainPointSchema)
    - icebreakers (IcebreakerSchema)
    - hook_pitch (HookPitchSchema)
    - meta (MetaSchema)
    """
    pass
