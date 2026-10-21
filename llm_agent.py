import os
import time
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class AgentDecision(BaseModel):
    category: str = Field(description="Must be exactly one of: 'RTI', 'Grievance', or 'PII_Violation'")
    public_authority: str | None = Field(default=None, description="Formal name of authority if RTI.")
    draft_text: str | None = Field(default=None, description="Draft RTI application text if RTI.")
    reasoning: str = Field(description="Evidence and reasoning behind the decision.")

def local_fallback_classifier(info_needed: str, dept: str, state: str) -> AgentDecision:
    text_lower = info_needed.lower()
    
    doc_keywords = ["copy", "copies", "report", "reports", "budget", "spending", "audit", "ledger", "invoice", "receipt", "file noting", "policy", "guideline", "expenditure", "records", "details of", "tender"]
    has_doc_request = any(k in text_lower for k in doc_keywords)
    
    pii_keywords = ["tax return", "salary slip", "medical record", "personal asset", "aadhaar", "pan card", "phone number", "neighbor", "private data"]
    is_pii = any(k in text_lower for k in pii_keywords)
    
    grievance_verbs = ["fix", "repair", "clean", "solve", "resolve", "action against", "complaint", "delayed", "refund", "replace", "install"]
    has_grievance_intent = any(k in text_lower for k in grievance_verbs)
    
    if is_pii:
        return AgentDecision(
            category="PII_Violation",
            public_authority=None,
            draft_text=None,
            reasoning="[Fallback Rule Engine] Request seeks third-party personal/private data. Flagged under Section 8(1)(j)."
        )
    elif has_grievance_intent and not has_doc_request:
        return AgentDecision(
            category="Grievance",
            public_authority=None,
            draft_text=None,
            reasoning="[Fallback Rule Engine] Request demands service repair/action rather than official records. Redirected to Grievance portal."
        )
    else:
        authority = f"Public Information Officer, {dept}, Government of {state}"
        draft = (
            f"To,\nThe Public Information Officer (PIO),\n{authority}\n\n"
            f"Subject: Application under Section 6(1) of the RTI Act, 2005.\n\n"
            f"Respected Sir/Madam,\n"
            f"Kindly provide certified copies of official records and expenditure details regarding:\n"
            f"\"{info_needed}\"\n\n"
            f"Please arrange to provide the information within the statutory 30-day timeline.\n\n"
            f"Applicant: Registered Citizen\nDate: {time.strftime('%Y-%m-%d')}"
        )
        return AgentDecision(
            category="RTI",
            public_authority=authority,
            draft_text=draft,
            reasoning="[Fallback Rule Engine] Request targets official information/public records. Mapped to valid RTI framework."
        )

def run_decision_rules(info_needed: str, dept: str, state: str) -> AgentDecision:
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key:
        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=5000)
            )
            
            prompt = f"""
            You are an expert Indian Governance and Legal AI Assistant specializing in the RTI Act 2005, Public Grievances, and Data Privacy under Section 8(1)(j).
            
            Analyze this citizen request across any department or state:
            - Info Requested: "{info_needed}"
            - Department: "{dept}"
            - State: "{state}"
            
            Classification Guidelines:
            1. "RTI": Choose this if asking for public records, government files, budgets, spending, tenders, policies, or official data under Section 2(j). Map the formal public authority and generate an RTI draft application under Section 6(1).
            2. "Grievance": Choose this if asking for service execution, direct repairs, or complaint resolution where no official record is primarily sought.
            3. "PII_Violation": Choose this if asking for third-party personal data or private information exempted under Section 8(1)(j).
            """
            
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AgentDecision,
                    temperature=0.1,
                ),
            )
            return AgentDecision.model_validate_json(response.text)
            
        except Exception as e:
            print(f"⚠️ API call skipped/failed ({e}). Executing local rule engine...")
            return local_fallback_classifier(info_needed, dept, state)
    else:
        print("⚠️ GEMINI_API_KEY not found. Running local rule engine...")
        return local_fallback_classifier(info_needed, dept, state)