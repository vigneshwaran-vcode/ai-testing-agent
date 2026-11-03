"""Test Execution Engine for AI Model Testing & Investigation."""
import os
import sys
import time
import json
import subprocess
import tempfile
from config import Config
from database import get_db
from models import get_provider
from engine.evaluator import evaluate_response, extract_python_code
from engine.investigator import investigate_test_result

def run_isolated_python_code(code: str, test_assertions: str) -> dict:
    """
    Executes Python code in a sandboxed subprocess with strict timeout.
    Returns:
    - passed: bool
    - stdout: str
    - error: str
    """
    full_script = f"""
# Isolated Sandbox Execution
import sys

{code}

# Test Verification Assertions
{test_assertions}
"""
    temp_dir = Config.SANDBOX_FOLDER
    os.makedirs(temp_dir, exist_ok=True)

    with tempfile.NamedTemporaryFile('w', suffix='.py', dir=temp_dir, delete=False, encoding='utf-8') as f:
        f.write(full_script)
        temp_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=Config.CODE_SANDBOX_TIMEOUT
        )
        passed = (proc.returncode == 0) and ("TESTS_PASSED" in proc.stdout or proc.returncode == 0)
        return {
            "passed": passed,
            "stdout": proc.stdout.strip(),
            "error": proc.stderr.strip() if proc.returncode != 0 else ""
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "stdout": "",
            "error": f"Execution timed out after {Config.CODE_SANDBOX_TIMEOUT} seconds (Infinite loop or stalled process)."
        }
    except Exception as e:
        return {
            "passed": False,
            "stdout": "",
            "error": f"Sandbox execution error: {str(e)}"
        }
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

def execute_single_test(session_id: int, test_case: dict, provider_instance) -> dict:
    """
    Executes one test case against the configured model, scores it, investigates failures,
    and commits the result to SQLite.
    """
    capability = test_case.get("capability")
    prompt = test_case.get("prompt")
    test_case_id = test_case.get("id")
    criteria_json = test_case.get("evaluation_criteria", "{}")

    model_response = ""
    response_time_ms = 0.0
    execution_result = None

    # Step 1: Send prompt to model provider
    try:
        if capability == "image_generation" and hasattr(provider_instance, "generate_image"):
            image_url, response_time_ms = provider_instance.generate_image(prompt)
            model_response = f"Generated Image URL: {image_url}"
        else:
            model_response, response_time_ms = provider_instance.chat(prompt)
    except Exception as e:
        model_response = f"API Error: {str(e)}"
        response_time_ms = 0.0

    # Step 2: If coding, run sandbox execution
    if capability == "coding" and not model_response.startswith("API Error:"):
        code = extract_python_code(model_response)
        try:
            crit = json.loads(criteria_json) if isinstance(criteria_json, str) else criteria_json
            test_code = crit.get("test_code", "")
            if test_code:
                execution_result = run_isolated_python_code(code, test_code)
        except Exception as e:
            execution_result = {"passed": False, "error": str(e), "stdout": ""}

    # Step 3: Evaluate response using capability-specific metrics
    eval_res = evaluate_response(
        capability=capability,
        prompt=prompt,
        response=model_response,
        criteria_json=criteria_json,
        execution_result=execution_result
    )

    # Step 4: Perform forensic failure investigation
    investigation = investigate_test_result(
        test_case=test_case,
        model_response=model_response,
        eval_result=eval_res,
        execution_result=execution_result
    )

    # Step 5: Save result to SQLite
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO test_results (
            test_case_id, session_id, capability, model_response,
            response_time_ms, score, status, metrics, failures,
            evidence, severity, confidence, recommendation, executed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (
        test_case_id,
        session_id,
        capability,
        model_response,
        response_time_ms,
        eval_res.get("score", 0),
        investigation.get("category", "Requires human review"),
        json.dumps(eval_res.get("metrics", {})),
        json.dumps(eval_res.get("failures", [])),
        json.dumps([investigation.get("evidence", "")]),
        investigation.get("severity", "low"),
        investigation.get("confidence", 90.0),
        investigation.get("recommendation", "")
    ))
    result_id = cursor.lastrowid

    # Update test_case status
    case_status = "passed" if eval_res.get("score", 0) >= 70 else "failed"
    cursor.execute("UPDATE test_cases SET status=? WHERE id=?", (case_status, test_case_id))

    conn.commit()
    conn.close()

    return {
        "id": result_id,
        "test_case_id": test_case_id,
        "capability": capability,
        "subcategory": test_case.get("subcategory"),
        "difficulty": test_case.get("difficulty"),
        "prompt": prompt,
        "model_response": model_response,
        "response_time_ms": round(response_time_ms, 1),
        "score": eval_res.get("score", 0),
        "status": investigation.get("category"),
        "metrics": eval_res.get("metrics", {}),
        "failures": eval_res.get("failures", []),
        "evidence": investigation.get("evidence"),
        "severity": investigation.get("severity"),
        "confidence": investigation.get("confidence"),
        "recommendation": investigation.get("recommendation")
    }

def update_session_aggregates(session_id: int):
    """
    Computes and updates aggregate metrics for a session:
    overall score, reliability level (HIGH/MEDIUM/LOW), avg response time, capability breakdown.
    """
    conn = get_db()
    results = conn.execute("SELECT * FROM test_results WHERE session_id=?", (session_id,)).fetchall()
    if not results:
        conn.close()
        return

    total = len(results)
    scores = [r["score"] for r in results if r["score"] is not None]
    times = [r["response_time_ms"] for r in results if r["response_time_ms"] is not None]
    passed = sum(1 for r in results if r["score"] and r["score"] >= 70)
    failed = total - passed

    overall_score = round(sum(scores) / total, 1) if scores else 0
    avg_time = round(sum(times) / total, 1) if times else 0

    if overall_score >= Config.RELIABILITY_HIGH:
        reliability = "HIGH"
    elif overall_score >= Config.RELIABILITY_MEDIUM:
        reliability = "MEDIUM"
    else:
        reliability = "LOW"

    # Capability breakdown
    caps = {}
    for r in results:
        c = r["capability"]
        if c not in caps:
            caps[c] = {"scores": [], "times": [], "passed": 0, "total": 0, "failures": 0}
        caps[c]["scores"].append(r["score"])
        caps[c]["times"].append(r["response_time_ms"])
        caps[c]["total"] += 1
        if r["score"] and r["score"] >= 70:
            caps[c]["passed"] += 1
        else:
            caps[c]["failures"] += 1

    # Insert/update capability_scores table
    conn.execute("DELETE FROM capability_scores WHERE session_id=?", (session_id,))
    for c, data in caps.items():
        c_avg = round(sum(data["scores"]) / data["total"], 1) if data["scores"] else 0
        c_time = round(sum(data["times"]) / data["total"], 1) if data["times"] else 0
        c_rel = "HIGH" if c_avg >= 80 else ("MEDIUM" if c_avg >= 50 else "LOW")
        conn.execute('''
            INSERT INTO capability_scores (
                session_id, capability, total_tests, passed_tests,
                avg_score, avg_response_time, failure_count, reliability_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, c, data["total"], data["passed"], c_avg, c_time, data["failures"], c_rel))

    # Update test_sessions table
    conn.execute('''
        UPDATE test_sessions
        SET status='completed',
            total_tests=?,
            passed_tests=?,
            failed_tests=?,
            avg_response_time=?,
            overall_score=?,
            reliability_level=?,
            completed_at=datetime('now')
        WHERE id=?
    ''', (total, passed, failed, avg_time, overall_score, reliability, session_id))

    conn.commit()
    conn.close()
