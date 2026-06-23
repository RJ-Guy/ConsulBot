# Frontend Implementation Plan: Sales Call Prep-Sheet Generator

This document provides a highly detailed, component-by-component frontend structure, custom CSS styling guides, and implementation instructions for the **ConsulBot Sales Call Prep-Sheet UI**. 

A frontend development agent should be able to read this file and build the user interface (`frontend/app/app.py`) and verify correctness using the isolation testing guide.

---

## 1. Directory Structure

The frontend code will reside in `frontend/app/app.py` and communicate directly with `backend/orchestrator.py`.

```text
ConsulBot/
├── Plan/
│   ├── backend_plan.md
│   └── frontend_plan.md              # This plan
├── backend/
│   ├── orchestrator.py               # Chained backend pipeline
│   ├── schemas.py                    # Data validation models
│   └── ...
├── frontend/
│   └── app/
│       └── app.py                    # Streamlit UI Entry Point
├── tests/
│   └── test_frontend.py              # UI Isolation test script
```



---

## 2. Design Aesthetics & Styling Guidelines

To ensure a premium, modern, and high-impact visual identity:
* **Color Palette**: Use dark background tones, glassmorphism card styles, and neon/pastel accents:
  - Background: Dark slate/grey (`#0E1117`)
  - Accent Primary: Electric Cyan/Blue (`#00F2FE` or `#1E90FF`)
  - Accent Success (Live data): Emerald Green (`#10B981`)
  - Accent Warning (Cached data): Amber Orange (`#F59E0B`)
* **Typography**: Ingest Google Fonts (e.g., *Inter* or *Outfit*) to replace default system fonts.
* **Layout Structure**: 
  - Left Sidebar or top-row grid for inputs.
  - Main panel displaying the generated prep-sheet with clean dividers, card containers, and highlighted badges.
  - Interactivity: Custom CSS hover states, copy buttons, and download indicators.

---

## 3. Streamlit Entry Point (`frontend/app/app.py`)

This file handles user input, binds to the async orchestrator pipeline, manages state persistence (to prevent re-runs from wiping results), and renders custom HTML/CSS cards.

