"""AI Model Testing, Evaluation and Investigation Agent — Flask Application."""
import os
import sys
import io
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, Response
from flask_cors import CORS

from config import Config
from database import (
    init_db, get_db, get_active_model, set_active_model,
    create_session, get_session, get_all_sessions,
    get_session_results, get_capability_scores,
    save_model_config, get_all_models, get_setting, set_setting
)
from models import get_provider
from capabilities.detector import detect_capabilities, CAPABILITY_DEFINITIONS
from capabilities.test_generator import generate_test_cases
from engine.test_runner import execute_single_test, update_session_aggregates
from reports.csv_report import generate_csv_report
from reports.pdf_report import generate_pdf_report

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'static')
)
app.config.from_object(Config)
app.jinja_env.auto_reload = True
CORS(app)

# Initialize database on startup
init_db()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    active_model = get_active_model()
    sessions = get_all_sessions()
    latest_session = sessions[0] if sessions else None
    return render_template(
        'dashboard.html',
        active_page='dashboard',
        active_model=active_model,
        latest_session=latest_session,
        sessions=sessions[:5]
    )

@app.route('/select-model')
def select_model():
    active_model = get_active_model()
    saved_models = get_all_models()
    return render_template(
        'model_select.html',
        active_page='select_model',
        active_model=active_model,
        saved_models=saved_models
    )

@app.route('/capabilities')
def capabilities():
    active_model = get_active_model()
    caps = []
    if active_model:
        caps_stored = json.loads(active_model.get("capabilities") or "[]")
        caps = detect_capabilities(active_model["provider"], active_model["model_id"], caps_stored)
    return render_template(
        'capabilities.html',
        active_page='capabilities',
        active_model=active_model,
        capabilities=caps,
        all_definitions=CAPABILITY_DEFINITIONS
    )

@app.route('/test-config')
def test_config():
    active_model = get_active_model()
    caps = []
    if active_model:
        caps_stored = json.loads(active_model.get("capabilities") or "[]")
        caps = detect_capabilities(active_model["provider"], active_model["model_id"], caps_stored)
    return render_template(
        'test_config.html',
        active_page='test_config',
        active_model=active_model,
        capabilities=caps
    )

@app.route('/run-tests')
def run_tests():
    active_model = get_active_model()
    session_id = request.args.get('session_id')
    session = get_session(session_id) if session_id else None
    return render_template(
        'run_tests.html',
        active_page='run_tests',
        active_model=active_model,
        session=session,
        session_id=session_id
    )

@app.route('/investigation')
def investigation():
    active_model = get_active_model()
    session_id = request.args.get('session_id')
    sessions = get_all_sessions()

    if not session_id and sessions:
        session_id = sessions[0]["id"]

    session = get_session(session_id) if session_id else None
    results = get_session_results(session_id) if session_id else []

    return render_template(
        'investigation.html',
        active_page='investigation',
        active_model=active_model,
        session=session,
        sessions=sessions,
        results=results
    )

@app.route('/analysis')
def analysis():
    active_model = get_active_model()
    session_id = request.args.get('session_id')
    sessions = get_all_sessions()

    if not session_id and sessions:
        session_id = sessions[0]["id"]

    session = get_session(session_id) if session_id else None
    cap_scores = get_capability_scores(session_id) if session_id else []

    return render_template(
        'analysis.html',
        active_page='analysis',
        active_model=active_model,
        session=session,
        sessions=sessions,
        cap_scores=cap_scores
    )

@app.route('/reports')
def reports():
    active_model = get_active_model()
    session_id = request.args.get('session_id')
    sessions = get_all_sessions()

    if not session_id and sessions:
        session_id = sessions[0]["id"]

    session = get_session(session_id) if session_id else None
    results = get_session_results(session_id) if session_id else []
    cap_scores = get_capability_scores(session_id) if session_id else []

    return render_template(
        'reports.html',
        active_page='reports',
        active_model=active_model,
        session=session,
        sessions=sessions,
        results=results,
        cap_scores=cap_scores
    )

@app.route('/history')
def history():
    active_model = get_active_model()
    sessions = get_all_sessions()
    return render_template(
        'history.html',
        active_page='history',
        active_model=active_model,
        sessions=sessions
    )

