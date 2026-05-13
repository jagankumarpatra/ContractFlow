import json
from typing import Optional
from app.core.config import settings

MOCK_ANALYSIS = {
    "parties": ["Party A Corp", "Party B Ltd"],
    "contract_summary": "This is a service agreement between two companies for software development services.",
    "key_dates": {
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "notice_period": "30 days"
    },
    "key_obligations": [
        "Service provider must deliver software within agreed timelines",
        "Client must make payment within 30 days of invoice",
        "Both parties must maintain confidentiality of shared information"
    ],
    "risky_clauses": [
        "Section 4.2: Unlimited liability clause — no cap on damages",
        "Section 7.1: Auto-renewal clause without explicit opt-out"
    ],
    "payment_terms": "Net 30 days from invoice date",
    "governing_law": "Laws of India",
    "termination_conditions": [
        "Either party may terminate with 30 days written notice",
        "Immediate termination for material breach"
    ],
    "risk_score": 6,
    "risk_level": "medium",
    "recommendations": [
        "Add a liability cap (e.g., 3x contract value)",
        "Clarify auto-renewal opt-out procedure",
        "Define specific SLA metrics"
    ]
}

def analyze_contract(contract_text: str, title: str = "") -> dict:
    """
    Analyze contract text using Claude API.
    Falls back to mock response if API key not configured.
    """
    if not settings.ANTHROPIC_API_KEY:
        # Return realistic mock — same structure as real Claude response
        mock = MOCK_ANALYSIS.copy()
        mock["contract_summary"] = f"Analysis of contract: {title}. {mock['contract_summary']}"
        mock["_note"] = "Mock analysis — set ANTHROPIC_API_KEY for real AI analysis"
        return mock

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        prompt = f"""Analyze the following contract and return a JSON response with these exact fields:
- parties: list of party names mentioned
- contract_summary: 2-3 sentence summary
- key_dates: dict with start_date, end_date, notice_period
- key_obligations: list of main obligations
- risky_clauses: list of potentially risky clauses with section references
- payment_terms: string
- governing_law: string
- termination_conditions: list
- risk_score: integer 1-10 (10 = highest risk)
- risk_level: "low", "medium", or "high"
- recommendations: list of suggestions to reduce risk

Contract Title: {title}

Contract Text:
{contract_text[:4000]}

Return ONLY valid JSON, no markdown, no explanation."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        return json.loads(raw)

    except Exception as e:
        mock = MOCK_ANALYSIS.copy()
        mock["_error"] = f"AI analysis failed: {str(e)}. Showing mock response."
        return mock
