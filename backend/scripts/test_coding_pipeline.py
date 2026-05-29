"""Test coding pipeline directly to expose errors."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test():
    from app.models.schemas import CodingRequest, DocumentType, Specialty
    from app.agents.medical_coder import get_medical_coder

    request = CodingRequest(
        text="Patient has type 2 diabetes mellitus and hypertension.",
        document_type=DocumentType.PROGRESS_NOTE,
        specialty=Specialty("internal_medicine"),
    )

    agent = get_medical_coder()
    try:
        result = await agent.code_clinical_note(request)
        print(f"SUCCESS: {len(result.codes)} codes")
        for c in result.codes:
            print(f"  {c.code} — {c.description}")
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()

asyncio.run(test())
