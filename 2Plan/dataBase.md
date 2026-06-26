🗄️ What Data You Should Store
To keep your app clean, fast, and secure, divide your data into two categories: User-Facing Data (so users can track their history) and System Caching Data (to avoid paying for duplicate API calls).

1. The Sales Teams / Users (Optional but looks great to judges)
Why: Allows you to demonstrate basic authentication or tracking of which sales representative generated which cheat sheets.

2. Generated Prep-Sheets (History & Cache)
Why: If a salesperson prepares a dossier for "Stripe" on Friday, they shouldn't have to wait 10 seconds and burn Gemini tokens to see the exact same analysis on Saturday. Storing the structured JSON results lets you build a "Recent Briefings" sidebar history panel.

3. The Company Scraping Logs
Why: To store the clean Markdown text fetched by Jina Reader. If the scraper succeeds once, lock it in your database!

📐 The Ideal Database Schema (SQL Blueprint)
You can copy and paste this relational SQL layout directly into the Supabase SQL Editor dashboard to spin up your tables instantly:

-- 1. Create a table to track companies we have researched and cache their scraped markdown context
CREATE TABLE company_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL UNIQUE,
    company_url TEXT,
    scraped_markdown TEXT,  -- The raw text fetched from Jina Reader
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create a table to store the final generated AI sales dossiers
CREATE TABLE sales_prep_sheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES company_profiles(id) ON DELETE CASCADE,
    target_role TEXT NOT NULL,           -- e.g., "VP of Customer Operations"
    my_product_pitch TEXT NOT NULL,       -- e.g., "AI Chatbot System"
    
    -- We save the entire structured output as JSONB 
    -- This stores the company summary, 3 challenges, and the golden hook perfectly
    ai_generated_payload JSONB NOT NULL, 
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

🔄 The Smart Workflow Pipeline (With Caching Logic)
When a user clicks "Generate" in your Streamlit application, your backend code should follow this efficient pattern to save time and API costs:

[User Input] 
     │
     ▼
Check DB: Does this Company + Role exist in history?
     ├──> YES: Fetch stored JSON from DB instantly (0.1s response!)
     │
     └──> NO: Run Scraper ──> Call Gemini API ──> Save JSON to DB ──> Render to Screen

Why this structure wins points with judges:
Speed: Your app will feel incredibly fast for any repeating search queries because it skips the LLM call entirely and reads the stored JSON from Postgres.

Architecture Depth: It proves to the judges that you aren't just calling raw APIs inline; you understand how to design a sustainable data lifecycle for a real enterprise software system.