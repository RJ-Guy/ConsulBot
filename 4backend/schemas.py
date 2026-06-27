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
        min_length=0,
        max_length=2,
        description="List of 0 to 2 recent company milestones or updates (e.g. fundraise, product launch)."
    )

class PainPointItem(BaseModel):
    challenge: str = Field(..., description="The specific strategic challenge faced by this prospect profile.")
    why_it_matters: str = Field(..., description="Details on why this challenge affects operations or revenue.")

class PainPointSchema(BaseModel):
    strategic_pain_points: List[PainPointItem] = Field(
        ..., 
        min_length=3,
        max_length=3,
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
        min_length=2,
        max_length=3,
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
