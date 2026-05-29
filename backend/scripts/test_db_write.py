"""Test DB write to isolate 500 error."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test():
    from app.models.database import init_db, async_session_maker, CodingSession, AssignedCode
    from datetime import datetime
    import uuid

    await init_db()

    async with async_session_maker() as db:
        session_id = str(uuid.uuid4())
        try:
            rec = CodingSession(
                id=session_id,
                user_id="dev-user",
                status="completed",
                document_type="progress_note",
                specialty="cardiology",
                clinical_text="Patient has diabetes.",
                phi_encrypted=False,
                soap_json={"assessment": "diabetes", "raw_text": "test"},
                extracted_entities_json=[{"text": "diabetes", "entity_type": "DISEASE", "start_char": 0, "end_char": 8, "confidence": 0.7}],
                model_used="openai/gpt-4o",
                processing_time_ms=5000,
                summary="Test",
                requires_human_review=False,
                metadata_json={},
            )
            db.add(rec)

            code_rec = AssignedCode(
                session_id=session_id,
                code="E11.9",
                code_type="ICD-10-CM",
                description="Type 2 diabetes mellitus without complications",
                confidence=0.85,
                is_primary=True,
                evidence="Patient has diabetes",
                modifiers=[],
                hierarchy="E11",
            )
            db.add(code_rec)
            await db.commit()
            print(f"SUCCESS: session {session_id} written to DB")
        except Exception as e:
            import traceback
            print(f"ERROR: {e}")
            traceback.print_exc()
            await db.rollback()

asyncio.run(test())