```python
import streamlit as st
import asyncio
import datetime
from backend.orchestrator import generate_prep_sheet
from backend.schemas import FullPrepSheetSchema

# -------------------------------------------------------------
# 1. Page Configuration & Custom Premium Styling
# -------------------------------------------------------------
st.set_page_config(
    page_title="ConsulBot | B2B Call Prep Intelligence",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    /* Ingest Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Premium Glassmorphic Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    
    .hook-card {
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.08) 0%, rgba(79, 172, 254, 0.08) 100%);
        border: 1.5px solid rgba(0, 242, 254, 0.3);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
    }
    
    /* Headers & Accent Titles */
    .section-title {
        color: #00F2FE;
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: 12px;
        border-bottom: 1px solid rgba(0, 242, 254, 0.15);
        padding-bottom: 6px;
    }
    
    /* Metadata Badges */
    .badge-live {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .badge-cached {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    /* Pain Point Card Layout */
    .pain-point-title {
        color: #FF7597;
        font-weight: 600;
        margin-bottom: 4px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. Helper Functions
# -------------------------------------------------------------
def get_markdown_download_content(data: FullPrepSheetSchema) -> str:
    """Converts the structured Pydantic object into a clean Markdown document for export."""
    milestones_str = "\n".join([f"- {m}" for m in data.company_brief.recent_milestones])
    pain_points_str = "\n".join([
        f"### {idx+1}. {p.challenge}\n*Why it Matters:* {p.why_it_matters}" 
        for idx, p in enumerate(data.pain_points.strategic_pain_points)
    ])
    icebreakers_str = "\n".join([f"- {q}" for q in data.icebreakers.icebreaker_questions])
    
    return f"""# Sales Call Prep Sheet: {data.company_name}
**Prospect Job Title:** {data.job_title}
**Seller Product:** {data.seller_product}
**Generated At:** {data.meta.timestamp} (Source: {data.meta.data_source})

---

## 💡 The Golden Hook (Cold Opener)
> {data.hook_pitch.golden_hook}

---

## 🏢 Company Brief
{data.company_brief.short_summary}

### Recent Milestones
{milestones_str}

---

## 🎯 Inferred Pain Points
{pain_points_str}

---

## 💬 Icebreaker Questions
{icebreakers_str}

---

## 📈 Suggested Pitch
{data.hook_pitch.tailored_pitch}
"""

# -------------------------------------------------------------
# 3. Sidebar Input Interface
# -------------------------------------------------------------
st.sidebar.title("💼 Call Prep Input")
st.sidebar.markdown("Generate custom pre-call intelligence sheets in seconds.")

company_domain = st.sidebar.text_input(
    "Company Domain / URL", 
    value="stripe.com", 
    placeholder="e.g. stripe.com",
    help="Target business domain name."
)
job_title = st.sidebar.text_input(
    "Prospect Job Title", 
    value="VP of Customer Support", 
    placeholder="e.g. VP of Sales, Engineering Director"
)
seller_product = st.sidebar.text_area(
    "Your Product / Solution", 
    value="An AI agent platform that resolves customer support tickets during weekends.",
    placeholder="Describe what you are selling..."
)

# -------------------------------------------------------------
# 4. Action Trigger & Execution
# -------------------------------------------------------------
if st.sidebar.button("Generate Prep Sheet", type="primary", use_container_width=True):
    if not company_domain or not job_title or not seller_product:
        st.sidebar.error("All input fields are required!")
    else:
        with st.spinner("Analyzing domain and triggering sales agents..."):
            try:
                # Resolve the async orchestrator pipeline inside Streamlit's sync runtime
                result: FullPrepSheetSchema = asyncio.run(
                    generate_prep_sheet(
                        company_domain=company_domain,
                        job_title=job_title,
                        seller_product=seller_product
                    )
                )
                # Store the result in Streamlit Session State to prevent loss on re-runs
                st.session_state["prep_sheet_result"] = result
                st.success("Analysis complete!")
            except Exception as e:
                st.error(f"Error executing pipeline: {str(e)}")

# -------------------------------------------------------------
# 5. Output Panel Presentation
# -------------------------------------------------------------
if "prep_sheet_result" in st.session_state:
    data: FullPrepSheetSchema = st.session_state["prep_sheet_result"]
    
    # Title & Metadata Info
    col_title, col_meta = st.columns([3, 1])
    with col_title:
        st.title(f"Prep Sheet: {data.company_name}")
        st.caption(f"Prepared for Prospect Role: **{data.job_title}** | Pitched Solution: *{data.seller_product}*")
    
    with col_meta:
        badge_style = "badge-live" if data.meta.data_source == "live" else "badge-cached"
        st.markdown(
            f"<div style='text-align: right; margin-top: 15px;'>"
            f"<span class='{badge_style}'>{data.meta.data_source.upper()} DATA</span>"
            f"<div style='font-size: 0.75rem; color: grey; margin-top: 5px;'>{data.meta.timestamp[:19]} UTC</div>"
            f"</div>", 
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Grid Layout for Content
    left_column, right_column = st.columns([1, 1])
    
    with left_column:
        # A. The Golden Hook Card
        st.markdown(
            f"<div class='hook-card'>"
            f"<div class='section-title'>💡 The Golden Hook (Cold Opener)</div>"
            f"<p style='font-size: 1.15rem; font-style: italic; font-weight: 500;'>\"{data.hook_pitch.golden_hook}\"</p>"
            f"</div>",
            unsafe_allow_html=True
        )
        
        # B. Company Summary & Milestones
        milestones_html = "".join([f"<li>{m}</li>" for m in data.company_brief.recent_milestones])
        st.markdown(
            f"<div class='glass-card'>"
            f"<div class='section-title'>🏢 Company Brief</div>"
            f"<p>{data.company_brief.short_summary}</p>"
            f"<h4 style='font-size: 0.95rem; margin-top: 15px;'>Recent Milestones:</h4>"
            f"<ul>{milestones_html or '<li>No recent milestone listed.</li>'}</ul>"
            f"</div>",
            unsafe_allow_html=True
        )
        
        # C. Download / Export Actions
        markdown_text = get_markdown_download_content(data)
        st.download_button(
            label="📥 Download Prep Sheet (Markdown)",
            data=markdown_text,
            file_name=f"prep_sheet_{data.company_name.replace('.', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    with right_column:
        # D. Inferred Pain Points (Rendered as expanders for visual depth)
        st.markdown("<div class='section-title'>🎯 Strategic Pain Points</div>", unsafe_allow_html=True)
        for idx, p in enumerate(data.pain_points.strategic_pain_points):
            with st.expander(f"Challenge {idx+1}: {p.challenge}", expanded=True):
                st.markdown(f"**Why it matters:** {p.why_it_matters}")
        
        # E. Icebreakers
        st.markdown("<div class='section-title' style='margin-top: 25px;'>💬 Icebreaker Questions</div>", unsafe_allow_html=True)
        for q in data.icebreakers.icebreaker_questions:
            st.info(q)
            
        # F. Suggested Pitch
        st.markdown(
            f"<div class='glass-card' style='margin-top: 20px; border-left: 4px solid #00F2FE;'>"
            f"<div class='section-title'>📈 Suggested Pitch</div>"
            f"<p>{data.hook_pitch.tailored_pitch}</p>"
            f"</div>",
            unsafe_allow_html=True
        )
else:
    st.info("👈 Enter company credentials and click **'Generate Prep Sheet'** in the sidebar to begin.")
```

