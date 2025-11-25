# RecruitPro - AI Prompts Documentation

**Version:** 1.0
**Date:** November 25, 2025
**Purpose:** Complete documentation of all AI prompts used in RecruitPro

---

## Table of Contents

1. [Overview](#overview)
2. [CV Screening Prompts](#cv-screening-prompts)
3. [Document Analysis Prompts](#document-analysis-prompts)
4. [Job Description Generation](#job-description-generation)
5. [Outreach Email Generation](#outreach-email-generation)
6. [Call Script Generation](#call-script-generation)
7. [Market Research Prompts](#market-research-prompts)
8. [Salary Benchmarking](#salary-benchmarking)
9. [Candidate Scoring](#candidate-scoring)
10. [Chatbot Assistant](#chatbot-assistant)
11. [Verbal Screening Scripts](#verbal-screening-scripts)
12. [Prompt Engineering Techniques](#prompt-engineering-techniques)

---

## Overview

RecruitPro uses Google Gemini AI API (gemini-2.5-flash-lite) with structured prompts for all AI-powered features. Every prompt includes:

- **System instruction**: Defines AI role and behavior
- **User prompt**: Specific task with context
- **Output schema**: Expected JSON structure
- **Fallback logic**: Deterministic responses when AI unavailable

**Configuration**:
- Model: `gemini-2.5-flash-lite`
- Temperature: `0.15` (low for consistency)
- Base URL: `https://generativelanguage.googleapis.com/v1beta`
- Timeout: 30 seconds
- Retry: 3 attempts with exponential backoff

---

## CV Screening Prompts

### System Instruction

```
{
  "role": "Senior Talent Acquisition Partner for Egis Middle East & North America",
  "specialization": "Screening CVs for construction, engineering, project management, aviation, rail, buildings, and infrastructure roles within large capital programs",
  "tone": "Professional, efficient, analytical, and evidence-based",
  "compliance_rules": [
    "Read and analyze the entire CV — all pages, all sections, all appendices",
    "No truncation - use 100% of available CV content",
    "All statements must be grounded in the CV or provided context",
    "No fabricated or speculative data",
    "Use objective, factual, and professional tone"
  ]
}
```

### User Prompt Structure

```
=== FULL CV TEXT (NO TRUNCATION) ===
{full_cv_text}

=== JOB DESCRIPTION (JD) ===
Position: {position_title}
Department: {department}
Location: {location}
Experience Required: {experience_level}

Description:
{position_description}

Qualifications:
{qualifications_list}

Responsibilities:
{responsibilities_list}

Requirements (Must-Have):
{requirements_list}

=== YOUR TASK ===
Conduct a comprehensive, evidence-based CV screening for the above position.

IMPORTANT COMPLIANCE RULES:
1. READ THE ENTIRE CV - Do not truncate or skip any content
2. Extract ALL must-have requirements from the JD
3. For EACH requirement, classify compliance status:
   - ✅ Complying: requirement fully met with explicit CV evidence
   - ❌ Not Complying: requirement not met or contradicted
   - ⚠️ Not Mentioned / Cannot Confirm: CV lacks evidence

4. Provide specific CV evidence for every compliance assessment
5. Generate 4 key strengths and 2 potential gaps
6. Make final decision: Proceed to technical interview / Suitable for lower role / Reject

OUTPUT MUST MATCH THIS JSON SCHEMA:
{
  "candidate": {
    "name": "string (REQUIRED - extract from CV)",
    "email": "string or null",
    "phone": "string or null"
  },
  "table_1_screening_summary": {
    "overall_fit": "Strong Match | Potential Match | Low Match",
    "recommended_roles": ["string"],
    "key_strengths": ["string - exactly 4 items"],
    "potential_gaps": ["string - exactly 2 items"],
    "notice_period": "string"
  },
  "table_2_compliance": [
    {
      "requirement_category": "Education | Total Experience | Sector/Domain | Canadian Experience | Technical Skills | Software | Certifications | Stakeholder Engagement | Communication Skills | Mobility/Relocation",
      "requirement_description": "string - Detailed description from JD",
      "compliance_status": "✅ Complying | ❌ Not Complying | ⚠️ Not Mentioned / Cannot Confirm",
      "evidence": "string - Specific evidence from CV with page/section reference"
    }
  ],
  "final_recommendation": {
    "summary": "string - 3-4 sentence summary of overall assessment",
    "decision": "Proceed to technical interview | Suitable for a lower-grade role | Reject",
    "justification": "string - Clear justification based on compliance analysis"
  },
  "record_management": {
    "screened_at_utc": "ISO-8601 datetime string",
    "screened_by": "Senior Talent Acquisition Partner",
    "tags": ["string - relevant tags like 'strong-technical', 'leadership-ready', etc."]
  }
}
```

### Example Output

```json
{
  "candidate": {
    "name": "John Smith",
    "email": "john.smith@email.com",
    "phone": "+1-555-0123"
  },
  "table_1_screening_summary": {
    "overall_fit": "Strong Match",
    "recommended_roles": ["Senior Project Manager", "PMO Lead"],
    "key_strengths": [
      "15+ years progressive experience in mega infrastructure projects across GCC region",
      "Proven track record delivering $2B+ programmes on time and within budget",
      "Strong stakeholder management with C-suite and government entities",
      "PMP, P3O certified with deep PMO methodology expertise"
    ],
    "potential_gaps": [
      "Limited direct experience with aviation sector (primarily rail and roads)",
      "No explicit mention of BIM coordination workflows"
    ],
    "notice_period": "3 months (negotiable)"
  },
  "table_2_compliance": [
    {
      "requirement_category": "Total Experience",
      "requirement_description": "Minimum 10 years in large-scale infrastructure delivery",
      "compliance_status": "✅ Complying",
      "evidence": "CV shows 15 years total experience including Dubai Metro Extension (2018-2023, $1.8B) and Saudi Rail Network (2014-2018, $3.2B)"
    },
    {
      "requirement_category": "Sector/Domain",
      "requirement_description": "Aviation or rail mega-projects experience",
      "compliance_status": "⚠️ Not Mentioned / Cannot Confirm",
      "evidence": "CV demonstrates strong rail experience but no explicit aviation projects mentioned"
    },
    {
      "requirement_category": "Certifications",
      "requirement_description": "PMP or Prince2 certification",
      "compliance_status": "✅ Complying",
      "evidence": "PMP certified 2015, P3O Practitioner 2017 (CV page 1, Certifications section)"
    }
  ],
  "final_recommendation": {
    "summary": "John Smith is a strong match for Senior Project Manager with extensive GCC mega-project experience, proven PMO leadership, and robust stakeholder management credentials. While aviation-specific experience is limited, his transferable rail infrastructure expertise and commercial acumen make him well-suited for cross-sector delivery roles.",
    "decision": "Proceed to technical interview",
    "justification": "Candidate meets 9/11 must-have requirements with strong evidence. Two gaps (aviation sector, BIM) are mitigable given depth of parallel infrastructure experience and certifications. Recommended for technical panel to assess sector transferability."
  },
  "record_management": {
    "screened_at_utc": "2025-11-25T14:30:00Z",
    "screened_by": "Senior Talent Acquisition Partner",
    "tags": ["strong-technical", "gcc-experience", "pmo-lead", "mega-project"]
  }
}
```

### Fallback Logic (When AI Unavailable)

```python
def _fallback_screen_cv(cv_text: str, position_requirements: dict) -> dict:
    """Heuristic-based CV screening when Gemini unavailable"""

    # Extract basic information
    name = extract_name_from_cv(cv_text)
    email = extract_email_from_cv(cv_text)
    phone = extract_phone_from_cv(cv_text)

    # Calculate experience years
    years_exp = estimate_years_experience(cv_text)

    # Count skill matches
    required_skills = position_requirements.get("requirements", [])
    skills_found = count_skill_matches(cv_text, required_skills)

    # Determine overall fit
    if skills_found >= len(required_skills) * 0.7 and years_exp >= 10:
        overall_fit = "Strong Match"
        decision = "Proceed to technical interview"
    elif skills_found >= len(required_skills) * 0.5:
        overall_fit = "Potential Match"
        decision = "Suitable for a lower-grade role"
    else:
        overall_fit = "Low Match"
        decision = "Reject"

    return {
        "candidate": {"name": name, "email": email, "phone": phone},
        "table_1_screening_summary": {
            "overall_fit": overall_fit,
            "recommended_roles": [position_requirements.get("title", "Unknown")],
            "key_strengths": [
                f"Approximately {years_exp} years of relevant experience",
                f"{skills_found}/{len(required_skills)} required skills identified",
                "Further manual review recommended",
                "CV contains relevant keywords"
            ],
            "potential_gaps": [
                "Detailed analysis requires AI service",
                "Manual screening recommended for accuracy"
            ],
            "notice_period": "Not specified"
        },
        "table_2_compliance": [],
        "final_recommendation": {
            "summary": "Automated screening completed. Manual review recommended for detailed assessment.",
            "decision": decision,
            "justification": "Fallback heuristic analysis based on keyword matching and experience estimation."
        },
        "record_management": {
            "screened_at_utc": datetime.utcnow().isoformat(),
            "screened_by": "Automated Screening (Fallback Mode)",
            "tags": ["fallback-screening", "requires-manual-review"]
        }
    }
```

---

## Document Analysis Prompts

### System Instruction

```
You are a document analysis assistant for RecruitPro. Extract only information explicitly present in documents. Do not infer or invent data. Return valid JSON only matching the RecruitPro Standard schema.
```

### User Prompt

```
=== DOCUMENT TEXT ===
{document_content}

=== YOUR TASK ===
Analyze the provided document and return structured project and job information.

The document may be:
• a project scope/summary
• a single job description
• a list of multiple job descriptions
• a mix of project scope and one or more job descriptions

You must:
1. Correctly classify the document type
2. Extract project_info if project details exist
3. Extract all positions if any job descriptions exist

EXTRACTION RULES:
• Do NOT infer missing data
• Extract information exactly as written
• If tables exist, parse them carefully
• Preserve structure (lists, bullet points)
• Identify sector keywords: infrastructure, aviation, rail, energy, buildings, healthcare
• Valid job titles only (filter out headers like "Position List")

OUTPUT SCHEMA:
{
  "document_type": "project_scope | job_description | positions_list | mixed | general",
  "project_info": {
    "name": "string|null",
    "summary": "string|null",
    "scope_of_work": "string|null",
    "client": "string|null",
    "sector": "string|null",
    "location_region": "string|null"
  },
  "positions": [
    {
      "title": "string (REQUIRED)",
      "department": "string|null",
      "experience": "entry|mid|senior|executive",
      "qualifications": ["string"],
      "description": "string|null",
      "responsibilities": ["string"],
      "requirements": ["string"],
      "location": "string|null"
    }
  ]
}
```

### Example Output

```json
{
  "document_type": "mixed",
  "project_info": {
    "name": "Dubai Metro Blue Line Extension",
    "summary": "Design and construction of 15km automated metro extension connecting Dubai Marina to Jebel Ali Port",
    "scope_of_work": "Full EPCM delivery including civil works, systems integration, station architecture, and commissioning",
    "client": "Roads and Transport Authority (RTA)",
    "sector": "rail",
    "location_region": "GCC"
  },
  "positions": [
    {
      "title": "Senior Project Manager",
      "department": "Project Management Office",
      "experience": "senior",
      "qualifications": [
        "Bachelor's degree in Civil Engineering or related field",
        "PMP or equivalent certification",
        "15+ years in rail or metro projects"
      ],
      "description": "Lead the delivery of metro extension programme ensuring schedule, budget, quality, and safety compliance",
      "responsibilities": [
        "Overall programme governance and client interface",
        "Manage multidisciplinary teams (200+ staff)",
        "Risk and opportunity management",
        "Monthly progress reporting to steering committee"
      ],
      "requirements": [
        "GCC metro/rail experience mandatory",
        "Proven track record on $500M+ capital projects",
        "Strong stakeholder management with government entities"
      ],
      "location": "Dubai, UAE"
    }
  ]
}
```

### Fallback Logic

```python
def _fallback_analyze_file(document_text: str) -> dict:
    """Heuristic document analysis when AI unavailable"""

    # Classify document type
    doc_type = "general"
    if "scope of work" in document_text.lower():
        doc_type = "project_scope"
    elif "job description" in document_text.lower():
        doc_type = "job_description"

    # Extract project info keywords
    project_info = {
        "name": extract_project_name(document_text),
        "summary": extract_first_paragraph(document_text),
        "scope_of_work": None,
        "client": extract_client_keyword(document_text),
        "sector": detect_sector_keyword(document_text),
        "location_region": extract_location(document_text)
    }

    # Extract positions
    positions = extract_job_titles_heuristic(document_text)

    return {
        "document_type": doc_type,
        "project_info": project_info,
        "positions": positions
    }
```

---

## Job Description Generation

### System Instruction

```
Respond with valid JSON only.
```

### User Prompt

```
Generate a RecruitPro job description as JSON with keys:
['title', 'summary', 'description', 'responsibilities', 'requirements', 'nice_to_have', 'compensation_note']

Use the following context:
{
  "title": "Senior Design Manager",
  "project_summary": "Abu Dhabi International Airport Terminal 5 expansion",
  "responsibilities": ["Lead architectural coordination", "Manage design consultants"],
  "requirements": ["15+ years aviation architecture", "RIBA chartered"],
  "nice_to_have": ["BIM management experience", "LEED AP certification"],
  "salary_hint": "Competitive GCC package with housing and relocation"
}

Create a compelling, professional job description suitable for executive search.
```

### Example Output

```json
{
  "title": "Senior Design Manager",
  "summary": "Egis is seeking a Senior Design Manager to lead architectural coordination for the Abu Dhabi International Airport Terminal 5 expansion, a landmark aviation infrastructure programme.",
  "description": "This role demands exceptional design leadership, stakeholder management, and technical expertise to deliver world-class airport architecture within a fast-paced, collaborative environment.",
  "responsibilities": [
    "Lead architectural coordination across multidisciplinary design teams",
    "Manage design consultants ensuring deliverable quality and programme alignment",
    "Interface with client, authority, and contractor stakeholders",
    "Ensure design compliance with aviation standards and local codes",
    "Drive design innovation and value engineering initiatives"
  ],
  "requirements": [
    "15+ years progressive experience in aviation architecture",
    "RIBA chartered or equivalent professional qualification",
    "Proven track record on airport terminal projects $1B+",
    "Strong leadership and communication skills",
    "GCC experience highly preferred"
  ],
  "nice_to_have": [
    "BIM management experience (Revit, Navisworks)",
    "LEED AP certification or sustainability credentials",
    "Experience with FIDIC contracts",
    "Arabic language proficiency"
  ],
  "compensation_note": "Competitive GCC package including tax-free salary, housing allowance, annual flights, medical insurance, and relocation support."
}
```

### Fallback Template

```python
def _fallback_generate_jd(context: dict) -> dict:
    """Template-based JD generation"""
    title = context.get("title", "Position")
    project_summary = context.get("project_summary", "a flagship programme")

    return {
        "title": title,
        "summary": f"Egis is seeking a {title} to accelerate delivery of {project_summary} with a focus on operational excellence, innovation and sustainable outcomes.",
        "description": f"This role requires deep technical expertise, stakeholder fluency, and a proven ability to deliver complex infrastructure programmes on time and within budget.",
        "responsibilities": context.get("responsibilities", [
            "Lead technical delivery across the programme lifecycle",
            "Manage multidisciplinary teams and external consultants",
            "Interface with client and authority stakeholders",
            "Drive innovation and continuous improvement initiatives"
        ]),
        "requirements": context.get("requirements", [
            "10+ years experience in large-scale infrastructure projects",
            "Chartered or working towards chartership",
            "Proven stakeholder management across consultants and contractors",
            "Strong commercial and contractual acumen"
        ]),
        "nice_to_have": context.get("nice_to_have", [
            "GCC or international project experience",
            "Advanced degree (MSc, MBA)",
            "Proficiency in digital delivery tools (BIM, P6, Power BI)"
        ]),
        "compensation_note": context.get("salary_hint", "Competitive package aligned with market benchmarks and candidate experience.")
    }
```

---

## Outreach Email Generation

### System Instruction

```
Return valid JSON only.
```

### User Prompt

```
Create an outreach email for a candidate. Respond as JSON with keys 'subject' and 'body'.

Context:
{
  "candidate_name": "Sarah Johnson",
  "title": "Senior Project Manager",
  "company": "Egis",
  "template": "standard",
  "highlights": [
    "Tier-one infrastructure programme in Abu Dhabi",
    "Leadership role with commercial autonomy",
    "Competitive GCC package with housing"
  ]
}
```

### Example Outputs

**Standard Template:**
```json
{
  "subject": "Opportunity: Senior Project Manager | Tier-one infrastructure programme",
  "body": "Hi Sarah,\n\nI'm leading a search at Egis for a Senior Project Manager and your profile stood out. We're assembling a taskforce that blends technical mastery with collaborative leadership.\n\nHighlights:\n• Tier-one infrastructure programme in Abu Dhabi\n• Leadership role with commercial autonomy\n• Competitive GCC package with housing\n\nCould we schedule a 15 minute call this week to explore the fit?\n\nBest regards,\nEgis Talent"
}
```

**Executive Template:**
```json
{
  "subject": "Leadership opportunity | Senior Project Manager | Egis",
  "body": "Hello Sarah,\n\nEgis is mobilising a leadership team for a flagship programme and your track record aligns closely with what we're building.\n\nKey details:\n• Tier-one infrastructure programme in Abu Dhabi\n• Leadership role with commercial autonomy\n• Competitive GCC package with housing\n\nLet's find time to connect over the next few days.\n\nWarm regards,\nEgis Executive Talent"
}
```

**Technical Template:**
```json
{
  "subject": "Technical leadership | Senior Project Manager | Egis",
  "body": "Hi Sarah,\n\nWe're standing up a delivery pod focused on advanced engineering workflows and your contributions caught our attention.\n\nWhy this matters:\n• Tier-one infrastructure programme in Abu Dhabi\n• Leadership role with commercial autonomy\n• Competitive GCC package with housing\n\nWould you be open to a short conversation?\n\nThanks,\nEgis Talent"
}
```

---

## Call Script Generation

### System Instruction

```
Return valid JSON only.
```

### User Prompt

```
Draft a structured call script for a recruiter. Return JSON including candidate, role, location, value_props (list) and sections (object).

Context:
{
  "candidate_name": "Michael Chen",
  "title": "Lead Civil Engineer",
  "location": "Dubai, UAE",
  "project": "Dubai Metro Blue Line Extension"
}
```

### Example Output

```json
{
  "candidate": "Michael Chen",
  "role": "Lead Civil Engineer",
  "location": "Dubai, UAE",
  "value_props": [
    "Tier-one metro infrastructure programme",
    "Empowered technical decision making",
    "Leadership succession planning pathway"
  ],
  "sections": {
    "introduction": "Hi Michael, it's great to connect. I'm Abdulla Nigil from Egis, leading talent acquisition for the North America and Middle East regions. Thanks for making time today.",
    "context": "We're partnering with RTA to deliver the Dubai Metro Blue Line Extension — 15km automated metro with 12 new stations. The programme is mobilising now and we're building a senior technical leadership team.",
    "motivation": [
      "What would prompt you to explore a new role right now?",
      "How do you evaluate opportunities in terms of scale and autonomy?"
    ],
    "technical": [
      "Walk me through a recent project where you had to resolve a major civil engineering challenge.",
      "How do you lead design coordination with remote partners or subconsultants?"
    ],
    "managerial": [
      "How large were the teams you led and how were they structured?",
      "Tell me about your stakeholder management cadence — who do you typically interface with?"
    ],
    "commercial": [
      "What financial levers do you monitor most closely during delivery?",
      "Describe a time you protected margin without compromising quality or safety."
    ],
    "objection_handling": [
      {
        "objection": "Timing isn't right",
        "response": "We can align interviews around your availability, including after-hours. The opportunity will remain open for the right candidate."
      },
      {
        "objection": "Relocation concerns",
        "response": "We provide full mobilisation support including family assistance, schooling support, housing allowance, and settling-in budget."
      }
    ],
    "closing": "I'd love to continue the conversation with our Technical Director. Are you open to a technical discussion next week? I'll coordinate timing and send a calendar invite. Really appreciate your time today, Michael."
  }
}
```

---

## Market Research Prompts

### System Instruction

```
Return valid JSON only.
```

### User Prompt

```
Generate market research insights as JSON with keys:
['region', 'sector', 'summary', 'findings', 'sources']

Context:
{
  "region": "GCC",
  "sector": "aviation",
  "summary": "Airport expansion programme requiring multidisciplinary delivery partners"
}
```

### Example Output

```json
{
  "region": "GCC",
  "sector": "aviation",
  "summary": "Airport expansion programme requiring multidisciplinary delivery partners",
  "findings": [
    {
      "title": "GCC flagship aviation initiatives",
      "description": "Comparable mega-projects include Abu Dhabi Terminal 5 ($3B), Doha Hamad expansion ($6B), and Riyadh King Salman Airport ($35B). All delivered under FIDIC contracts with collaborative PMC models.",
      "leads": [
        "PMC: Parsons, AECOM, Jacobs",
        "Consultant: Arup, Dar, Egis",
        "Contractor: Al Naboodah, Arabtec, CCC"
      ]
    },
    {
      "title": "Talent availability snapshot",
      "description": "Regional supply constrained at Principal+ levels due to concurrent mega-projects. Compelling EVP and mobility support critical for securing top talent.",
      "leads": [
        "Leverage mega-project alumni networks",
        "Promote long-term career progression",
        "Offer competitive GCC packages with housing"
      ]
    },
    {
      "title": "Market dynamics",
      "description": "Aviation sector growth driven by Vision 2030 initiatives, tourism expansion, and logistics hub ambitions. Technical roles in aviation systems and MEP coordination particularly scarce.",
      "leads": [
        "Consider international talent with GCC willingness",
        "Upskill mid-level engineers through mentorship",
        "Partner with academic institutions for early careers"
      ]
    }
  ],
  "sources": [
    {
      "title": "GCC Aviation Infrastructure Digest 2024",
      "url": "https://insights.egis/gcc/aviation"
    },
    {
      "title": "World Construction Network",
      "url": "https://www.worldconstructionnetwork.com"
    },
    {
      "title": "Middle East Economic Digest (MEED)",
      "url": "https://www.meed.com"
    }
  ]
}
```

---

## Salary Benchmarking

### System Instruction

```
Return valid JSON only.
```

### User Prompt

```
Provide a salary benchmark as JSON with keys:
['currency', 'annual_min', 'annual_mid', 'annual_max', 'rationale', 'sources']

Context:
{
  "title": "Senior Project Manager",
  "region": "GCC",
  "sector": "infrastructure",
  "seniority": "senior",
  "currency": "USD"
}
```

### Example Output

```json
{
  "currency": "USD",
  "annual_min": 125000,
  "annual_mid": 155000,
  "annual_max": 185000,
  "rationale": "Market benchmark for senior Senior Project Manager in GCC infrastructure sector. Base calculation: $105,000 (manager base) × 1.30 (senior multiplier) × 1.25 (GCC cost-of-living) × 1.15 (infrastructure complexity) = $196,331. Adjusted to market range based on recent placements and competitor data. GCC packages typically tax-free with housing, flights, medical included.",
  "sources": [
    {
      "title": "Glassdoor Salary Data",
      "url": "https://www.glassdoor.com"
    },
    {
      "title": "PayScale Industry Reports",
      "url": "https://www.payscale.com"
    },
    {
      "title": "Robert Half Salary Guide",
      "url": "https://www.roberthalf.com/salary-guide"
    },
    {
      "title": "Hays GCC Salary Survey 2024",
      "url": "https://www.hays.com/gcc-salary-guide"
    }
  ]
}
```

### Fallback Calculation Engine

```python
# Base role salaries (USD, annual)
BASE_SALARIES = {
    "engineer": 85000,
    "manager": 105000,
    "director": 145000,
    "specialist": 75000,
    "coordinator": 65000,
    "analyst": 70000,
    "architect": 90000,
    "consultant": 95000,
    "lead": 110000,
    "executive": 175000
}

# Seniority multipliers
SENIORITY_MULTIPLIERS = {
    "junior": 0.70,
    "mid": 1.0,
    "senior": 1.30,
    "principal": 1.50,
    "director": 1.65,
    "vp": 1.85,
    "c-level": 2.20
}

# Regional cost-of-living adjustments
REGIONAL_ADJUSTMENTS = {
    "gcc": 1.25,  # Tax-free, expat packages
    "uae": 1.30,
    "saudi": 1.25,
    "qatar": 1.28,
    "us": 1.15,
    "uk": 1.05,
    "europe": 1.00,
    "asia": 0.85,
    "australia": 1.10
}

# Sector complexity adjustments
SECTOR_ADJUSTMENTS = {
    "infrastructure": 1.15,
    "aviation": 1.20,
    "rail": 1.15,
    "energy": 1.25,
    "healthcare": 1.10,
    "buildings": 1.00
}

def calculate_salary_benchmark(title, region, sector, seniority):
    # Detect base role from title
    base_role = detect_base_role(title)  # "manager"
    base_salary = BASE_SALARIES.get(base_role, 85000)

    # Apply multipliers
    seniority_mult = SENIORITY_MULTIPLIERS.get(seniority, 1.0)
    regional_mult = REGIONAL_ADJUSTMENTS.get(region.lower(), 1.0)
    sector_mult = SECTOR_ADJUSTMENTS.get(sector.lower(), 1.0)

    # Calculate midpoint
    annual_mid = base_salary * seniority_mult * regional_mult * sector_mult

    # Calculate range (±20%)
    annual_min = int(annual_mid * 0.80)
    annual_max = int(annual_mid * 1.20)
    annual_mid = int(annual_mid)

    return {
        "annual_min": annual_min,
        "annual_mid": annual_mid,
        "annual_max": annual_max
    }
```

---

## Candidate Scoring

### System Instruction

```
Return valid JSON only.
```

### User Prompt

```
Score a candidate for RecruitPro. Return JSON with keys:
technical_fit, cultural_alignment, growth_potential, match_score, notes (list)

Context:
{
  "skills": ["PMO", "Stakeholder Management", "Risk Management", "P6", "BIM"],
  "years_experience": 12,
  "leadership": true
}
```

### Example Output

```json
{
  "technical_fit": 0.85,
  "cultural_alignment": 0.80,
  "growth_potential": 0.75,
  "match_score": 0.80,
  "notes": [
    "Strong PMO and stakeholder management credentials",
    "12 years experience demonstrates seasoned professional",
    "Leadership background aligns with senior role expectations",
    "BIM and P6 proficiency indicate digital delivery readiness",
    "Consider deep dive on international mobility and GCC adaptability"
  ]
}
```

### Fallback Scoring Logic

```python
def fallback_score_candidate(skills, years_experience, leadership):
    # Initialize scores
    technical = 0.5
    cultural = 0.5
    growth = 0.5

    # Skill bonuses (each premium skill +0.1)
    premium_skills = {"bim", "pmc", "design management", "pmp", "p6", "fidic"}
    for skill in skills:
        if skill.lower() in premium_skills:
            technical += 0.1

    # Experience bonus
    if years_experience > 10:
        technical += 0.2
        growth += 0.1
    elif years_experience > 5:
        technical += 0.1

    # Leadership bonus
    if leadership:
        cultural += 0.2
        growth += 0.1

    # Cap scores at 1.0
    technical = min(technical, 1.0)
    cultural = min(cultural, 1.0)
    growth = min(growth, 1.0)

    # Calculate match score (weighted average)
    match_score = (technical * 0.4 + cultural * 0.3 + growth * 0.3)

    return {
        "technical_fit": round(technical, 2),
        "cultural_alignment": round(cultural, 2),
        "growth_potential": round(growth, 2),
        "match_score": round(match_score, 2),
        "notes": [
            f"Candidate has {years_experience} years of experience.",
            f"Identified {len(skills)} relevant skills.",
            "Leadership experience noted." if leadership else "Consider leadership potential.",
            "Recommend technical screening for detailed assessment."
        ]
    }
```

---

## Chatbot Assistant

### System Instruction

```
Return valid JSON only.
```

### User Prompt

```
You are the RecruitPro assistant. Provide a helpful reply in JSON with keys 'reply' and 'context_echo'.

Conversation:
{
  "history": [
    {"role": "user", "content": "What's the status of my Dubai Metro project?"},
    {"role": "assistant", "content": "The Dubai Metro Blue Line Extension has 3 open positions with 12 active candidates in screening."}
  ],
  "message": "Can you launch a sourcing job for Senior Civil Engineers?"
}
```

### Example Output

```json
{
  "reply": "I'll prepare a sourcing job for Senior Civil Engineers on the Dubai Metro Blue Line Extension project. \n\nTo get started, I need:\n1. Position ID (or I can create a new position)\n2. Key skills/keywords for the search\n3. Target location (Dubai, or broader GCC?)\n4. Seniority level (Senior, Principal, Lead?)\n\nOnce you provide these details, I'll generate a LinkedIn X-Ray search string and launch the sourcing job.",
  "context_echo": "User inquiring about sourcing Senior Civil Engineers for Dubai Metro project."
}
```

### Intent-Based Fallback Responses

```python
INTENT_RESPONSES = {
    "market_research": "I'll prepare a market analysis pack. Provide the project ID or region/sector details, and I'll generate insights on talent availability, comparable projects, and salary benchmarks.",

    "sourcing": "Happy to start sourcing. Share the position ID plus keywords (skills, certifications, job titles), and I'll build a boolean search and launch LinkedIn X-Ray or SmartRecruiters import.",

    "status": "Current status: we have {project_count} active projects with {position_count} open positions and {candidate_count} candidates in various stages. {interview_count} interviews scheduled this week.",

    "salary": "I can provide salary benchmarks. Share the role title, region, sector, and seniority level, and I'll generate a compensation range with market sources.",

    "help": "Here's what I can help with:\n1. Summarise candidate pipeline and project status\n2. Launch AI-powered sourcing jobs (LinkedIn, SmartRecruiters)\n3. Generate market research and salary benchmarks\n4. Screen CVs against job descriptions\n5. Create outreach emails and call scripts\n\nJust let me know which workflow to trigger!"
}

def detect_intent(message: str) -> str:
    """Detect user intent from message"""
    message_lower = message.lower()

    for intent, keywords in [
        ("status", ("status", "update", "progress", "pipeline")),
        ("market_research", ("market research", "market analysis", "research pack")),
        ("sourcing", ("sourcing", "boolean", "talent map", "source candidates")),
        ("salary", ("salary", "compensation", "benchmark", "pay range")),
        ("help", ("help", "what can you do", "capabilities"))
    ]:
        if any(keyword in message_lower for keyword in keywords):
            return intent

    return "general"
```

---

## Verbal Screening Scripts

### System Instruction

```
ROLE & GOAL

Persona:
Act as a Senior Talent Acquisition Partner conducting insight-driven, conversational, candidate-centric screening calls. You never ask candidates to repeat what's already in the CV — you probe for depth, behaviour, ownership, decisions, impact, and motivation.

Primary Goal:
Generate a complete, structured, conversational 20–30 minute verbal screening script tailored to the JD, CV, role seniority, and leadership expectations. The script must support a strong, evidence-based submission report.
```

### User Prompt Structure

```
Generate a verbal screening script for:

CANDIDATE: {candidate_name}
POSITION: {position_title}
SENIORITY: {seniority_level}
LEADERSHIP SCOPE: {leadership_scope}

JOB DESCRIPTION:
{full_jd_text}

CV SUMMARY:
{cv_highlights}

Create a structured 20-30 minute screening script with 8 sections:
1. Introduction, Purpose & Job Overview (3-4 mins)
2. Core Experience & JD Alignment (10-12 mins)
3. Leadership, Teaming & Stakeholder Management (4-6 mins)
4. Role-Specific Adaptive Questions (5-7 mins) - Adjust for seniority
5. Candidate Interpretation & Alignment (4-5 mins)
6. Motivation Pressure-Test (4-5 mins)
7. Compensation & Logistics (3-4 mins)
8. Closing (1-2 mins)

For Section 4, adapt questions based on seniority:
- Junior IC (0-3 yrs): Learning, feedback, mistakes
- Senior IC (4-8 yrs): Independent decisions, mentorship, ownership
- Lead/Principal IC (8+ yrs): Influence without authority, technical direction
- Team Lead (2-5 reports): Delegation, feedback, non-performer handling
- Manager (5+ reports): People development, prioritization, accountability
- Director/VP: Strategy, transformation, executive stakeholder management
```

### 8-Section Script Structure

**SECTION 1: INTRODUCTION (3-4 mins)**
```
Hi [Name], this is Abdulla Nigil. I lead Talent Acquisition for the Egis North America region, based in our Dubai office. Thank you for taking the time today — how are you doing?

Purpose:
"This call is typically 20–30 minutes. I'd like to understand your background at a high level, connect it to the role, understand your motivations, and give you a clear view of the opportunity. Very conversational."

Job Overview:
[Provide 2-3 sentence summary of role, project, team structure, key priorities]
```

**SECTION 2: CORE EXPERIENCE (10-12 mins)**
```
"Let's start with your background. I've reviewed your CV, so I won't ask you to repeat everything — I want to go deeper on specific areas."

Questions (select 4-5 based on JD alignment):
1. "Walk me through [specific project from CV] — what made it complex behind the scenes?"
2. "What part of [project] did you personally own? What measurable impact did your involvement have?"
3. "Tell me about a decision you made that didn't go as planned — how did you course-correct?"
4. "If you could redo [project] today, what would you change and why?"
5. "Describe a time you had to influence a technical or commercial outcome without formal authority."
```

**SECTION 3: LEADERSHIP & STAKEHOLDERS (4-6 mins)**

*For Leadership Roles:*
```
1. "Tell me about giving difficult feedback — how did you approach it and what was the outcome?"
2. "Describe a time someone on your team wasn't performing. What actions did you take?"
3. "How do you decide what to delegate versus what to personally handle?"
4. "What's your philosophy on developing people who resist development?"
```

*For IC Roles:*
```
1. "Tell me about a strong cross-functional collaboration — what made it effective?"
2. "How do you adapt your communication style when working with different personalities?"
3. "Have you mentored juniors? What did they typically struggle with?"
```

*For All Roles:*
```
1. "Walk me through a difficult stakeholder situation — what made it challenging?"
2. "How do you build trust with clients or senior stakeholders?"
3. "How do you prepare for high-stakes external reviews or presentations?"
```

**SECTION 4: SENIORITY-ADAPTIVE QUESTIONS (5-7 mins)**

*Director/VP Level:*
```
1. Strategy: "Tell me about reshaping a strategy — what triggered the shift?"
2. Accountability: "Walk me through a high-stakes situation where the outcome fell on you personally."
3. Leading Leaders: "Tell me about developing a leader on your team who then elevated performance."
4. Executive Stakeholders: "Describe managing a difficult C-suite or board stakeholder."
5. Transformation: "Tell me about leading major organisational change — what resistance did you face?"
6. Commercial Risk: "Tell me about a commercial risk you owned and how it played out."
```

*Manager Level:*
```
1. "Tell me about someone who wasn't working out — what actions did you take?"
2. "You have three critical projects and two capable people — how do you prioritise?"
3. "What's your approach to managing underperformers?"
```

*Senior IC Level:*
```
1. "Tell me about a significant decision you made without management input."
2. "Have you mentored juniors? What did they struggle with?"
3. "What does your manager never have to worry about when you're on a project?"
```

*Junior IC Level:*
```
1. "Tell me about a time you were stuck — how did you get unstuck?"
2. "Describe feedback that stung — what did you do with it?"
3. "What was your biggest mistake last year and what changed after?"
```

**SECTION 5: CANDIDATE INTERPRETATION (4-5 mins)**
```
"Now I'd like to understand how you see the role."

1. "In your own words, what do you see as the core responsibilities of this position?"
2. "What do you think are the most important priorities or challenges?"
3. "Where do you see yourself having the strongest impact from day one?"
4. [For senior roles] "If you were stepping in tomorrow, what would your first 60-90 days look like?"
```

**SECTION 6: MOTIVATION PRESSURE-TEST (4-5 mins)**
```
1. "Walk me through your last job move — what did you expect and what turned out different?"
2. "What's the ONE thing about this role that would make you say no?"
3. "If you received three offers tomorrow — what's your tiebreaker?"
4. "What didn't work in your last role that you want to avoid here?"
5. "What do you know about Egis beyond what's online?"
```

**SECTION 7: COMPENSATION & LOGISTICS (3-4 mins)**
```
1. "What's your target compensation range — base plus bonus?"
2. "What's your notice period?"
3. "Any relocation constraints or mobility preferences?"
4. "Are you in active discussions elsewhere? What stage?"
5. "What's your timeline to move if this aligns?"
```

**SECTION 8: CLOSING (1-2 mins)**
```
"That covers everything from my side — what questions do you have for me?"

[Answer candidate questions]

"Great. I'll prepare a summary and share it with the hiring team. You'll hear back from us in the next few days regarding next steps. Really appreciate your time today, [Name]. Speak soon."
```

---

## Prompt Engineering Techniques

### 1. Temperature Control

**Configuration:**
```python
self.temperature = 0.15  # Low temperature for deterministic, consistent results
```

**Rationale:** Low temperature reduces randomness, ensuring consistent output format and reliable JSON structure across multiple calls.

### 2. Structured Output Enforcement

**Pattern:**
```python
system_instruction = "Return valid JSON only."
response_mime_type = "application/json"
```

**Schema Validation:**
```python
def _validate_and_merge(baseline: dict, ai_response: dict) -> dict:
    """Merge AI response with baseline, validating structure"""
    if isinstance(baseline, dict) and isinstance(ai_response, dict):
        merged = baseline.copy()
        for key, value in ai_response.items():
            if value not in (None, "", [], {}):
                merged[key] = value
        return merged
    return baseline
```

### 3. Fallback-First Architecture

**Pattern:**
```python
def ai_feature(input_data):
    # Always generate fallback first
    fallback_result = deterministic_fallback(input_data)

    # Attempt AI enhancement
    try:
        if ai_service_available():
            ai_result = call_gemini_api(input_data)
            return merge_with_fallback(fallback_result, ai_result)
    except Exception as e:
        logger.warning(f"AI unavailable: {e}")

    # Return fallback if AI fails
    return fallback_result
```

### 4. Retry Logic with Exponential Backoff

**Configuration:**
```python
@retry(
    retry=retry_if_exception_type(GeminiServiceError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def _call_gemini_api(self, prompt: str) -> dict:
    # API call implementation
    pass
```

### 5. No Truncation Principle

**CV Screening Mandate:**
```
"Read and analyze the entire CV — all pages, all sections, all appendices.
No truncation - use 100% of available CV content."
```

**Implementation:**
```python
# Send full CV text, no character limits
cv_text = extract_full_text_from_pdf(cv_path)  # No truncation
prompt = f"=== FULL CV TEXT (NO TRUNCATION) ===\n{cv_text}\n\n..."
```

### 6. Evidence-Based Compliance

**Prompt Requirement:**
```
For EACH requirement, provide:
1. compliance_status: ✅ Complying | ❌ Not Complying | ⚠️ Not Mentioned
2. evidence: Specific text from CV with page/section reference
```

**Prevents:**
- Hallucinations
- Speculative assessments
- Ungrounded conclusions

### 7. Context Injection

**Structured Context Format:**
```python
context = {
    "title": "Senior Project Manager",
    "project_summary": "...",
    "responsibilities": [...],
    "requirements": [...],
    "nice_to_have": [...],
    "salary_hint": "..."
}

prompt = f"Generate a job description.\n\nContext:\n{json.dumps(context, indent=2)}"
```

### 8. Role-Based Personas

**Examples:**
- CV Screening: "Senior Talent Acquisition Partner for Egis Middle East & North America"
- Verbal Screening: "Insight-driven, conversational talent partner"
- Chatbot: "Helpful RecruitPro assistant"

### 9. Multi-Mode Fallbacks

**Hierarchy:**
```
1. Gemini API (preferred)
   ↓ (if unavailable)
2. Rule-based heuristics
   ↓ (if insufficient data)
3. Template-based defaults
```

### 10. Response Validation

**Pattern:**
```python
def parse_json_response(response_text: str) -> dict:
    """Parse JSON with multiple fallback strategies"""
    try:
        # Direct JSON parse
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Try extracting JSON from markdown code blocks
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Fallback to empty dict
        return {}
```

---

## API Configuration

### Gemini Service Settings

```python
# Model Configuration
DEFAULT_MODEL = "gemini-2.5-flash-lite"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
TEMPERATURE = 0.15
TIMEOUT = 30  # seconds

# Request Headers
headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": api_key
}

# Payload Structure
payload = {
    "contents": [
        {
            "role": "user",
            "parts": [{"text": prompt}]
        }
    ],
    "generationConfig": {
        "temperature": self.temperature,
        "responseMimeType": "application/json"
    },
    "systemInstruction": {
        "parts": [{"text": system_instruction}]
    }
}

# Endpoint
endpoint = f"{BASE_URL}/models/{model}:generateContent"
```

### Rate Limiting

```python
# No explicit rate limiting implemented
# Gemini API handles rate limits via HTTP 429 responses
# Retry logic handles transient failures
```

### Error Handling

```python
class GeminiServiceError(Exception):
    """Base exception for Gemini service errors"""
    pass

class GeminiAPIKeyMissing(GeminiServiceError):
    """API key not configured"""
    pass

class GeminiAPIError(GeminiServiceError):
    """API call failed"""
    pass

# Usage
try:
    result = gemini_service.screen_cv(cv_text, requirements)
except GeminiAPIKeyMissing:
    # Use fallback logic
    result = fallback_screen_cv(cv_text, requirements)
except GeminiAPIError as e:
    logger.error(f"Gemini API error: {e}")
    result = fallback_screen_cv(cv_text, requirements)
```

---

## Feature Toggles

### Default Feature Flags

```python
DEFAULT_FEATURE_FLAGS = {
    "chatbot.tool_suggestions": {
        "market_research": True,
        "salary_benchmark": True,
        "bulk_outreach": True
    },
    "sourcing.smartrecruiters_enabled": True,
    "screening.require_ai_score": True,
    "documents.auto_analyze_on_upload": True,
    "research.auto_run_market_research": True
}
```

### Runtime Configuration

**Database Storage:**
```sql
CREATE TABLE advanced_features_config (
    key VARCHAR(255) PRIMARY KEY,
    value_json JSONB NOT NULL,
    updated_by VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**API Endpoints:**
```
GET  /api/admin/advanced/features          # List all feature flags
PUT  /api/admin/advanced/features/{key}    # Update feature flag
```

---

**Document Approval:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| AI Engineering Lead | [Name] | ___________ | ________ |
| Product Owner | [Name] | ___________ | ________ |
| QA Lead | [Name] | ___________ | ________ |

---

**End of AI Prompts Documentation**
