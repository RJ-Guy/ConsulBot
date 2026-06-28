import streamlit as st

# -------------------------------------------------------------
# 1. Page Configuration & Premium Aesthetics
# -------------------------------------------------------------
st.set_page_config(
    page_title="ConsulBot | B2B Call Prep Intelligence",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    
    /* Golden Hook Opener Card */
    .hook-card {
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.08) 0%, rgba(79, 172, 254, 0.08) 100%);
        border: 1.5px solid rgba(0, 242, 254, 0.35);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0, 242, 254, 0.1);
    }
    
    /* Tailored Pitch Card */
    .pitch-card {
        background: rgba(255, 255, 255, 0.03);
        border-left: 4px solid #00F2FE;
        border-radius: 4px 14px 14px 4px;
        padding: 24px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    
    /* Section Titles */
    .section-title {
        color: #00F2FE;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 12px;
        border-bottom: 1px solid rgba(0, 242, 254, 0.15);
        padding-bottom: 6px;
    }
    
    /* Metadata Badges */
    .badge-demo {
        background-color: rgba(0, 242, 254, 0.15);
        color: #00F2FE;
        border: 1px solid rgba(0, 242, 254, 0.3);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. Placeholder Data Models (UI Demo)
# -------------------------------------------------------------
DEFAULT_PLACEHOLDER = {
    "company_name": "stripe.com",
    "job_title": "VP of Customer Support",
    "seller_product": "AI Automated Escalation Platform",
    "golden_hook": "I noticed Stripe recently expanded Stripe Tax globally while processing over $1 Trillion in volume.",
    "company_summary": "Stripe provides financial infrastructure for internet commerce. Their software allows businesses of all sizes to accept payments and manage online operations seamlessly.",
    "milestones": [
        "Launched Stripe Tax across 50+ international jurisdictions to automate compliance.",
        "Secured strategic enterprise global partnerships to expand payment processing infra."
    ],
    "pain_points": [
        {
            "challenge": "High Weekend Support Escalation Volumes",
            "why_it_matters": "Spikes during non-business hours degrade customer SLA agreements and increase workforce burnout."
        },
        {
            "challenge": "Cross-Border Tax & Compliance Complexity",
            "why_it_matters": "Managing region-specific financial regulations manually scales operational overhead exponentially."
        },
        {
            "challenge": "Merchant Integration Downtime Disruptions",
            "why_it_matters": "API friction during checkout integrations directly impacts merchant conversion rates and revenue."
        }
    ],
    "icebreakers": [
        "How is your customer ops team managing SLA spikes during major holiday processing peaks?",
        "What strategies are you testing this quarter to streamline merchant onboarding compliance?"
    ],
    "tailored_pitch": "Our AI Automated Escalation Platform seamlessly integrates with Stripe's support workflow to resolve weekend ticket spikes automatically. By enforcing 15-minute response SLAs without expanding headcount, your core engineering teams can stay focused on API scaling.",
    "timestamp": "2026-06-27T22:45:00Z",
    "data_source": "LAYOUT DEMO (PLACEHOLDER)"
}

# Ensure robust Session State initialization across reruns
if "active_data" not in st.session_state:
    st.session_state["active_data"] = DEFAULT_PLACEHOLDER

# -------------------------------------------------------------
# 3. Sidebar Component Layout
# -------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.title("💼 Call Prep Input")
        st.caption("Generate tailored pre-call intelligence")
        
        with st.expander("📝 New Briefing Inputs", expanded=True):
            st.text_input(
                "Company Domain / URL", 
                value=st.session_state["active_data"]["company_name"], 
                placeholder="e.g. stripe.com",
                key="input_domain"
            )
            st.text_input(
                "Prospect Job Title", 
                value=st.session_state["active_data"]["job_title"], 
                placeholder="e.g. VP of Sales",
                key="input_role"
            )
            st.text_area(
                "Your Product / Solution", 
                value=st.session_state["active_data"]["seller_product"],
                height=100,
                key="input_product"
            )
            
            st.button("🚀 Generate Prep Sheet", type="primary", use_container_width=True, key="btn_generate")
            
        st.markdown("---")
        st.subheader("🗄️ Recent Briefings (History)")
        
        # Static placeholder history list
        mock_history = [
            {"company": "stripe.com", "role": "VP of Customer Support"},
            {"company": "vercel.com", "role": "Head of Infrastructure"},
            {"company": "snowflake.com", "role": "Director of Data Platform"}
        ]
        
        for item in mock_history:
            st.button(
                f"🏢 {item['company']} | 👤 {item['role']}", 
                key=f"hist_{item['company']}", 
                use_container_width=True
            )

# -------------------------------------------------------------
# 4. Main Layout & Display Containers
# -------------------------------------------------------------
def render_main_layout():
    data = st.session_state["active_data"]
    
    # Top Header Container
    header_col, meta_col = st.columns([3, 1])
    
    with header_col:
        st.title(f"Prep Sheet: {data['company_name']}")
        st.caption(f"Target Prospect: **{data['job_title']}** | Solution: *{data['seller_product']}*")
        
    with meta_col:
        st.markdown(
            f"<div style='text-align: right; margin-top: 15px;'>"
            f"<span class='badge-demo'>{data['data_source']}</span>"
            f"<div style='font-size: 0.75rem; color: #888; margin-top: 6px;'>{data['timestamp'][:19]} UTC</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        
    st.markdown("---")
    
    # 2-Column Main Dashboard Container
    left_col, right_col = st.columns([1, 1])
    
    with left_col:
        # Card 1: Golden Hook (Opener)
        st.markdown(
            f"<div class='hook-card'>"
            f"<div class='section-title'>💡 The Golden Hook (Cold Opener)</div>"
            f"<p style='font-size: 1.15rem; font-style: italic; font-weight: 500;'>\"{data['golden_hook']}\"</p>"
            f"</div>",
            unsafe_allow_html=True
        )
        
        # Card 2: Company Brief & Milestones
        milestones_html = "".join([f"<li>{m}</li>" for m in data['milestones']])
        st.markdown(
            f"<div class='glass-card'>"
            f"<div class='section-title'>🏢 Company Brief</div>"
            f"<p style='color: #CBD5E1; line-height: 1.6;'>{data['company_summary']}</p>"
            f"<h4 style='font-size: 0.95rem; color: #E2E8F0; margin-top: 16px; margin-bottom: 8px;'>Recent Milestones:</h4>"
            f"<ul style='color: #CBD5E1; padding-left: 20px; line-height: 1.5;'>{milestones_html}</ul>"
            f"</div>",
            unsafe_allow_html=True
        )
        
        # Action Container: Export Button
        placeholder_markdown = f"# Prep Sheet: {data['company_name']}\n\n## Hook\n{data['golden_hook']}"
        st.download_button(
            label="📥 Download Prep Sheet (Markdown)",
            data=placeholder_markdown,
            file_name=f"prep_sheet_{data['company_name'].replace('.', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
            key="btn_download"
        )

    with right_col:
        # Container 3: Strategic Pain Points
        st.markdown("<div class='section-title'>🎯 Strategic Pain Points</div>", unsafe_allow_html=True)
        for idx, item in enumerate(data['pain_points']):
            with st.expander(f"Challenge {idx+1}: {item['challenge']}", expanded=True):
                st.markdown(f"**Why it matters:** {item['why_it_matters']}")
                
        # Container 4: Icebreaker Questions
        st.markdown("<div class='section-title' style='margin-top: 24px;'>💬 Icebreaker Questions</div>", unsafe_allow_html=True)
        for q in data['icebreakers']:
            st.info(q)
            
        # Card 5: Tailored Pitch
        st.markdown(
            f"<div class='pitch-card'>"
            f"<div class='section-title'>📈 Suggested Pitch</div>"
            f"<p style='color: #CBD5E1; line-height: 1.6;'>{data['tailored_pitch']}</p>"
            f"</div>",
            unsafe_allow_html=True
        )

# -------------------------------------------------------------
# 5. Main Execution Entry Point
# -------------------------------------------------------------
def main():
    render_sidebar()
    render_main_layout()

if __name__ == "__main__":
    main()