@app.route('/settings')
def settings_page():
    active_model = get_active_model()
    settings_dict = {
        "openai_key": get_setting("OPENAI_API_KEY", Config.OPENAI_API_KEY),
        "gemini_key": get_setting("GOOGLE_API_KEY", Config.GOOGLE_API_KEY),
        "anthropic_key": get_setting("ANTHROPIC_API_KEY", Config.ANTHROPIC_API_KEY),
        "ollama_url": get_setting("OLLAMA_BASE_URL", Config.OLLAMA_BASE_URL),
        "custom_url": get_setting("CUSTOM_API_URL", Config.CUSTOM_API_URL),
        "custom_key": get_setting("CUSTOM_API_KEY", Config.CUSTOM_API_KEY),
        "timeout": get_setting("DEFAULT_TIMEOUT", str(Config.DEFAULT_TIMEOUT)),
        "rel_high": get_setting("RELIABILITY_HIGH", str(Config.RELIABILITY_HIGH)),
        "rel_med": get_setting("RELIABILITY_MEDIUM", str(Config.RELIABILITY_MEDIUM)),
    }
    return render_template(
        'settings.html',
        active_page='settings',
        active_model=active_model,
        settings=settings_dict
    )

# ─────────────────────────────────────────────────────────────────────────────
# REST API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/active-model', methods=['GET'])
def api_active_model():
    model = get_active_model()
    return jsonify({"success": True, "model": model})

@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    data = request.json or {}
    provider_name = data.get('provider')
    api_key = data.get('api_key', '').strip()
    base_url = data.get('base_url', '').strip()
    model_id = data.get('model_id', '').strip()

    if not api_key:
        # Fallback to saved setting or env
        env_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "custom": "CUSTOM_API_KEY"
        }
        ref = env_map.get(provider_name)
        if ref:
            api_key = get_setting(ref, getattr(Config, ref, ""))

    try:
        provider = get_provider(provider_name, api_key=api_key, base_url=base_url, model_id=model_id, timeout=Config.DEFAULT_TIMEOUT)
        res = provider.test_connection()
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "message": f"Integration error: {str(e)}"})

@app.route('/api/select-model', methods=['POST'])
def api_select_model():
    data = request.json or {}
    provider = data.get('provider')
    model_id = data.get('model_id')
    display_name = data.get('display_name') or f"{provider.title()} {model_id}"
    api_key = data.get('api_key', '').strip()
    base_url = data.get('base_url', '').strip()

    # Save API key in settings if provided
    if api_key:
        env_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "custom": "CUSTOM_API_KEY"
        }
        ref = env_map.get(provider)
        if ref:
            set_setting(ref, api_key)

    # Detect supported capabilities
    prov_instance = get_provider(provider, api_key=api_key, base_url=base_url, model_id=model_id, timeout=Config.DEFAULT_TIMEOUT)
    detected_caps = prov_instance.get_capabilities() if hasattr(prov_instance, "get_capabilities") else ["chat", "coding", "reasoning", "document", "safety"]

    model_config_id = save_model_config(
        provider=provider,
        model_id=model_id,
        display_name=display_name,
        api_key_ref=api_key,
        base_url=base_url,
        capabilities=detected_caps
    )
    set_active_model(model_config_id)

    return jsonify({
        "success": True,
        "message": f"Successfully activated {display_name}",
        "model_config_id": model_config_id,
        "capabilities": detected_caps
    })

@app.route('/api/models/<int:config_id>/activate', methods=['POST'])
def api_activate_model(config_id):
    set_active_model(config_id)
    return jsonify({"success": True, "message": f"Model configuration #{config_id} activated."})

@app.route('/api/providers', methods=['GET'])
def api_providers():
    from models.gemini_provider import GEMINI_MODELS
    from models.openai_provider import OPENAI_MODELS
    from models.anthropic_provider import ANTHROPIC_MODELS
    return jsonify({
        "success": True,
        "providers": {
            "gemini": GEMINI_MODELS,
            "openai": OPENAI_MODELS,
            "anthropic": ANTHROPIC_MODELS
        }
    })

@app.route('/api/capabilities/detect', methods=['GET'])
def api_detect_capabilities():
    active_model = get_active_model()
    if not active_model:
        return jsonify({"success": False, "message": "No active model selected."}), 400

    stored_caps = json.loads(active_model.get("capabilities") or "[]")
    caps = detect_capabilities(active_model["provider"], active_model["model_id"], stored_caps)
    return jsonify({"success": True, "capabilities": caps})