---

## 4. Step-by-Step Frontend Agent Directives

The frontend agent should follow this sequence to implement and test the UI.

1. **Verify Environment**: Make sure `streamlit` is active in the virtual environment.
2. **Implement app.py**: Initialize `frontend/app/app.py` with the Streamlit skeletons and custom CSS classes.
3. **Verify State Control**: Click inputs, collapse cards, and ensure that interacting with components (e.g. expanding cards) does not re-trigger backend agent calls.
4. **Link Backend**: Bind the button click to `asyncio.run(generate_prep_sheet(...))`.

---

## 5. UI Isolation & Rendering Test Script

The backend agent requires API keys, but the frontend layout can be tested entirely **offline** using mock data objects. 

Instruct the frontend agent to create `tests/test_frontend.py` to launch the UI with mock responses:

```python
"""
UI Isolation Test: Run via `streamlit run tests/test_frontend.py`
This allows testing all CSS styles, badges, columns, and downloads without calling LLMs.
"""
import sys
import os
import streamlit as st

# Inject workspace root into system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.schemas import (
    FullPrepSheetSchema, 
    CompanyBriefSchema, 
    PainPointSchema, 
    PainPointItem, 
    IcebreakerSchema, 
    HookPitchSchema, 
    MetaSchema
)

# Mock schema response objects matching validations
mock_sheet = FullPrepSheetSchema(
    company_name="stripe.com",
    job_title="VP of Customer Support",
    seller_product="ConsulBot automated scaling platform",
    company_brief=CompanyBriefSchema(
        short_summary="Stripe building financial software infrastructure for internet payment transactions.",
        recent_milestones=[
            "Stripe launched Stripe Tax globally to automate compliance.",
            "Stripe raised $6.5B in funding at a $50B valuation."
        ]
    ),
    pain_points=PainPointSchema(
        strategic_pain_points=[
            PainPointItem(challenge="High support volumes during weekends", why_it_matters="Degrades SLA responses and increases churn."),
            PainPointItem(challenge="Global compliance overhead", why_it_matters="Scaling teams manually to keep up with country-specific tax rules is expensive."),
            PainPointItem(challenge="API downtime integration errors", why_it_matters="Causes merchant payment disruption and brand damage.")
        ]
    ),
    icebreakers=IcebreakerSchema(
        icebreaker_questions=[
            "How does Stripe plan to expand Stripe Tax to support non-EU regions this quarter?",
            "What strategies is your support team using to mitigate ticket spikes during retail holidays?"
        ]
    ),
    hook_pitch=HookPitchSchema(
        golden_hook="I noticed Stripe recently raised $6.5B to build custom banking APIs.",
        tailored_pitch="ConsulBot fits into Stripe's infrastructure by automatically managing client ticket loads over the weekend. It ensures SLAs stay below 15 minutes, allowing engineering teams to focus strictly on API core updates."
    ),
    meta=MetaSchema(
        data_source="cached",
        timestamp="2026-06-23T21:55:00Z"
    )
)

# Save mock to session state to bypass backend processing
st.session_state["prep_sheet_result"] = mock_sheet

# Import and execute the UI script
import frontend.app.app as app
```

Run this command to check the visual rendering:
```bash
uv run streamlit run tests/test_frontend.py
```
This launches a local development server showcasing the premium glassmorphic UI, metadata badges, downloadable markdown files, and structured columns.
