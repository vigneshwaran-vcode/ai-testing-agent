"""Smoke test suite to verify all backend engines, routes, and DB layers."""
import os
import sys
import json

backend_dir = os.path.dirname(__file__)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app
from database import init_db, save_model_config, set_active_model, create_session, get_active_model
from capabilities.detector import detect_capabilities
from capabilities.test_generator import generate_test_cases
from engine.evaluator import evaluate_response
from engine.investigator import investigate_test_result
from reports.csv_report import generate_csv_report
from reports.pdf_report import generate_pdf_report

def run_smoke_test():
    print("--> 1. Initializing DB...")
    init_db()

    print("--> 2. Testing Model Selection and Active Model...")
    mid = save_model_config("gemini", "gemini-1.5-flash", "Google Gemini 1.5 Flash", capabilities=["chat", "coding", "reasoning", "document", "safety"])
    set_active_model(mid)
    active = get_active_model()
    assert active["model_id"] == "gemini-1.5-flash", "Active model mismatch!"
    print("    [PASS] Active model saved:", active["display_name"])

    print("--> 3. Testing Capability Detection...")
    caps = detect_capabilities("gemini", "gemini-1.5-flash")
    assert len(caps) >= 5, "Expected at least 5 capabilities for Gemini!"
    print(f"    [PASS] Detected {len(caps)} capabilities.")

    print("--> 4. Testing Automatic Test Generation...")
    cases = generate_test_cases(["chat", "coding", "reasoning", "safety"], count_per_cap=2)
    assert len(cases) > 0, "No test cases generated!"
    print(f"    [PASS] Generated {len(cases)} test cases.")

    print("--> 5. Testing Evaluator and Investigator Engine...")
    eval_res = evaluate_response("reasoning", "bat and ball problem", "The ball costs 5 cents ($0.05).", '{"correct_answer": "5 cents"}')
    assert eval_res["score"] == 100.0, f"Expected 100 score, got {eval_res['score']}"
    inv = investigate_test_result({"capability": "reasoning", "subcategory": "Math"}, "5 cents", eval_res)
    assert inv["category"] == "Correct", f"Expected Correct, got {inv['category']}"
    print(f"    [PASS] Evaluator & Investigator verified. Score={eval_res['score']}, Category={inv['category']}")

    print("--> 6. Testing Test Client Routes...")
    client = app.test_client()
    for route in ['/dashboard', '/select-model', '/capabilities', '/test-config', '/history', '/settings']:
        res = client.get(route)
        assert res.status_code == 200, f"Route {route} failed with {res.status_code}"
        print(f"    [PASS] Route {route} -> 200 OK")

    print("--> 7. Testing PDF & CSV Generation...")
    sid = create_session(mid, "gemini", "gemini-1.5-flash", "Smoke Test Session")
    csv_out = generate_csv_report(sid)
    assert "AI MODEL EVALUATION" in csv_out, "CSV header missing"
    pdf_out = generate_pdf_report(sid)
    assert len(pdf_out) > 500, "PDF bytes too small"
    print(f"    [PASS] CSV export ({len(csv_out)} chars) and PDF report ({len(pdf_out)} bytes) verified.")

    print("\n[SUCCESS] ALL SMOKE TESTS PASSED!")

if __name__ == '__main__':
    run_smoke_test()
