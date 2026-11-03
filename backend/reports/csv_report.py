"""CSV Report Exporter for Test Sessions."""
import csv
import io
import json
from database import get_session, get_session_results, get_capability_scores

def generate_csv_report(session_id: int) -> str:
    """
    Generates a comprehensive CSV string for the specified test session.
    """
    session = get_session(session_id)
    if not session:
        return ""

    results = get_session_results(session_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header section
    writer.writerow(["=== AI MODEL EVALUATION & INVESTIGATION REPORT ==="])
    writer.writerow(["Session ID", session.get("id")])
    writer.writerow(["Session Name", session.get("session_name")])
    writer.writerow(["Provider", session.get("provider")])
    writer.writerow(["Model ID", session.get("model_id")])
    writer.writerow(["Overall Score", f"{session.get('overall_score')}/100"])
    writer.writerow(["Reliability Assessment", session.get("reliability_level")])
    writer.writerow(["Average Latency (ms)", session.get("avg_response_time")])
    writer.writerow(["Total Tests", session.get("total_tests")])
    writer.writerow(["Passed Tests", session.get("passed_tests")])
    writer.writerow(["Failed Tests", session.get("failed_tests")])
    writer.writerow(["Tested At", session.get("started_at")])
    writer.writerow([])

    # Table of Individual Results
    writer.writerow([
        "Test #",
        "Capability",
        "Subcategory",
        "Difficulty",
        "Score (0-100)",
        "Investigation Status",
        "Latency (ms)",
        "Test Prompt",
        "Model Output",
        "Detected Failure",
        "Evidence",
        "Severity",
        "Confidence",
        "Recommended Improvement"
    ])

    for idx, r in enumerate(results, 1):
        failures = ""
        try:
            raw_f = r.get("failures")
            if raw_f:
                parsed_f = json.loads(raw_f) if isinstance(raw_f, str) else raw_f
                failures = "; ".join(parsed_f) if isinstance(parsed_f, list) else str(parsed_f)
        except Exception:
            failures = str(r.get("failures", ""))

        evidence = ""
        try:
            raw_e = r.get("evidence")
            if raw_e:
                parsed_e = json.loads(raw_e) if isinstance(raw_e, str) else raw_e
                evidence = "; ".join(parsed_e) if isinstance(parsed_e, list) else str(parsed_e)
        except Exception:
            evidence = str(r.get("evidence", ""))

        writer.writerow([
            idx,
            r.get("capability", ""),
            r.get("subcategory", ""),
            r.get("difficulty", ""),
            r.get("score", ""),
            r.get("status", ""),
            r.get("response_time_ms", ""),
            r.get("prompt", ""),
            r.get("model_response", ""),
            failures,
            evidence,
            r.get("severity", ""),
            r.get("confidence", ""),
            r.get("recommendation", "")
        ])

    return output.getvalue()