@app.route('/api/test-cases/generate', methods=['POST'])
def api_generate_test_cases():
    data = request.json or {}
    capabilities = data.get('capabilities', ['chat'])
    count_per_cap = int(data.get('count_per_cap', 3))
    difficulty = data.get('difficulty', 'all')

    cases = generate_test_cases(capabilities, count_per_cap=count_per_cap, difficulty_filter=difficulty)
    return jsonify({"success": True, "cases": cases, "count": len(cases)})

@app.route('/api/session/start', methods=['POST'])
def api_start_session():
    data = request.json or {}
    test_cases = data.get('test_cases', [])
    session_name = data.get('session_name')

    active_model = get_active_model()
    if not active_model:
        return jsonify({"success": False, "message": "No active model selected."}), 400

    session_id = create_session(
        model_config_id=active_model["id"],
        provider=active_model["provider"],
        model_id=active_model["model_id"],
        session_name=session_name
    )

    # Insert test cases into database
    conn = get_db()
    inserted_cases = []
    for tc in test_cases:
        cursor = conn.execute('''
            INSERT INTO test_cases (session_id, capability, subcategory, difficulty, prompt, expected_output, evaluation_criteria, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (
            session_id,
            tc.get("capability"),
            tc.get("subcategory"),
            tc.get("difficulty", "normal"),
            tc.get("prompt"),
            tc.get("expected_output", ""),
            tc.get("evaluation_criteria", "")
        ))
        inserted_cases.append({
            "id": cursor.lastrowid,
            "session_id": session_id,
            "capability": tc.get("capability"),
            "subcategory": tc.get("subcategory"),
            "difficulty": tc.get("difficulty"),
            "prompt": tc.get("prompt"),
            "evaluation_criteria": tc.get("evaluation_criteria")
        })

    conn.execute("UPDATE test_sessions SET total_tests=? WHERE id=?", (len(inserted_cases), session_id))
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "session_id": session_id,
        "test_cases": inserted_cases
    })

@app.route('/api/test/execute-single', methods=['POST'])
def api_execute_single_test():
    data = request.json or {}
    session_id = data.get('session_id')
    test_case = data.get('test_case')

    active_model = get_active_model()
    if not active_model:
        return jsonify({"success": False, "message": "No active model configured."}), 400

    # Retrieve credentials
    api_key = active_model.get("api_key_ref")
    if not api_key:
        env_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "custom": "CUSTOM_API_KEY"
        }
        ref = env_map.get(active_model["provider"])
        if ref:
            api_key = get_setting(ref, getattr(Config, ref, ""))

    base_url = active_model.get("base_url")

    provider_instance = get_provider(
        active_model["provider"],
        api_key=api_key,
        base_url=base_url,
        model_id=active_model["model_id"],
        timeout=Config.DEFAULT_TIMEOUT
    )

    result = execute_single_test(session_id, test_case, provider_instance)
    return jsonify({"success": True, "result": result})

@app.route('/api/session/<int:session_id>/finalize', methods=['POST'])
def api_finalize_session(session_id):
    update_session_aggregates(session_id)
    session = get_session(session_id)
    return jsonify({"success": True, "session": session})

@app.route('/api/session/<int:session_id>', methods=['GET'])
def api_get_session(session_id):
    session = get_session(session_id)
    results = get_session_results(session_id)
    cap_scores = get_capability_scores(session_id)
    return jsonify({
        "success": True,
        "session": session,
        "results": results,
        "capability_scores": cap_scores
    })

@app.route('/api/sessions', methods=['GET'])
def api_list_sessions():
    sessions = get_all_sessions()
    return jsonify({"success": True, "sessions": sessions})

@app.route('/api/session/<int:session_id>/export/csv', methods=['GET'])
def api_export_csv(session_id):
    csv_data = generate_csv_report(session_id)
    session = get_session(session_id)
    filename = f"evaluation_{session.get('provider')}_{session.get('model_id')}_{session_id}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/api/session/<int:session_id>/export/pdf', methods=['GET'])
def api_export_pdf(session_id):
    pdf_bytes = generate_pdf_report(session_id)
    session = get_session(session_id)
    filename = f"evaluation_{session.get('provider')}_{session.get('model_id')}_{session_id}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    data = request.json or {}
    for k, v in data.items():
        set_setting(k, str(v).strip())
    return jsonify({"success": True, "message": "Settings saved successfully."})

# Run local development server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
